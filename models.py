from pydantic import BaseModel
from typing import Optional


class AnalysisRequest(BaseModel):
    text: str
    document_type: Optional[str] = "general"  # terms, privacy_policy, contract, general


class Finding(BaseModel):
    section_id: str
    section_title: str
    issue_type: str          # e.g. "missing_disclosure", "ambiguous_language", "liability_gap"
    severity: str            # HIGH | MEDIUM | LOW
    description: str
    flagged_text: Optional[str] = None
    suggestion: Optional[str] = None
    source: str              # "rule_engine" | "llm" | "rag+llm"


class RiskReport(BaseModel):
    report_id: str
    filename: str
    analyzed_at: str
    overall_risk: str        # HIGH | MEDIUM | LOW
    risk_score: float        # 0–100
    sections: list[dict]
    findings: list[dict]
    summary: str


class DocumentMeta(BaseModel):
    report_id: str
    filename: str
    analyzed_at: str
    overall_risk: str
    total_issues: int
