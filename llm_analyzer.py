import os
import json
import re
from typing import Optional

import google.generativeai as genai

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


SYSTEM_PROMPT = """You are a senior legal compliance analyst.

You specialize in:
- GDPR (EU)
- CCPA (USA)
- DPDP Act 2023 (India)
- Consumer Protection laws (India & global)

Your job is to identify:

1. COMPLIANCE RISKS
2. AMBIGUITIES
3. MISSING DISCLOSURES
4. INCONSISTENCIES
5. UNFAIR TERMS

IMPORTANT:
- Always ground your analysis in the provided guidelines
- If guidelines reference a regulation, include it in output

Return ONLY a JSON array.

Each item MUST contain:
- issue_type (snake_case)
- severity ("HIGH" | "MEDIUM" | "LOW")
- description
- flagged_text (exact phrase if possible)
- suggestion
- reason (why this is an issue)
- regulation_reference (e.g., "DPDP Act 2023", "GDPR Article 5")
"""


USER_TEMPLATE = """Analyze this document section.

Section Title: {title}

Section Text:
{text}

Relevant Compliance Guidelines:
{guidelines}

Instructions:
- Use guidelines to justify findings
- Include regulation_reference where applicable
- Do NOT return empty unless absolutely no issues exist

Return ONLY JSON array.
"""


class LLMAnalyzer:
    def __init__(self):
        if GEMINI_API_KEY:
            print("[LLMAnalyzer] Gemini initialized")
            genai.configure(api_key=GEMINI_API_KEY)

            self.model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                system_instruction=SYSTEM_PROMPT,
                generation_config={
                    "temperature": 0.3,  # 🔥 slightly higher = better outputs
                    "response_mime_type": "application/json"
                },
            )
        else:
            self.model = None
            print("[LLMAnalyzer] GEMINI_API_KEY not set. Skipping LLM.")

    def analyze_sections(self, sections: list[dict], guideline_contexts: dict) -> list[dict]:
        if not self.model:
            return []

        findings = []

        for section in sections:
            try:
                print(f"[LLM] Processing section: {section['id']}")

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
        guideline_text = "\n".join(
            f"- [{g.get('regulation', 'Best Practice')}] {g.get('text', '')}"
            for g in guidelines
        ) or "No guidelines available."

        prompt = USER_TEMPLATE.format(
            title=section["title"],
            text=section["text"][:2000],
            guidelines=guideline_text,
        )

        response = self.model.generate_content(prompt)

        raw = response.text.strip()
        print("[LLM RAW OUTPUT]:", raw[:300])  # debug

        items = self._safe_parse_json(raw)

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
                "reason": item.get("reason"),  # 🔥 NEW
                "regulation_reference": item.get("regulation_reference"),  # 🔥 NEW
                "source": "llm",
            })

        return findings

    def _safe_parse_json(self, raw: str):
        """Robust JSON parsing (handles Gemini quirks)"""

        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return data
        except:
            pass

        # fallback: extract JSON array
        try:
            match = re.search(r"\[.*\]", raw, re.DOTALL)
            if match:
                return json.loads(match.group())
        except:
            pass

        print("[LLMAnalyzer] Failed to parse JSON")
        return []