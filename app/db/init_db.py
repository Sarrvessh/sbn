"""Database initialization for PostgreSQL — tables, bootstrap keys, and seeds."""

from __future__ import annotations

import time

from sqlalchemy.exc import OperationalError

from app.core.config import settings
from app.db.models import Trace
from app.db.session import SessionLocal, engine
from app.repositories.api_key_repository import ApiKeyRepository
from app.repositories.escalation_rule_repository import EscalationRuleRepository
from app.repositories.policy_repository import PolicyRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.escalation import EscalationRuleCreate
from app.schemas.policy import PolicyCreateRequest


def initialize_database(max_retries: int = 10, retry_delay_seconds: int = 2) -> None:
    """Initialize PostgreSQL tables (with retry) and seed defaults."""
    _init_postgres(max_retries, retry_delay_seconds)


def _init_postgres(max_retries: int, retry_delay_seconds: int) -> None:
    """Create tables if they don't exist and seed API keys."""
    for attempt in range(1, max_retries + 1):
        try:
            from app.db.base import Base
            Base.metadata.create_all(bind=engine)
            _seed_bootstrap_api_keys()
            _seed_default_policies()
            return
        except OperationalError:
            if attempt == max_retries:
                raise
            time.sleep(retry_delay_seconds)


def backfill_projects() -> None:
    """Backfill projects table from distinct project names in traces table."""
    with SessionLocal() as db:
        repo = ProjectRepository(db)
        names = (
            db.query(Trace.project_name)
            .distinct()
            .order_by(Trace.project_name)
            .all()
        )
        for (name,) in names:
            if name:
                repo.get_or_create_by_name(name)
        db.commit()


def _seed_bootstrap_api_keys() -> None:
    """Ensure baseline API keys exist for local development and demos."""
    with SessionLocal() as db:
        repository = ApiKeyRepository(db)
        admin_key = settings.bootstrap_admin_api_key
        seeds = [
            (admin_key, "admin", None, "Bootstrap admin key"),
            (settings.bootstrap_analyst_api_key, "analyst",
             settings.bootstrap_analyst_project_scope, "Bootstrap analyst key"),
            (settings.bootstrap_viewer_api_key, "viewer",
             settings.bootstrap_viewer_project_scope, "Bootstrap viewer key"),
            (settings.bootstrap_ingest_api_key, "ingest", None, "Bootstrap ingest key"),
        ]
        for key, role, scope, description in seeds:
            if key:
                repository.upsert_bootstrap_key(
                    api_key=key, role=role, project_scope=scope, description=description,
                )
        db.commit()


def _seed_default_policies() -> None:
    """Seed default governance policies and escalation rules."""
    with SessionLocal() as db:
        policy_repo = PolicyRepository(db)

        default_policies = [
            PolicyCreateRequest(
                name="Block PII Emails",
                description="Blocks prompts containing email addresses",
                policy_type="regex",
                rule_config={"pattern": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"},
                severity="high",
                action="block",
            ),
            PolicyCreateRequest(
                name="Flag API Keys",
                description="Flags prompts containing potential API keys",
                policy_type="regex",
                rule_config={
                    "pattern": (
                        r"(sk-or-v1-[\w-]{20,}|"
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
                        r"[\w-]{32,})"
                    )
                },
                severity="medium",
                action="flag",
            ),
            PolicyCreateRequest(
                name="Flag Sensitive Keywords",
                description="Flags prompts with sensitive keywords",
                policy_type="keyword",
                rule_config={"keywords": ["secret", "password", "token", "key", "credential"]},
                severity="medium",
                action="flag",
            ),
        ]

        for policy in default_policies:
            existing = [p for p in policy_repo.list_all() if p.name == policy.name]
            if existing:
                ep = existing[0]
                if ep.rule_config != policy.rule_config:
                    ep.rule_config = policy.rule_config
                    ep.policy_type = policy.policy_type
            else:
                policy_repo.create(policy)

        escalation_repo = EscalationRuleRepository(db)
        default_rules = [
            EscalationRuleCreate(
                name="Blocked Content → Admin",
                description="Notify admins when content is blocked",
                rule_type="severity",
                rule_config={"severity": "high"},
                target_role="admin",
            ),
            EscalationRuleCreate(
                name="Flagged Content → Reviewer",
                description="Route flagged content to reviewers",
                rule_type="severity",
                rule_config={"severity": "medium"},
                target_role="reviewer",
            ),
        ]

        for rule in default_rules:
            existing = [r for r in escalation_repo.list_all() if r.name == rule.name]
            if not existing:
                escalation_repo.create(rule)

        db.commit()