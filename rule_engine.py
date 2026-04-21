import re
from typing import Optional


class RuleEngine:
    """
    Deterministic compliance rule checker.
    Fast, explainable, and consistent.
    Now enhanced with:
    - Indian compliance references
    - Reason field
    - Better explainability
    """

    RULES = [

        # ── DATA & PRIVACY ─────────────────────────────
        {
            "id": "R001",
            "issue_type": "missing_data_usage_disclosure",
            "severity": "HIGH",
            "required_keywords": ["data", "personal information", "collect"],
            "missing_keywords": ["purpose", "how we use", "data usage"],
            "description": "Data is collected but purpose of usage is not clearly defined.",
            "reason": "Users are not informed about how their personal data will be used.",
            "suggestion": "Clearly specify why and how user data is collected and processed.",
            "regulation_reference": "DPDP Act 2023, GDPR Article 5",
        },

        {
            "id": "R002",
            "issue_type": "missing_data_retention",
            "severity": "MEDIUM",
            "required_keywords": ["data", "store", "retain"],
            "missing_keywords": ["retain for", "deleted after", "retention period"],
            "description": "No data retention duration is specified.",
            "reason": "Users must know how long their data is stored.",
            "suggestion": "Add clear retention period and deletion policy.",
            "regulation_reference": "DPDP Act 2023, GDPR Article 5(1)(e)",
        },

        {
            "id": "R003",
            "issue_type": "missing_user_consent",
            "severity": "HIGH",
            "required_keywords": ["third party", "share"],
            "missing_keywords": ["consent", "opt-out", "you may choose"],
            "description": "Data sharing mentioned without user consent mechanism.",
            "reason": "User consent is mandatory before sharing personal data.",
            "suggestion": "Provide opt-in or opt-out options for data sharing.",
            "regulation_reference": "DPDP Act 2023, CCPA",
        },

        # ── REFUNDS & PAYMENTS ─────────────────────────
        {
            "id": "R004",
            "issue_type": "ambiguous_refund_terms",
            "severity": "MEDIUM",
            "required_keywords": ["refund", "return"],
            "missing_keywords": ["days", "eligible", "refund period"],
            "description": "Refund policy lacks clarity.",
            "reason": "Refund timelines and eligibility are not defined.",
            "suggestion": "Specify refund duration, eligibility, and process.",
            "regulation_reference": "Consumer Protection Act 2019",
        },

        {
            "id": "R005",
            "issue_type": "missing_payment_dispute_process",
            "severity": "MEDIUM",
            "required_keywords": ["payment", "charge"],
            "missing_keywords": ["dispute", "contact", "complaint"],
            "description": "No dispute resolution process for payments.",
            "reason": "Users need a way to challenge incorrect charges.",
            "suggestion": "Add dispute handling process with contact details.",
            "regulation_reference": "Consumer Protection Act 2019",
        },

        # ── LIABILITY ───────────────────────────────────
        {
            "id": "R006",
            "pattern": re.compile(
                r"(not liable|no liability|disclaim all liability)",
                re.IGNORECASE
            ),
            "issue_type": "overbroad_liability_exclusion",
            "severity": "HIGH",
            "description": "Unlimited liability disclaimer detected.",
            "reason": "Courts often reject blanket liability exclusions.",
            "suggestion": "Limit liability with a reasonable cap.",
            "regulation_reference": "Contract Law Best Practice",
        },

        {
            "id": "R007",
            "issue_type": "missing_liability_cap",
            "severity": "MEDIUM",
            "required_keywords": ["liability"],
            "missing_keywords": ["limited to", "maximum liability"],
            "description": "Liability discussed but no cap defined.",
            "reason": "Unlimited liability creates legal uncertainty.",
            "suggestion": "Define maximum liability cap.",
            "regulation_reference": "Contract Law Best Practice",
        },

        # ── TERMINATION ────────────────────────────────
        {
            "id": "R008",
            "issue_type": "missing_termination_notice",
            "severity": "MEDIUM",
            "required_keywords": ["terminate", "suspend"],
            "missing_keywords": ["notice", "prior notice"],
            "description": "Termination without notice defined.",
            "reason": "Users should be informed before service termination.",
            "suggestion": "Specify notice period before termination.",
            "regulation_reference": "Consumer Protection Act 2019",
        },

        # ── GOVERNING LAW ──────────────────────────────
        {
            "id": "R009",
            "issue_type": "missing_governing_law",
            "severity": "LOW",
            "required_keywords": ["agreement", "terms"],
            "missing_keywords": ["governing law", "jurisdiction"],
            "description": "No governing law defined.",
            "reason": "Legal disputes require defined jurisdiction.",
            "suggestion": "Specify governing law and jurisdiction.",
            "regulation_reference": "Contract Law Best Practice",
        },

        # ── AMBIGUITY ─────────────────────────────────
        {
            "id": "R010",
            "pattern": re.compile(
                r"\b(at our discretion|reasonable efforts|may or may not)\b",
                re.IGNORECASE
            ),
            "issue_type": "ambiguous_language",
            "severity": "LOW",
            "description": "Ambiguous language detected.",
            "reason": "Vague wording creates uncertainty for users.",
            "suggestion": "Use clear, measurable language.",
            "regulation_reference": "Consumer Protection Act 2019",
        },
    ]

    def analyze(self, sections: list[dict]) -> list[dict]:
        findings = []

        for section in sections:
            text_lower = section["text"].lower()

            for rule in self.RULES:
                finding = self._check_rule(rule, section, text_lower)
                if finding:
                    findings.append(finding)

        return findings

    def _check_rule(self, rule: dict, section: dict, text_lower: str) -> Optional[dict]:

        # Pattern-based rules
        if rule.get("pattern"):
            match = rule["pattern"].search(section["text"])
            if match:
                return self._make_finding(rule, section, match.group(0))
            return None

        required = rule.get("required_keywords", [])
        missing = rule.get("missing_keywords", [])

        if required and not any(kw in text_lower for kw in required):
            return None

        if missing and any(kw in text_lower for kw in missing):
            return None

        return self._make_finding(rule, section)

    def _make_finding(self, rule: dict, section: dict, flagged_text: str = None) -> dict:
        return {
            "section_id": section["id"],
            "section_title": section["title"],
            "issue_type": rule["issue_type"],
            "severity": rule["severity"],
            "description": rule["description"],
            "flagged_text": flagged_text,
            "suggestion": rule.get("suggestion"),
            "reason": rule.get("reason"),  # 🔥 NEW
            "regulation_reference": rule.get("regulation_reference"),  # 🔥 NEW
            "source": "rule_engine",
            "rule_id": rule["id"],
        }