"""Tests for PII redaction service."""
from __future__ import annotations

from app.services.pii_redaction_service import redact_dict, redact_text


class TestRedactText:
    def test_email(self):
        assert redact_text("Contact me at user@example.com") == "Contact me at [EMAIL]"

    def test_phone(self):
        assert redact_text("Call 555-123-4567 now") == "Call [PHONE] now"

    def test_ssn(self):
        assert redact_text("SSN: 123-45-6789") == "SSN: [SSN]"

    def test_credit_card(self):
        assert redact_text("Card: 4111-1111-1111-1111") == "Card: [CARD]"

    def test_ip_address(self):
        assert redact_text("From 192.168.1.1") == "From [IP]"

    def test_api_key(self):
        assert redact_text("sk-or-v1-abcdef1234567890abcdef1234567890abcdef12") == "[API_KEY]"
        assert redact_text("ghp_abcdefghijklmnopqrstuvwxyz1234567890") == "[API_KEY]"

    def test_multiple_pii(self):
        result = redact_text("email: user@test.com, phone: 555-000-1111")
        assert "[EMAIL]" in result
        assert "[PHONE]" in result

    def test_no_pii(self):
        text = "This is a normal message with no sensitive data."
        assert redact_text(text) == text


class TestRedactDict:
    def test_redacts_prompt(self):
        obj = {"prompt": "my email is a@b.com", "response": "ok"}
        result = redact_dict(obj)
        assert result["prompt"] == "my email is [EMAIL]"
        assert result["response"] == "ok"

    def test_redacts_response(self):
        obj = {"response": "call 555-111-2222"}
        result = redact_dict(obj)
        assert "[PHONE]" in result["response"]

    def test_redacts_retrieval_documents(self):
        obj = {"retrieval_documents": [{"content": "email: x@y.com", "title": "doc"}]}
        result = redact_dict(obj)
        assert result["retrieval_documents"][0]["content"] == "email: [EMAIL]"

    def test_skips_non_string(self):
        obj = {"prompt": 42}
        assert redact_dict(obj)["prompt"] == 42

    def test_custom_fields(self):
        obj = {"custom": "email: a@b.com"}
        result = redact_dict(obj, fields=["custom"])
        assert result["custom"] == "email: [EMAIL]"

    def test_empty_obj(self):
        assert redact_dict({}) == {}
