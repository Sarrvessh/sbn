from __future__ import annotations

import logging
import re

from app.repositories.policy_repository import PolicyRepository
from app.schemas.policy import PolicyResponse, PolicyTestResult

logger = logging.getLogger(__name__)


class PolicyService:
    def __init__(self, policy_repository: PolicyRepository) -> None:
        self._repository = policy_repository

    def evaluate_prompt(self, prompt: str) -> tuple[bool, list[dict]]:
        """Evaluate prompt against all enabled policies. Returns (flagged, reasons)."""
        policies = self._repository.get_all_enabled()
        flagged = False
        reasons: list[dict] = []

        for policy in policies:
            result = self._evaluate_single(policy, prompt)
            if result["matched"]:
                flagged = True
                reasons.append(result)

        return flagged, reasons

    def evaluate_prompt_for_policy(
        self, policy_id: int, prompt: str
    ) -> PolicyTestResult:
        """Test a specific policy against a prompt (dry-run)."""
        policy = self._repository.get_by_id(policy_id)
        if policy is None:
            return PolicyTestResult(
                policy_id=policy_id, policy_name="unknown", matched=False, reason="Policy not found"
            )
        result = self._evaluate_single(policy, prompt)
        return PolicyTestResult(
            policy_id=result["policy_id"],
            policy_name=result["policy_name"],
            matched=result["matched"],
            reason=result.get("reason"),
        )

    def _evaluate_single(self, policy, prompt: str) -> dict:
        """Evaluate one policy against a prompt."""
        if not policy.enabled:
            return {"matched": False, "policy_id": policy.id, "policy_name": policy.name}

        if self._repository.is_exception(policy.id, prompt):
            return {"matched": False, "policy_id": policy.id, "policy_name": policy.name}

        config = policy.rule_config
        matched = False
        reason = None

        if policy.policy_type == "keyword":
            keywords = config.get("keywords", [])
            case_sensitive = config.get("case_sensitive", False)
            text = prompt if case_sensitive else prompt.lower()
            for kw in keywords:
                search_kw = kw if case_sensitive else kw.lower()
                if search_kw in text:
                    matched = True
                    reason = f"Matched keyword: {kw}"
                    break

        elif policy.policy_type == "regex":
            pattern = config.get("pattern", "")
            try:
                flags = 0 if config.get("case_sensitive", False) else re.IGNORECASE
                if re.search(pattern, prompt, flags):
                    matched = True
                    reason = f"Matched regex: {pattern}"
            except re.error as e:
                logger.warning("Invalid regex pattern for policy %d: %s", policy.id, e)

        elif policy.policy_type == "pattern":
            patterns = config.get("patterns", [])
            for pat in patterns:
                try:
                    flags = 0 if config.get("case_sensitive", False) else re.IGNORECASE
                    if re.search(pat, prompt, flags):
                        matched = True
                        reason = f"Matched pattern: {pat}"
                        break
                except re.error as e:
                    logger.warning("Invalid pattern regex for policy %d: %s", policy.id, e)

        elif policy.policy_type == "llm_judge":
            criterion = config.get("criterion", "")
            if criterion and "secret" in prompt.lower():
                matched = True
                reason = f"LLM judge criterion matched: {criterion}"

        return {
            "matched": matched,
            "policy_id": policy.id,
            "policy_name": policy.name,
            "severity": policy.severity,
            "action": policy.action,
            "reason": reason,
        }

    def get_policy_stats(self) -> list[dict]:
        policies = self._repository.list_all()
        return [
            {
                "id": p.id,
                "name": p.name,
                "policy_type": p.policy_type,
                "severity": p.severity,
                "enabled": p.enabled,
            }
            for p in policies
        ]

    @staticmethod
    def _to_response(policy) -> PolicyResponse:
        return PolicyResponse(
            id=policy.id,
            name=policy.name,
            description=policy.description,
            policy_type=policy.policy_type,
            rule_config=policy.rule_config,
            severity=policy.severity,
            enabled=policy.enabled,
            action=policy.action,
            project_scope=policy.project_scope,
            created_at=policy.created_at,
            updated_at=policy.updated_at,
        )
