"""PII detection and redaction service — applied at query time."""

from __future__ import annotations

import re
from typing import Any

PII_PATTERNS: list[tuple[str, str, str]] = [
    ("email", r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "[EMAIL]"),
    ("phone", r"\b(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}\b", "[PHONE]"),
    ("ssn", r"\b\d{3}-\d{2}-\d{4}\b", "[SSN]"),
    ("credit_card", r"\b(?:\d[ -]?){13,19}\b", "[CARD]"),
    ("ip_address", r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "[IP]"),
    (
        "api_key",
        (
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
        ),
        "[API_KEY]",
    ),
]


def redact_text(text: str) -> str:
    for _name, pattern, replacement in PII_PATTERNS:
        text = re.sub(pattern, replacement, text)
    return text


def redact_dict(obj: dict[str, Any], fields: list[str] | None = None) -> dict[str, Any]:
    if fields is None:
        fields = ["prompt", "response", "prompt_preview", "response_preview", "input", "output", "content"]
    result = dict(obj)
    for key in fields:
        if key in result and isinstance(result[key], str):
            result[key] = redact_text(result[key])
    if "retrieval_documents" in result and isinstance(result["retrieval_documents"], list):
        redacted_docs: list[dict[str, Any]] = []
        for doc in result["retrieval_documents"]:
            if isinstance(doc, dict):
                redacted_docs.append(redact_dict(doc, fields=["content"]))
            else:
                redacted_docs.append(doc)
        result["retrieval_documents"] = redacted_docs
    return result
