import os
import json
from typing import Optional

import google.generativeai as genai

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

SYSTEM_PROMPT = """You are a senior legal compliance analyst specializing in terms of service, 
privacy policies, and commercial contracts. Your job is to identify:

1. COMPLIANCE RISKS — clauses that may violate GDPR, CCPA, consumer protection laws, or industry standards
2. AMBIGUITIES — vague language that could be interpreted in multiple ways and harm users
3. MISSING DISCLOSURES — required information that is absent (e.g., data retention periods, refund timelines)
4. INCONSISTENCIES — contradictions within or across sections
5. UNFAIR TERMS — clauses that disproportionately favor the drafting party

Always respond with a valid JSON array only. No preamble. No explanation outside JSON.
Each item must have these fields:
- issue_type: string (snake_case, e.g. "missing_data_retention")
- severity: "HIGH" | "MEDIUM" | "LOW"
- description: string (1-2 sentences, plain English)
- flagged_text: string | null (the exact problematic phrase if applicable)  
- suggestion: string (concrete improvement recommendation)
"""

USER_TEMPLATE = """Analyze this document section for compliance issues.

Section Title: {title}
Section Text:
{text}

Relevant Compliance Guidelines:
{guidelines}

Respond ONLY with a JSON array of findings. Return an empty array [] if no issues found."""


class LLMAnalyzer:
    """
    Uses Google Gemini (free tier) to analyze document sections semantically.
    Handles rate limits gracefully by catching exceptions per section.
    """

    def __init__(self):
        if GEMINI_API_KEY:
            genai.configure(api_key=GEMINI_API_KEY)
            self.model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                system_instruction=SYSTEM_PROMPT,
                generation_config={"temperature": 0.1, "response_mime_type": "application/json"},
            )
        else:
            self.model = None
            print("[LLMAnalyzer] GEMINI_API_KEY not set. LLM analysis will be skipped.")

    def analyze_sections(self, sections: list[dict], guideline_contexts: dict) -> list[dict]:
        """Analyze all sections and return merged findings list."""
        if not self.model:
            return []

        findings = []
        for section in sections:
            try:
                section_findings = self._analyze_one(
                    section=section,
                    guidelines=guideline_contexts.get(section["id"], []),
                )
                findings.extend(section_findings)
            except Exception as e:
                print(f"[LLMAnalyzer] Error on section {section['id']}: {e}")
                continue

        return findings

    def _analyze_one(self, section: dict, guidelines: list[dict]) -> list[dict]:
        """Analyze a single section and parse the JSON response."""
        guideline_text = "\n".join(
            f"- [{g.get('regulation', 'Best Practice')}] {g.get('text', '')}"
            for g in guidelines
        ) or "No specific guidelines retrieved."

        prompt = USER_TEMPLATE.format(
            title=section["title"],
            text=section["text"][:2000],  # Stay within token budget
            guidelines=guideline_text,
        )

        response = self.model.generate_content(prompt)
        raw = response.text.strip()

        # Parse JSON safely
        try:
            items = json.loads(raw)
            if not isinstance(items, list):
                return []
        except json.JSONDecodeError:
            # Try to extract JSON array from text
            start = raw.find("[")
            end = raw.rfind("]") + 1
            if start >= 0 and end > start:
                items = json.loads(raw[start:end])
            else:
                return []

        # Attach section metadata
        findings = []
        for item in items:
            if not isinstance(item, dict):
                continue
            findings.append({
                "section_id": section["id"],
                "section_title": section["title"],
                "issue_type": item.get("issue_type", "unknown"),
                "severity": item.get("severity", "LOW"),
                "description": item.get("description", ""),
                "flagged_text": item.get("flagged_text"),
                "suggestion": item.get("suggestion"),
                "source": "llm",
            })

        return findings
