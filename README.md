# AI Policy & Compliance Reviewer

An AI-powered backend system that analyzes legal documents (T&Cs, privacy policies, contracts) 
for compliance risks, ambiguous language, and missing disclosures — combining LLM reasoning 
with a deterministic rule engine for high-accuracy results.

---

## Architecture

```
Document Upload
     │
     ▼
┌─────────────────┐
│ Document Parser │  ── PDF / plain text → sections
└────────┬────────┘
         │
    ┌────┴──────────────────────────┐
    │                               │
    ▼                               ▼
┌──────────┐               ┌─────────────────┐
│  Rule    │               │   RAG Engine    │
│  Engine  │               │ (SentenceTransf)│
│ (Regex / │               │ Retrieves top-k │
│ Keywords)│               │ guidelines      │
└────┬─────┘               └───────┬─────────┘
     │                             │
     │              ┌──────────────┘
     │              ▼
     │     ┌────────────────┐
     │     │  LLM Analyzer  │  ── Gemini 1.5 Flash (free tier)
     │     │  (Gemini API)  │
     │     └───────┬────────┘
     │             │
     └──────┬──────┘
            ▼
    ┌───────────────┐
    │ Risk Report   │  ── JSON response with section findings
    │ Builder       │
    └───────────────┘
```

---

## Quick Start

```bash
# 1. Clone and install
pip install -r requirements.txt

# 2. Set your Gemini API key (free at https://aistudio.google.com)
export GEMINI_API_KEY=your_key_here

# 3. Run
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`.
Interactive docs at `http://localhost:8000/docs`.

---

## API Endpoints

### `POST /analyze-document`
Upload a PDF or `.txt` file for compliance analysis.

```bash
curl -X POST http://localhost:8000/analyze-document \
  -F "file=@terms_of_service.pdf"
```

**Response:**
```json
{
  "report_id": "uuid",
  "filename": "terms.pdf",
  "overall_risk": "HIGH",
  "risk_score": 72.5,
  "summary": "Analyzed 8 sections. Found 11 issues (3 high, 5 medium, 3 low).",
  "findings": [
    {
      "section_id": "sec_003",
      "section_title": "4.2 Refund Policy",
      "issue_type": "ambiguous_refund_terms",
      "severity": "MEDIUM",
      "description": "Refund terms mentioned but no timeline or eligibility criteria defined.",
      "flagged_text": null,
      "suggestion": "Specify refund window (e.g., '30 days from purchase') and eligible conditions.",
      "source": "rule_engine"
    }
  ]
}
```

### `GET /get-risk-report/{report_id}`
Retrieve a previously generated report.

### `GET /reports`
List all analyzed documents.

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| Hybrid rule engine + LLM | Rules catch known patterns reliably; LLM handles nuance and novel issues |
| RAG with local embeddings | Grounded responses; no extra API calls; works offline |
| Section-level analysis | Precise attribution; LLM context window stays focused |
| Gemini free tier | Zero cost for portfolio/demo; `gemini-1.5-flash` is fast and capable |
| `response_mime_type: "application/json"` | Forces structured JSON output; eliminates parsing brittle |

---

## Tech Stack

| Layer | Technology |
|---|---|
| LLM | Google Gemini 1.5 Flash (free tier) |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` (local) |
| Backend | Python + FastAPI |
| PDF Parsing | pypdf |
| Storage | In-memory dict (swap for SQLite/PostgreSQL in prod) |

---

## Extending This

- **Add more rules** in `rule_engine.py` — just append to the `RULES` list
- **Expand guidelines** in `compliance_guidelines.json` — add regulation texts for RAG
- **Swap LLM** — `llm_analyzer.py` is easily swappable with OpenAI, Anthropic, etc.
- **Persistent storage** — replace `reports_store` dict in `main.py` with SQLite via SQLAlchemy
- **Frontend** — connect to the React UI in `/frontend`
