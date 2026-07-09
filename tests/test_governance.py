"""Tests for fallback governance rules — no DB required."""

from __future__ import annotations

from app.services.governance_service import _fallback_evaluate


class TestFallbackGovernance:
    def test_clean_prompt(self):
        flagged, reasons = _fallback_evaluate("What is the weather today?")
        assert flagged is False
        assert reasons == []

    def test_secret_keyword(self):
        flagged, reasons = _fallback_evaluate("The secret is pizza")
        assert flagged is True
        assert any("secret" in r for r in reasons)

    def test_email_address(self):
        flagged, reasons = _fallback_evaluate("Contact me at user@example.com")
        assert flagged is True
        assert any("email" in r for r in reasons)

    def test_phone_number(self):
        flagged, reasons = _fallback_evaluate("Call me at 555-123-4567")
        assert flagged is True
        assert any("phone" in r for r in reasons)

    def test_ssn_pattern(self):
        flagged, reasons = _fallback_evaluate("My SSN is 123-45-6789")
        assert flagged is True
        assert any("SSN" in r for r in reasons)

    def test_api_key_openai(self):
        flagged, reasons = _fallback_evaluate("key is sk-proj-abcdef1234567890abcdef12")
        assert flagged is True
        assert any("API key" in r for r in reasons)

    def test_credit_card_pattern(self):
        flagged, reasons = _fallback_evaluate("4111111111111111")
        assert flagged is True
        assert any("card" in r for r in reasons)

    def test_multiple_flags(self):
        flagged, reasons = _fallback_evaluate("secret at user@test.com and 123-45-6789")
        assert flagged is True
        assert len(reasons) >= 3

    def test_case_insensitive_secret(self):
        flagged, reasons = _fallback_evaluate("SECRET is hidden")
        assert flagged is True
        assert any("secret" in r for r in reasons)

    def test_empty_prompt(self):
        flagged, reasons = _fallback_evaluate("")
        assert flagged is False
        assert reasons == []
