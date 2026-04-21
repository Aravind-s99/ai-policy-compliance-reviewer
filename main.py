from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import uuid
import os
from datetime import datetime

from models import RiskReport, DocumentMeta
from document_parser import DocumentParser
from rule_engine import RuleEngine
from llm_analyzer import LLMAnalyzer
from rag_engine import RAGEngine


app = FastAPI(
    title="AI Policy & Compliance Reviewer",
    description="Analyzes documents for compliance risks, ambiguities, and inconsistencies",
    version="1.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔥 Configurable region (default: india)
DEFAULT_REGION = os.getenv("COMPLIANCE_REGION", "india")

# Initialize components
parser = DocumentParser()
rule_engine = RuleEngine()
rag_engine = RAGEngine()
llm_analyzer = LLMAnalyzer()

# In-memory store
reports_store: dict[str, RiskReport] = {}


@app.post("/analyze-document", response_model=RiskReport)
async def analyze_document(file: UploadFile = File(...)):
    """
    Upload a PDF or plain text document for compliance analysis.
    Returns a structured risk report with section-level findings.
    """

    if file.content_type not in ["application/pdf", "text/plain"]:
        raise HTTPException(status_code=400, detail="Only PDF and plain text files are supported")

    content = await file.read()

    # 1. Parse document
    if file.content_type == "application/pdf":
        sections = parser.parse_pdf(content)
    else:
        sections = parser.parse_text(content.decode("utf-8"))

    if not sections:
        raise HTTPException(status_code=422, detail="Could not extract any content from document")

    # 🔥 2. RAG with REGION SUPPORT
    guideline_contexts = {}
    for section in sections:
        guideline_contexts[section["id"]] = rag_engine.retrieve(
            section["text"],
            top_k=3,
            region=DEFAULT_REGION  # 🔥 key upgrade
        )

    # 3. Rule engine
    rule_findings = rule_engine.analyze(sections)

    # 4. LLM analysis
    llm_findings = llm_analyzer.analyze_sections(sections, guideline_contexts)

    # 5. Build report
    report_id = str(uuid.uuid4())
    report = _build_report(
        report_id=report_id,
        filename=file.filename,
        sections=sections,
        rule_findings=rule_findings,
        llm_findings=llm_findings,
    )

    reports_store[report_id] = report
    return report


@app.get("/get-risk-report/{report_id}", response_model=RiskReport)
async def get_risk_report(report_id: str):
    if report_id not in reports_store:
        raise HTTPException(status_code=404, detail="Report not found")
    return reports_store[report_id]


@app.get("/reports", response_model=list[DocumentMeta])
async def list_reports():
    return [
        DocumentMeta(
            report_id=r.report_id,
            filename=r.filename,
            analyzed_at=r.analyzed_at,
            overall_risk=r.overall_risk,
            total_issues=len(r.findings),
        )
        for r in reports_store.values()
    ]


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.1.0"}


# ─────────────────────────────────────────────

def _build_report(report_id, filename, sections, rule_findings, llm_findings) -> RiskReport:
    all_findings = rule_findings + llm_findings

    # Deduplicate
    seen = set()
    unique_findings = []

    for f in all_findings:
        key = (f["section_id"], f["issue_type"][:40])
        if key not in seen:
            seen.add(key)
            unique_findings.append(f)

    # Risk score
    severity_weights = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
    total_weight = sum(severity_weights.get(f["severity"], 1) for f in unique_findings)
    max_weight = max(len(unique_findings) * 3, 1)

    risk_score = round(min(total_weight / max_weight * 100, 100), 1)

    if risk_score >= 70:
        overall_risk = "HIGH"
    elif risk_score >= 35:
        overall_risk = "MEDIUM"
    else:
        overall_risk = "LOW"

    return RiskReport(
        report_id=report_id,
        filename=filename,
        analyzed_at=datetime.utcnow().isoformat(),
        overall_risk=overall_risk,
        risk_score=risk_score,
        sections=[{"id": s["id"], "title": s["title"], "text": s["text"][:300]} for s in sections],
        findings=unique_findings,
        summary=f"Analyzed {len(sections)} sections. Found {len(unique_findings)} issues "
                f"({sum(1 for f in unique_findings if f['severity'] == 'HIGH')} high, "
                f"{sum(1 for f in unique_findings if f['severity'] == 'MEDIUM')} medium, "
                f"{sum(1 for f in unique_findings if f['severity'] == 'LOW')} low severity).",
    )


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)