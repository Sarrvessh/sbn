from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.policy_repository import PolicyRepository
from app.services.policy_service import PolicyService


def evaluate_governance(
    prompt: str, db: Session | None = None
) -> tuple[bool, list[str]]:
    """Evaluate prompt against policies. Falls back to hardcoded checks if no DB."""

    if db is not None:
        repo = PolicyRepository(db)
        service = PolicyService(repo)
        flagged, results = service.evaluate_prompt(prompt)
        reasons = []
        for r in results:
            if r.get("reason"):
                reasons.append(r["reason"])
        return flagged, reasons

    return _fallback_evaluate(prompt)


def _fallback_evaluate(prompt: str) -> tuple[bool, list[str]]:
    """Fallback hardcoded governance checks when DB policies aren't available."""
    import re

    reasons: list[str] = []
    lowered = prompt.lower()

    if "secret" in lowered:
        reasons.append("Contains restricted keyword: secret")

    if re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", prompt):
        reasons.append("Contains possible email address")

    if re.search(r"\b(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}\b", prompt):
        reasons.append("Contains possible phone number")

    if re.search(r"\b\d{3}-\d{2}-\d{4}\b", prompt):
        reasons.append("Contains possible SSN format")

    if re.search(r"\b(?:\d[ -]?){13,19}\b", prompt):
        reasons.append("Contains possible payment card pattern")

    api_key_re = re.compile(
        r"\b("
        r"sk-or-v1-[\w-]{20,}|"
        r"sk-ant-[\w-]{20,}|"
        r"sk-[\w-]{20,}|"
        r"fk-[\w-]{16,}|"
        r"AIza[\w-]{35}|"
        r"AKIA[\w-]{16}|"
        r"gh[pous]_[\w-]{20,}|"
        r"github_pat_[\w-]{40,}|"
        r"hf_[\w-]{20,}|"
        r"r8_[\w-]{20,}|"
        r"n8n_[\w-]{20,}|"
        r"xox[bprs]-[\w-]{20,}|"
        r"sbp_[\w-]{20,}|"
        r"pk\.[\w-]{30,}|"
        r"sk\.[\w-]{30,}|"
        r"AC[\w-]{30,}|"
        r"SG\.[\w-]{20,}|"
        r"whsec_[\w-]{20,}|"
        r"rk_live_[\w-]{20,}|"
        r"pat_[\w-]{20,}|"
        r"eyJ[\w-]+\.[\w-]+|"
        r"[\w-]{32,}"
        r")\b"
    )
    if api_key_re.search(prompt):
        reasons.append("Contains possible API key")

    return (len(reasons) > 0, reasons)
