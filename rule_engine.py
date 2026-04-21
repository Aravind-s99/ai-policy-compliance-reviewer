import re
from typing import Optional


class RuleEngine:
    """
    Deterministic compliance rule checker.
    Runs regex/keyword/pattern checks that don't need LLM reasoning.
    These are fast, explainable, and always consistent.
    """

    RULES = [
        # ── DATA & PRIVACY ──────────────────────────────────────────────────
        {
            "id": "R001",
            "name": "missing_data_usage_disclosure",
            "pattern": None,
            "required_keywords": ["data", "personal information", "collect", "process"],
            "missing_keywords": ["purpose", "use your data", "how we use", "data usage"],
            "issue_type": "missing_disclosure",
            "severity": "HIGH",
            "description": "Section discusses data collection but does not disclose the purpose or how data will be used.",
            "suggestion": "Add a clear statement explaining the purpose for which personal data is collected and processed (e.g., 'We collect your data to...').",
        },
        {
            "id": "R002",
            "name": "missing_data_retention_period",
            "required_keywords": ["data", "personal information", "store", "retain"],
            "missing_keywords": ["retention period", "retain for", "stored for", "deleted after", "kept for"],
            "issue_type": "missing_retention_policy",
            "severity": "MEDIUM",
            "description": "Data retention or deletion timeline is not specified.",
            "suggestion": "Specify how long personal data is retained and under what conditions it is deleted (GDPR Article 5(1)(e) requirement).",
        },
        {
            "id": "R003",
            "name": "missing_third_party_sharing",
            "required_keywords": ["third party", "third-party", "partners", "affiliates", "share your"],
            "missing_keywords": ["consent", "opt-out", "you may opt", "your choice", "you can choose"],
            "issue_type": "missing_user_consent_mechanism",
            "severity": "HIGH",
            "description": "Third-party data sharing is mentioned without providing user opt-out or consent mechanism.",
            "suggestion": "Include an explicit opt-out option or consent mechanism when sharing data with third parties.",
        },
        # ── REFUND & PAYMENT ─────────────────────────────────────────────────
        {
            "id": "R004",
            "name": "vague_refund_policy",
            "required_keywords": ["refund", "return", "cancellation"],
            "missing_keywords": ["within", "days", "eligible", "process", "refund period"],
            "issue_type": "ambiguous_refund_terms",
            "severity": "MEDIUM",
            "description": "Refund or cancellation terms are mentioned but lack specific timelines or eligibility criteria.",
            "suggestion": "Specify the refund window (e.g., '30 days from purchase'), eligible conditions, and the refund processing timeline.",
        },
        {
            "id": "R005",
            "name": "missing_payment_dispute_process",
            "required_keywords": ["payment", "charge", "billing", "fee"],
            "missing_keywords": ["dispute", "chargeback", "contest", "billing issue", "contact us"],
            "issue_type": "missing_dispute_process",
            "severity": "MEDIUM",
            "description": "Payment terms do not describe how users can dispute charges.",
            "suggestion": "Add a payment dispute resolution process with contact information and expected resolution timeline.",
        },
        # ── LIABILITY ────────────────────────────────────────────────────────
        {
            "id": "R006",
            "name": "unlimited_liability_waiver",
            "pattern": re.compile(
                r"(no\s+liability|not\s+liable|disclaim\s+all\s+liability|exclude\s+all\s+liability)",
                re.IGNORECASE,
            ),
            "required_keywords": [],
            "missing_keywords": [],
            "issue_type": "overbroad_liability_exclusion",
            "severity": "HIGH",
            "description": "Blanket liability exclusion detected. Courts in many jurisdictions may not enforce unlimited disclaimers.",
            "suggestion": "Narrow the liability exclusion to specific circumstances and cap damages to a defined amount (e.g., 'limited to the amount paid in the 12 months preceding the claim').",
        },
        {
            "id": "R007",
            "name": "missing_limitation_of_liability_cap",
            "required_keywords": ["liability", "damages", "liable"],
            "missing_keywords": ["shall not exceed", "limited to", "maximum liability", "cap on liability"],
            "issue_type": "missing_liability_cap",
            "severity": "MEDIUM",
            "description": "Liability is discussed but no monetary cap or limit is defined.",
            "suggestion": "Define a maximum liability cap, typically linked to amounts paid by the user in a given period.",
        },
        # ── TERMINATION ──────────────────────────────────────────────────────
        {
            "id": "R008",
            "name": "unilateral_termination_without_notice",
            "required_keywords": ["terminate", "suspend", "revoke", "cancel your account"],
            "missing_keywords": ["notice", "prior notice", "days notice", "written notice", "without cause"],
            "issue_type": "missing_termination_notice",
            "severity": "MEDIUM",
            "description": "Service may be terminated/suspended without specifying notice period or cause.",
            "suggestion": "Define the notice period before termination (e.g., '30 days written notice') and the grounds for immediate termination.",
        },
        # ── GOVERNING LAW ────────────────────────────────────────────────────
        {
            "id": "R009",
            "name": "missing_governing_law",
            "required_keywords": ["agreement", "terms", "contract", "policy"],
            "missing_keywords": ["governing law", "jurisdiction", "laws of", "courts of"],
            "issue_type": "missing_governing_law",
            "severity": "LOW",
            "description": "Governing law or jurisdiction for dispute resolution is not specified.",
            "suggestion": "Add a governing law clause specifying which jurisdiction's laws apply and where disputes will be resolved.",
        },
        # ── INTELLECTUAL PROPERTY ─────────────────────────────────────────────
        {
            "id": "R010",
            "name": "broad_ip_assignment",
            "pattern": re.compile(
                r"(assign\s+all\s+(rights|ip|intellectual\s+property)|irrevocable.*license|worldwide.*royalty.free)",
                re.IGNORECASE,
            ),
            "required_keywords": [],
            "missing_keywords": [],
            "issue_type": "overbroad_ip_assignment",
            "severity": "HIGH",
            "description": "Potentially overbroad IP assignment or license grant detected.",
            "suggestion": "Limit IP grants to what is strictly necessary for service operation, and ensure users retain ownership of their content.",
        },
        # ── AMBIGUITY PATTERNS ───────────────────────────────────────────────
        {
            "id": "R011",
            "name": "vague_language_detected",
            "pattern": re.compile(
                r"\b(as\s+appropriate|reasonable\s+efforts|at\s+our\s+sole\s+discretion|"
                r"from\s+time\s+to\s+time|may\s+or\s+may\s+not|"
                r"without\s+limitation|including\s+but\s+not\s+limited\s+to)\b",
                re.IGNORECASE,
            ),
            "required_keywords": [],
            "missing_keywords": [],
            "issue_type": "ambiguous_language",
            "severity": "LOW",
            "description": "Vague or discretionary language detected that may create uncertainty.",
            "suggestion": "Replace vague terms with specific, measurable criteria where possible.",
        },
    ]

    def analyze(self, sections: list[dict]) -> list[dict]:
        """Run all rules against each section and return findings."""
        findings = []
        for section in sections:
            text = section["text"].lower()
            for rule in self.RULES:
                finding = self._check_rule(rule, section, text)
                if finding:
                    findings.append(finding)
        return findings

    def _check_rule(self, rule: dict, section: dict, text_lower: str) -> Optional[dict]:
        # Regex-based pattern check
        if rule.get("pattern"):
            match = rule["pattern"].search(section["text"])
            if match:
                return self._make_finding(rule, section, flagged_text=match.group(0))
            return None

        # Keyword-presence + missing-keyword check
        required = rule.get("required_keywords", [])
        missing = rule.get("missing_keywords", [])

        has_required = any(kw in text_lower for kw in required)
        if not has_required:
            return None

        has_missing = any(kw in text_lower for kw in missing)
        if has_missing:
            return None  # The required disclosure IS present → no issue

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
            "source": "rule_engine",
            "rule_id": rule["id"],
        }
