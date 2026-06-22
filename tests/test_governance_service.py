from __future__ import annotations

from app.services.governance_service import evaluate_governance


class TestEvaluateGovernance:
    def test_clean_prompt_no_flags(self):
        flagged, reasons = evaluate_governance("What is the weather in London?")
        assert flagged is False
        assert reasons == []

    def test_detects_secret_keyword(self):
        flagged, reasons = evaluate_governance("The secret key is 12345")
        assert flagged is True
        assert any("secret" in r.lower() for r in reasons)

    def test_detects_email(self):
        flagged, reasons = evaluate_governance("Contact me at user@example.com")
        assert flagged is True
        assert any("email" in r.lower() for r in reasons)

    def test_detects_phone(self):
        flagged, reasons = evaluate_governance("Call me at +1 (555) 123-4567")
        assert flagged is True
        assert any("phone" in r.lower() for r in reasons)

    def test_detects_ssn(self):
        flagged, reasons = evaluate_governance("My SSN is 123-45-6789")
        assert flagged is True
        assert any("ssn" in r.lower() for r in reasons)

    def test_detects_credit_card(self):
        flagged, reasons = evaluate_governance("Card: 4111 1111 1111 1111")
        assert flagged is True
        assert any("card" in r.lower() for r in reasons)

    def test_multiple_reasons(self):
        flagged, reasons = evaluate_governance(
            "secret user@example.com +1-555-123-4567"
        )
        assert flagged is True
        assert len(reasons) >= 2

    def test_case_insensitive_secret(self):
        flagged, reasons = evaluate_governance("This is a SECRET message")
        assert flagged is True
