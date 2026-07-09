"""End-to-end API tests exercising the full FastAPI app with SQLite + MongoDB."""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Generator
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db.base import Base
from app.main import create_application
from app.repositories.api_key_repository import ApiKeyRepository, hash_api_key

TEST_MONGODB_URL = os.getenv("TEST_MONGODB_URL", "mongodb://localhost:27017/ai_observability_test")


@pytest.fixture(scope="module")
def db_path() -> Generator[str, None, None]:
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    path = tmp.name
    tmp.close()
    yield path
    try:
        Path(path).unlink(missing_ok=True)
    except PermissionError:
        pass


@pytest.fixture(scope="module")
def db_session(db_path: str) -> Generator[Session, None, None]:
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    _seed_bootstrap_keys(session)
    _seed_default_policies(session)
    yield session
    session.close()


@pytest.fixture(scope="module")
def client(db_session: Session, db_path: str) -> Generator[TestClient, None, None]:
    app = create_application()
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestSession = sessionmaker(bind=engine)

    def override_get_db() -> Generator[Session, None, None]:
        session = TestSession()
        try:
            yield session
        finally:
            session.close()

    from app.db.session import get_db
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture(scope="module")
def admin_headers() -> dict[str, str]:
    return {"X-API-Key": settings.bootstrap_admin_api_key}


@pytest.fixture(scope="module")
def analyst_headers() -> dict[str, str]:
    return {"X-API-Key": settings.bootstrap_analyst_api_key}


@pytest.fixture(scope="module")
def viewer_headers() -> dict[str, str]:
    return {"X-API-Key": settings.bootstrap_viewer_api_key}


@pytest.fixture(scope="module")
def ingest_headers() -> dict[str, str]:
    return {"X-API-Key": settings.bootstrap_ingest_api_key}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _seed_bootstrap_keys(db: Session) -> None:
    repo = ApiKeyRepository(db)
    seeds = [
        (settings.bootstrap_admin_api_key, "admin", None, "Bootstrap admin key"),
        (settings.bootstrap_analyst_api_key, "analyst", settings.bootstrap_analyst_project_scope, "Bootstrap analyst key"),
        (settings.bootstrap_viewer_api_key, "viewer", settings.bootstrap_viewer_project_scope, "Bootstrap viewer key"),
        (settings.bootstrap_ingest_api_key, "ingest", None, "Bootstrap ingest key"),
    ]
    for key, role, scope, desc in seeds:
        hashed = hash_api_key(key)
        existing = repo.get_active_by_hash(hashed)
        if existing is None:
            repo.upsert_bootstrap_key(api_key=key, role=role, project_scope=scope, description=desc)
    db.commit()


def _seed_default_policies(db: Session) -> None:
    from app.repositories.policy_repository import PolicyRepository
    from app.schemas.policy import PolicyCreateRequest
    from app.repositories.escalation_rule_repository import EscalationRuleRepository
    from app.schemas.escalation import EscalationRuleCreate
    repo = PolicyRepository(db)
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
            rule_config={"pattern": r"(sk-or-v1-[\w-]{20,}|sk-[\w-]{20,})"},
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
        existing = [p for p in repo.list_all() if p.name == policy.name]
        if not existing:
            repo.create(policy)

    erepo = EscalationRuleRepository(db)
    default_rules = [
        EscalationRuleCreate(
            name="Blocked Content \u2192 Admin",
            description="Notify admins when content is blocked",
            rule_type="severity", rule_config={"severity": "high"}, target_role="admin",
        ),
        EscalationRuleCreate(
            name="Flagged Content \u2192 Reviewer",
            description="Route flagged content to reviewers",
            rule_type="severity", rule_config={"severity": "medium"}, target_role="reviewer",
        ),
    ]
    for rule in default_rules:
        existing = [r for r in erepo.list_all() if r.name == rule.name]
        if not existing:
            erepo.create(rule)
    db.commit()


def unique_project() -> str:
    return f"e2e-test-{uuid4().hex[:8]}"


# ===================================================================
# Tests
# ===================================================================

class TestHealth:
    def test_health(self, client: TestClient) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestAuth:
    def test_no_auth(self, client: TestClient, admin_headers: dict) -> None:
        resp = client.get("/api/v1/projects")
        assert resp.status_code == 401

    def test_invalid_key(self, client: TestClient) -> None:
        resp = client.get("/api/v1/projects", headers={"X-API-Key": "bad-key"})
        assert resp.status_code == 401

    def test_list_api_keys(self, client: TestClient, admin_headers: dict) -> None:
        resp = client.get("/api/v1/auth/api-keys", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 4
        roles = [k["role"] for k in data]
        assert "admin" in roles

    def test_create_api_key(self, client: TestClient, admin_headers: dict) -> None:
        resp = client.post("/api/v1/auth/api-keys", headers=admin_headers, json={
            "role": "analyst",
            "project_scope": None,
            "description": "e2e test key",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["role"] == "analyst"
        assert data["description"] == "e2e test key"
        assert data["api_key"].startswith("sbn_analyst_")
        assert len(data["api_key"]) > 20

    def test_create_admin_key_with_scope_rejected(self, client: TestClient, admin_headers: dict) -> None:
        resp = client.post("/api/v1/auth/api-keys", headers=admin_headers, json={
            "role": "admin",
            "project_scope": "my-project",
            "description": "bad",
        })
        assert resp.status_code == 400

    def test_non_admin_cannot_list_keys(self, client: TestClient, viewer_headers: dict) -> None:
        resp = client.get("/api/v1/auth/api-keys", headers=viewer_headers)
        assert resp.status_code == 403


class TestProjects:
    def test_list_empty(self, client: TestClient, admin_headers: dict) -> None:
        resp = client.get("/api/v1/projects", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_create_project(self, client: TestClient, admin_headers: dict) -> None:
        pname = unique_project()
        resp = client.post("/api/v1/projects", headers=admin_headers, json={
            "name": pname,
            "description": "e2e test project",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == pname
        assert data["description"] == "e2e test project"
        assert data["id"] > 0

    def test_create_duplicate(self, client: TestClient, admin_headers: dict) -> None:
        pname = unique_project()
        client.post("/api/v1/projects", headers=admin_headers, json={"name": pname})
        resp = client.post("/api/v1/projects", headers=admin_headers, json={"name": pname})
        assert resp.status_code == 409

    def test_get_detail_not_found(self, client: TestClient, admin_headers: dict) -> None:
        resp = client.get("/api/v1/projects/non-existent", headers=admin_headers)
        assert resp.status_code == 404

    def test_delete_project(self, client: TestClient, admin_headers: dict) -> None:
        pname = unique_project()
        client.post("/api/v1/projects", headers=admin_headers, json={"name": pname})
        resp = client.delete(f"/api/v1/projects/{pname}", headers=admin_headers)
        assert resp.status_code == 204

    def test_viewer_can_list(self, client: TestClient, viewer_headers: dict) -> None:
        resp = client.get("/api/v1/projects", headers=viewer_headers)
        assert resp.status_code == 200

    def test_analyst_can_create(self, client: TestClient, analyst_headers: dict) -> None:
        pname = unique_project()
        resp = client.post("/api/v1/projects", headers=analyst_headers, json={
            "name": pname,
            "description": "created by analyst",
        })
        assert resp.status_code == 201

    def test_viewer_cannot_create(self, client: TestClient, viewer_headers: dict) -> None:
        resp = client.post("/api/v1/projects", headers=viewer_headers, json={
            "name": unique_project(),
        })
        assert resp.status_code == 403

    def test_ingest_role_cannot_create(self, client: TestClient, ingest_headers: dict) -> None:
        resp = client.post("/api/v1/projects", headers=ingest_headers, json={
            "name": unique_project(),
        })
        assert resp.status_code == 403


class TestTraces:
    """Requires MongoDB on localhost:27017."""

    @pytest.mark.integration
    def test_ingest_trace(self, client: TestClient, admin_headers: dict) -> None:
        rid = uuid4().hex
        resp = client.post("/api/v1/ingest", headers=admin_headers, json={
            "request_id": rid,
            "project_name": "e2e-traces",
            "prompt": "Hello world",
            "response": "Hi there",
            "model_name": "gpt-4o-mini",
            "total_tokens": 50,
            "cost": 0.002,
            "latency_ms": 123.45,
            "status": "success",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        assert resp.status_code == 201
        assert resp.json()["request_id"] == rid

    @pytest.mark.integration
    def test_ingest_invalid_payload(self, client: TestClient, admin_headers: dict) -> None:
        resp = client.post("/api/v1/ingest", headers=admin_headers, json={
            "request_id": "too-short",
            "project_name": "test",
            "prompt": "hi",
            "response": "",
            "model_name": "gpt-4",
            "latency_ms": -1,
            "status": "unknown",
        })
        assert resp.status_code == 422

    @pytest.mark.integration
    def test_get_trace_detail(self, client: TestClient, admin_headers: dict) -> None:
        rid = uuid4().hex
        client.post("/api/v1/ingest", headers=admin_headers, json={
            "request_id": rid,
            "project_name": "e2e-traces",
            "prompt": "Detail test",
            "response": "Detail response",
            "model_name": "gpt-4o-mini",
            "total_tokens": 30,
            "cost": 0.001,
            "latency_ms": 50.0,
            "status": "success",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        resp = client.get(f"/api/v1/traces/{rid}", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["request_id"] == rid
        assert data["prompt"] == "Detail test"
        assert data["status"] == "success"

    @pytest.mark.integration
    def test_trace_not_found(self, client: TestClient, admin_headers: dict) -> None:
        resp = client.get("/api/v1/traces/nonexistent-request-id", headers=admin_headers)
        assert resp.status_code == 404

    @pytest.mark.integration
    def test_flag_and_unflag(self, client: TestClient, admin_headers: dict) -> None:
        rid = uuid4().hex
        client.post("/api/v1/ingest", headers=admin_headers, json={
            "request_id": rid,
            "project_name": "e2e-traces",
            "prompt": "Flag me",
            "response": "OK",
            "model_name": "gpt-4o-mini",
            "total_tokens": 10,
            "cost": 0.0005,
            "latency_ms": 30.0,
            "status": "success",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        flag = client.post(f"/api/v1/traces/{rid}/flag", headers=admin_headers)
        assert flag.status_code == 200
        assert flag.json()["flagged_for_governance"] is True

        unflag = client.post(f"/api/v1/traces/{rid}/unflag", headers=admin_headers)
        assert unflag.status_code == 200
        assert unflag.json()["flagged_for_governance"] is False

    @pytest.mark.integration
    def test_redact_param(self, client: TestClient, admin_headers: dict) -> None:
        rid = uuid4().hex
        client.post("/api/v1/ingest", headers=admin_headers, json={
            "request_id": rid,
            "project_name": "e2e-traces",
            "prompt": "My email is test@example.com",
            "response": "Noted",
            "model_name": "gpt-4o-mini",
            "total_tokens": 10,
            "cost": 0.0005,
            "latency_ms": 30.0,
            "status": "success",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        resp = client.get(f"/api/v1/traces/{rid}?redact=true", headers=admin_headers)
        assert resp.status_code == 200
        assert "***" in resp.json()["prompt"] or "[REDACTED]" in resp.json()["prompt"] or "[EMAIL]" in resp.json()["prompt"]

    @pytest.mark.integration
    def test_recent_traces(self, client: TestClient, admin_headers: dict) -> None:
        resp = client.get("/api/v1/traces/recent?limit=10", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    @pytest.mark.integration
    def test_export_json(self, client: TestClient, admin_headers: dict) -> None:
        resp = client.get("/api/v1/export/traces?format=json", headers=admin_headers)
        assert resp.status_code == 200
        data = json.loads(resp.content)
        assert isinstance(data, list)

    @pytest.mark.integration
    def test_export_csv(self, client: TestClient, admin_headers: dict) -> None:
        resp = client.get("/api/v1/export/traces?format=csv", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "text/csv; charset=utf-8"
        assert resp.text.startswith("request_id")

    @pytest.mark.integration
    def test_export_batch(self, client: TestClient, admin_headers: dict) -> None:
        resp = client.get("/api/v1/export/traces/batch?limit=10", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert "next_cursor" in data
        assert "has_more" in data

    @pytest.mark.integration
    def test_ingest_auto_creates_project(self, client: TestClient, admin_headers: dict) -> None:
        pname = f"auto-project-{uuid4().hex[:8]}"
        rid = uuid4().hex
        client.post("/api/v1/ingest", headers=admin_headers, json={
            "request_id": rid,
            "project_name": pname,
            "prompt": "Auto project test",
            "response": "OK",
            "model_name": "gpt-4o-mini",
            "total_tokens": 10,
            "cost": 0.001,
            "latency_ms": 25.0,
            "status": "success",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        resp = client.get(f"/api/v1/projects/{pname}", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == pname


class TestSpans:
    @pytest.mark.integration
    def test_create_and_list_spans(self, client: TestClient, admin_headers: dict) -> None:
        rid = uuid4().hex
        client.post("/api/v1/ingest", headers=admin_headers, json={
            "request_id": rid,
            "project_name": "e2e-spans",
            "prompt": "Span test",
            "response": "Span response",
            "model_name": "gpt-4o-mini",
            "total_tokens": 20,
            "cost": 0.001,
            "latency_ms": 40.0,
            "status": "success",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        resp = client.get(f"/api/v1/traces/{rid}/spans", headers=admin_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestGovernance:
    def test_list_policies(self, client: TestClient, admin_headers: dict) -> None:
        resp = client.get("/api/v1/policies", headers=admin_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 3
        names = [p["name"] for p in resp.json()]
        assert "Block PII Emails" in names

    def test_create_policy(self, client: TestClient, admin_headers: dict) -> None:
        resp = client.post("/api/v1/policies", headers=admin_headers, json={
            "name": "e2e-block-ssn",
            "description": "Block SSNs",
            "policy_type": "regex",
            "rule_config": {"pattern": r"\b\d{3}-\d{2}-\d{4}\b"},
            "severity": "high",
            "action": "block",
            "enabled": True,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "e2e-block-ssn"
        assert data["action"] == "block"
        assert data["enabled"] is True

    def test_get_policy(self, client: TestClient, admin_headers: dict) -> None:
        created = client.post("/api/v1/policies", headers=admin_headers, json={
            "name": "e2e-get-policy",
            "policy_type": "keyword",
            "rule_config": {"keywords": ["test"]},
            "severity": "low",
            "action": "flag",
        }).json()
        resp = client.get(f"/api/v1/policies/{created['id']}", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "e2e-get-policy"

    def test_update_policy(self, client: TestClient, admin_headers: dict) -> None:
        created = client.post("/api/v1/policies", headers=admin_headers, json={
            "name": "e2e-update-me",
            "policy_type": "keyword",
            "rule_config": {"keywords": ["old"]},
            "severity": "low",
            "action": "flag",
        }).json()
        resp = client.put(f"/api/v1/policies/{created['id']}", headers=admin_headers, json={
            "name": "e2e-updated",
            "severity": "high",
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == "e2e-updated"
        assert resp.json()["severity"] == "high"

    def test_delete_policy(self, client: TestClient, admin_headers: dict) -> None:
        created = client.post("/api/v1/policies", headers=admin_headers, json={
            "name": "e2e-delete-me",
            "policy_type": "keyword",
            "rule_config": {"keywords": ["delete"]},
            "severity": "low",
            "action": "flag",
        }).json()
        resp = client.delete(f"/api/v1/policies/{created['id']}", headers=admin_headers)
        assert resp.status_code == 204
        resp = client.get(f"/api/v1/policies/{created['id']}", headers=admin_headers)
        assert resp.status_code == 404

    def test_policy_test_match(self, client: TestClient, admin_headers: dict) -> None:
        resp = client.post("/api/v1/policies/test", headers=admin_headers, json={
            "prompt": "My secret password is 123",
        })
        assert resp.status_code == 200
        results = resp.json()
        matched = [r for r in results if r["matched"]]
        assert len(matched) >= 1
        assert any("secret" in (r.get("reason") or "") or r.get("policy_name") == "Flag Sensitive Keywords" for r in matched)

    def test_policy_test_no_match(self, client: TestClient, admin_headers: dict) -> None:
        resp = client.post("/api/v1/policies/test", headers=admin_headers, json={
            "prompt": "Hello, this is a harmless message about the weather.",
        })
        assert resp.status_code == 200
        matched = [r for r in resp.json() if r["matched"]]
        assert len(matched) == 0

    def test_single_policy_test(self, client: TestClient, admin_headers: dict) -> None:
        created = client.post("/api/v1/policies", headers=admin_headers, json={
            "name": "e2e-single-test",
            "policy_type": "keyword",
            "rule_config": {"keywords": ["urgent"]},
            "severity": "medium",
            "action": "flag",
        }).json()
        resp = client.post(f"/api/v1/policies/{created['id']}/test", headers=admin_headers, json={
            "prompt": "This is urgent",
        })
        assert resp.status_code == 200
        assert resp.json()["matched"] is True
        assert resp.json()["policy_id"] == created["id"]

    def test_evaluate_endpoint(self, client: TestClient, admin_headers: dict) -> None:
        resp = client.post("/api/v1/policies/evaluate", headers=admin_headers, json={
            "prompt": "My email is user@example.com",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["decision"] in ("allow", "flag", "block", "require_approval")

    def test_policy_exceptions(self, client: TestClient, admin_headers: dict) -> None:
        created = client.post("/api/v1/policies", headers=admin_headers, json={
            "name": "e2e-exc-test",
            "policy_type": "keyword",
            "rule_config": {"keywords": ["bypass"]},
            "severity": "medium",
            "action": "flag",
        })
        assert created.status_code == 201, created.text
        pid = created.json()["id"]
        exc = client.post(f"/api/v1/policies/{pid}/exceptions", headers=admin_headers, json={
            "pattern": "safe-bypass",
            "reason": "e2e test exception",
        })
        assert exc.status_code == 201, exc.text
        assert exc.json()["pattern"] == "safe-bypass"

        exc_list = client.get(f"/api/v1/policies/{pid}/exceptions", headers=admin_headers)
        assert exc_list.status_code == 200
        assert len(exc_list.json()) >= 1

        eid = exc.json()["id"]
        delete = client.delete(f"/api/v1/exceptions/{eid}", headers=admin_headers)
        assert delete.status_code == 204

    def test_analyst_can_list_policies(self, client: TestClient, analyst_headers: dict) -> None:
        resp = client.get("/api/v1/policies", headers=analyst_headers)
        assert resp.status_code == 200

    def test_viewer_cannot_create_policy(self, client: TestClient, viewer_headers: dict) -> None:
        resp = client.post("/api/v1/policies", headers=viewer_headers, json={
            "name": "should-fail",
            "policy_type": "keyword",
            "rule_config": {"keywords": ["x"]},
            "severity": "low",
            "action": "flag",
        })
        assert resp.status_code == 403


class TestOversight:
    """Requires MongoDB for pending/reviewed trace listing."""

    @pytest.mark.integration
    def test_pending_reviews_empty(self, client: TestClient, admin_headers: dict) -> None:
        resp = client.get("/api/v1/reviews/pending", headers=admin_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.integration
    def test_review_workflow(self, client: TestClient, admin_headers: dict) -> None:
        rid = uuid4().hex
        client.post("/api/v1/ingest", headers=admin_headers, json={
            "request_id": rid,
            "project_name": "e2e-review",
            "prompt": "Review test with secret data",
            "response": "Reviewed response",
            "model_name": "gpt-4o-mini",
            "total_tokens": 30,
            "cost": 0.001,
            "latency_ms": 40.0,
            "status": "success",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        flagged = client.post(f"/api/v1/traces/{rid}/flag", headers=admin_headers)
        assert flagged.status_code == 200

        review = client.post("/api/v1/reviews", headers=admin_headers, json={
            "request_id": rid,
            "reviewer": "e2e-test",
            "decision": "approved",
            "notes": "Looks good",
        })
        assert review.status_code == 201
        assert review.json()["decision"] == "approved"

        reviews_for_trace = client.get(f"/api/v1/traces/{rid}/reviews", headers=admin_headers)
        assert reviews_for_trace.status_code == 200
        assert len(reviews_for_trace.json()) >= 1

    @pytest.mark.integration
    def test_reviewed_traces(self, client: TestClient, admin_headers: dict) -> None:
        resp = client.get("/api/v1/reviews/reviewed", headers=admin_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_audit_log(self, client: TestClient, admin_headers: dict) -> None:
        resp = client.get("/api/v1/audit-log", headers=admin_headers)
        assert resp.status_code == 200
        log = resp.json()
        assert isinstance(log, list)

    def test_escalation_rules_crud(self, client: TestClient, admin_headers: dict) -> None:
        created = client.post("/api/v1/escalation-rules", headers=admin_headers, json={
            "name": "e2e-escalation",
            "description": "E2E test rule",
            "rule_type": "severity",
            "rule_config": {"severity": "high"},
            "target_role": "admin",
        })
        assert created.status_code == 201
        eid = created.json()["id"]

        listed = client.get("/api/v1/escalation-rules", headers=admin_headers)
        assert listed.status_code == 200
        ids = [r["id"] for r in listed.json()]
        assert eid in ids

        updated = client.put(f"/api/v1/escalation-rules/{eid}", headers=admin_headers, json={
            "target_role": "reviewer",
        })
        assert updated.status_code == 200
        assert updated.json()["target_role"] == "reviewer"

        deleted = client.delete(f"/api/v1/escalation-rules/{eid}", headers=admin_headers)
        assert deleted.status_code == 204

        get_deleted = client.get(f"/api/v1/escalation-rules/{eid}", headers=admin_headers)
        assert get_deleted.status_code == 404

    @pytest.mark.integration
    def test_escalated_reviews(self, client: TestClient, admin_headers: dict) -> None:
        resp = client.get("/api/v1/reviews/escalated", headers=admin_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestAnalytics:
    @pytest.mark.integration
    def test_realtime_metrics(self, client: TestClient, admin_headers: dict) -> None:
        resp = client.get("/api/v1/analytics/realtime", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_cost" in data
        assert "governance_flagged_count" in data

    @pytest.mark.integration
    def test_governance_metrics(self, client: TestClient, admin_headers: dict) -> None:
        resp = client.get("/api/v1/analytics/governance", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "flag_rate" in data
        assert "by_severity" in data

    @pytest.mark.integration
    def test_system_metrics(self, client: TestClient, admin_headers: dict) -> None:
        resp = client.get("/api/v1/analytics/system", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "uptime_hours" in data
        assert "total_projects" in data

    @pytest.mark.integration
    def test_cost_analytics(self, client: TestClient, admin_headers: dict) -> None:
        resp = client.get("/api/v1/analytics/costs", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "daily_costs" in data

    @pytest.mark.integration
    def test_cost_prediction(self, client: TestClient, admin_headers: dict) -> None:
        resp = client.get("/api/v1/analytics/costs/predicted", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "projected_monthly_cost" in data
        assert "confidence" in data
        assert "daily_predictions" in data

    @pytest.mark.integration
    def test_alerts_endpoint(self, client: TestClient, admin_headers: dict) -> None:
        resp = client.get("/api/v1/alerts", headers=admin_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_metrics_endpoint(self, client: TestClient, admin_headers: dict) -> None:
        resp = client.get("/api/v1/metrics", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_cost" in data
        assert "governance_flagged_count" in data


class TestWebhooks:
    def test_create_webhook(self, client: TestClient, admin_headers: dict) -> None:
        resp = client.post("/api/v1/webhooks", headers=admin_headers, json={
            "name": "e2e-webhook",
            "url": "https://example.com/webhook",
            "secret": "whsec_test123",
            "events": ["alert.high_latency", "trace.ingested"],
            "enabled": True,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "e2e-webhook"
        assert data["url"] == "https://example.com/webhook"
        assert "alert.high_latency" in data["events"]

    def test_list_webhooks(self, client: TestClient, admin_headers: dict) -> None:
        resp = client.get("/api/v1/webhooks", headers=admin_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_update_webhook(self, client: TestClient, admin_headers: dict) -> None:
        created = client.post("/api/v1/webhooks", headers=admin_headers, json={
            "name": "e2e-wh-update",
            "url": "https://example.com/old",
            "events": ["alert.high_latency"],
            "enabled": False,
        }).json()
        wid = created["id"]
        resp = client.put(f"/api/v1/webhooks/{wid}", headers=admin_headers, json={
            "name": "e2e-wh-updated",
            "enabled": True,
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == "e2e-wh-updated"
        assert resp.json()["enabled"] is True

    def test_get_deliveries_empty(self, client: TestClient, admin_headers: dict) -> None:
        created = client.post("/api/v1/webhooks", headers=admin_headers, json={
            "name": "e2e-wh-delivery",
            "url": "https://example.com/del",
            "events": ["alert.high_latency"],
            "enabled": True,
        }).json()
        resp = client.get(f"/api/v1/webhooks/{created['id']}/deliveries", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_delete_webhook(self, client: TestClient, admin_headers: dict) -> None:
        created = client.post("/api/v1/webhooks", headers=admin_headers, json={
            "name": "e2e-wh-delete",
            "url": "https://example.com/del",
            "events": ["alert.high_latency"],
            "enabled": True,
        })
        assert created.status_code == 201, created.text
        wid = created.json()["id"]
        resp = client.delete(f"/api/v1/webhooks/{wid}", headers=admin_headers)
        assert resp.status_code == 204
        # Verify it's gone by checking list
        all_hooks = client.get("/api/v1/webhooks", headers=admin_headers).json()
        ids = [h["id"] for h in all_hooks]
        assert wid not in ids

    def test_webhook_test_endpoint(self, client: TestClient, admin_headers: dict) -> None:
        resp = client.post("/api/v1/webhooks/test", headers=admin_headers, json={
            "url": "https://httpbin.org/post",
            "secret": None,
        })
        # May fail because httpbin might not be reachable — check structure
        assert resp.status_code in (200, 502)

    def test_non_admin_cannot_create(self, client: TestClient, viewer_headers: dict) -> None:
        resp = client.post("/api/v1/webhooks", headers=viewer_headers, json={
            "name": "should-fail",
            "url": "https://example.com",
            "events": ["alert.high_latency"],
            "enabled": True,
        })
        assert resp.status_code == 403

    def test_analyst_can_list(self, client: TestClient, analyst_headers: dict) -> None:
        resp = client.get("/api/v1/webhooks", headers=analyst_headers)
        assert resp.status_code == 200


class TestAlertRules:
    def test_create_alert_rule(self, client: TestClient, admin_headers: dict) -> None:
        resp = client.post("/api/v1/alert-rules", headers=admin_headers, json={
            "name": "e2e-high-latency",
            "alert_type": "latency",
            "threshold_value": 2000.0,
            "project_name": None,
            "enabled": True,
        })
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["name"] == "e2e-high-latency"
        assert data["threshold_value"] == 2000.0

    def test_list_alert_rules(self, client: TestClient, admin_headers: dict) -> None:
        resp = client.get("/api/v1/alert-rules", headers=admin_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_update_alert_rule(self, client: TestClient, admin_headers: dict) -> None:
        created = client.post("/api/v1/alert-rules", headers=admin_headers, json={
            "name": "e2e-update-rule",
            "alert_type": "latency",
            "threshold_value": 1000.0,
            "project_name": None,
            "enabled": True,
        })
        assert created.status_code == 201, created.text
        rid = created.json()["id"]
        resp = client.put(f"/api/v1/alert-rules/{rid}", headers=admin_headers, json={
            "threshold_value": 3000.0,
            "enabled": False,
        })
        assert resp.status_code == 200
        assert resp.json()["threshold_value"] == 3000.0
        assert resp.json()["enabled"] is False

    def test_delete_alert_rule(self, client: TestClient, admin_headers: dict) -> None:
        created = client.post("/api/v1/alert-rules", headers=admin_headers, json={
            "name": "e2e-delete-rule",
            "alert_type": "latency",
            "threshold_value": 500.0,
            "project_name": None,
            "enabled": True,
        })
        assert created.status_code == 201, created.text
        rid = created.json()["id"]
        resp = client.delete(f"/api/v1/alert-rules/{rid}", headers=admin_headers)
        assert resp.status_code == 204
        all_rules = client.get("/api/v1/alert-rules", headers=admin_headers).json()
        ids = [r["id"] for r in all_rules]
        assert rid not in ids

    def test_project_specific_rule(self, client: TestClient, admin_headers: dict) -> None:
        pname = unique_project()
        resp = client.post("/api/v1/alert-rules", headers=admin_headers, json={
            "name": "e2e-project-rule",
            "alert_type": "cost",
            "threshold_value": 0.50,
            "project_name": pname,
            "enabled": True,
        })
        assert resp.status_code == 201, resp.text
        assert resp.json()["project_name"] == pname

    def test_non_admin_cannot_create(self, client: TestClient, viewer_headers: dict) -> None:
        resp = client.post("/api/v1/alert-rules", headers=viewer_headers, json={
            "name": "fail",
            "alert_type": "latency",
            "threshold_value": 100.0,
            "project_name": None,
            "enabled": True,
        })
        assert resp.status_code == 403


class TestTeamsAndBudgets:
    def test_teams_crud(self, client: TestClient, admin_headers: dict) -> None:
        created = client.post("/api/v1/teams", headers=admin_headers, json={
            "name": "e2e-team-alpha",
            "description": "Alpha team",
        })
        assert created.status_code == 201
        tid = created.json()["id"]

        listed = client.get("/api/v1/teams", headers=admin_headers)
        assert listed.status_code == 200
        ids = [t["id"] for t in listed.json()]
        assert tid in ids

        get_resp = client.get(f"/api/v1/teams/{tid}", headers=admin_headers)
        assert get_resp.status_code == 200
        assert get_resp.json()["name"] == "e2e-team-alpha"

        updated = client.put(f"/api/v1/teams/{tid}", headers=admin_headers, json={
            "name": "e2e-team-alpha-renamed",
        })
        assert updated.status_code == 200
        assert updated.json()["name"] == "e2e-team-alpha-renamed"

        deleted = client.delete(f"/api/v1/teams/{tid}", headers=admin_headers)
        assert deleted.status_code == 204

        get_deleted = client.get(f"/api/v1/teams/{tid}", headers=admin_headers)
        assert get_deleted.status_code == 404

    def test_team_project_assignment(self, client: TestClient, admin_headers: dict) -> None:
        team = client.post("/api/v1/teams", headers=admin_headers, json={
            "name": "e2e-team-proj",
        }).json()
        tid = team["id"]
        pname = unique_project()
        client.post("/api/v1/projects", headers=admin_headers, json={"name": pname})

        assign = client.post(f"/api/v1/teams/{tid}/projects", headers=admin_headers, json={
            "project_name": pname,
        })
        assert assign.status_code == 201
        assert assign.json()["project_name"] == pname

        projects = client.get(f"/api/v1/teams/{tid}/projects", headers=admin_headers)
        assert projects.status_code == 200
        assert pname in [p["project_name"] for p in projects.json()]

        remove = client.delete(f"/api/v1/teams/{tid}/projects?project_name={pname}", headers=admin_headers)
        assert remove.status_code == 204

    def test_budgets_crud(self, client: TestClient, admin_headers: dict) -> None:
        team = client.post("/api/v1/teams", headers=admin_headers, json={"name": "e2e-budget-team"})
        assert team.status_code == 201, team.text
        tid = team.json()["id"]
        budget = client.post("/api/v1/budgets", headers=admin_headers, json={
            "team_id": tid,
            "month": "2026-06",
            "budget_cents": 100000,
        })
        assert budget.status_code == 201, budget.text
        bid = budget.json()["id"]
        assert budget.json()["budget_cents"] == 100000

        listed = client.get("/api/v1/budgets", headers=admin_headers)
        assert listed.status_code == 200
        ids = [b["id"] for b in listed.json()]
        assert bid in ids

        updated = client.put(f"/api/v1/budgets/{bid}", headers=admin_headers, json={"budget_cents": 200000})
        assert updated.status_code == 200
        assert updated.json()["budget_cents"] == 200000

        deleted = client.delete(f"/api/v1/budgets/{bid}", headers=admin_headers)
        assert deleted.status_code == 204

    def test_budget_duplicate_month(self, client: TestClient, admin_headers: dict) -> None:
        team = client.post("/api/v1/teams", headers=admin_headers, json={"name": "e2e-dup-budget"})
        assert team.status_code == 201, team.text
        tid = team.json()["id"]
        client.post("/api/v1/budgets", headers=admin_headers, json={
            "team_id": tid, "month": "2026-07", "budget_cents": 50000,
        })
        dup = client.post("/api/v1/budgets", headers=admin_headers, json={
            "team_id": tid, "month": "2026-07", "budget_cents": 60000,
        })
        assert dup.status_code == 409

    def test_team_costs_endpoint(self, client: TestClient, admin_headers: dict) -> None:
        resp = client.get("/api/v1/analytics/costs/teams", headers=admin_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.integration
    def test_team_costs_with_data(self, client: TestClient, admin_headers: dict) -> None:
        resp = client.get("/api/v1/analytics/costs/teams", headers=admin_headers)
        assert resp.status_code == 200


class TestSettings:
    def test_get_settings(self, client: TestClient, admin_headers: dict) -> None:
        resp = client.get("/api/v1/settings", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "budget_alert_threshold_pct" in data

    def test_update_settings(self, client: TestClient, admin_headers: dict) -> None:
        resp = client.put("/api/v1/settings", headers=admin_headers, json={
            "budget_alert_threshold_pct": 90.0,
        })
        assert resp.status_code == 200
        assert resp.json()["budget_alert_threshold_pct"] == 90.0

    def test_non_admin_cannot_update(self, client: TestClient, viewer_headers: dict) -> None:
        resp = client.put("/api/v1/settings", headers=viewer_headers, json={
            "latency_alert_threshold_ms": 100.0,
        })
        assert resp.status_code == 403

    def test_viewer_cannot_get(self, client: TestClient, viewer_headers: dict) -> None:
        resp = client.get("/api/v1/settings", headers=viewer_headers)
        assert resp.status_code == 403


class TestRBACEnforcement:
    def test_admin_can_delete_project(self, client: TestClient, admin_headers: dict, analyst_headers: dict) -> None:
        pname = unique_project()
        client.post("/api/v1/projects", headers=admin_headers, json={"name": pname})
        resp = client.delete(f"/api/v1/projects/{pname}", headers=analyst_headers)
        assert resp.status_code == 403

    def test_ingest_cannot_access_reviews(self, client: TestClient, ingest_headers: dict) -> None:
        resp = client.get("/api/v1/reviews/pending", headers=ingest_headers)
        assert resp.status_code == 403

    def test_viewer_cannot_flag(self, client: TestClient, viewer_headers: dict) -> None:
        resp = client.post("/api/v1/traces/fake-id/flag", headers=viewer_headers)
        assert resp.status_code == 403

    def test_analyst_can_access_reviews(self, client: TestClient, analyst_headers: dict) -> None:
        resp = client.get("/api/v1/reviews/pending", headers=analyst_headers)
        assert resp.status_code == 200


class TestSSE:
    def test_sse_requires_auth(self, client: TestClient) -> None:
        resp = client.get("/api/v1/events/stream")
        assert resp.status_code in (401, 403)

    @pytest.mark.integration
    def test_sse_connect_returns_streaming_response(self, client: TestClient, viewer_headers: dict) -> None:
        with client.stream("GET", "/api/v1/events/stream", headers=viewer_headers) as resp:
            assert resp.status_code == 200
            assert resp.headers.get("content-type") == "text/event-stream"


class TestAgentRun:
    @pytest.mark.integration
    def test_agent_run_requires_auth(self, client: TestClient) -> None:
        resp = client.post("/api/v1/agent/run", json={})
        assert resp.status_code in (401, 403)

    @pytest.mark.integration
    def test_agent_run_validates_payload(self, client: TestClient, admin_headers: dict) -> None:
        resp = client.post("/api/v1/agent/run", headers=admin_headers, json={})
        assert resp.status_code in (400, 422)


class TestSpansEndpoint:
    def test_create_and_list_spans(self, client: TestClient, ingest_headers: dict, viewer_headers: dict) -> None:
        trace_id = str(uuid4().hex[:32])
        span_id = str(uuid4().hex[:16])
        request_id = str(uuid4().hex[:20])
        now = datetime.now(timezone.utc).isoformat()

        payload = {
            "trace_id": trace_id,
            "span_id": span_id,
            "trace_request_id": request_id,
            "name": "test-span",
            "span_type": "llm",
            "started_at": now,
            "ended_at": now,
        }
        resp = client.post(f"/api/v1/traces/{request_id}/spans", headers=ingest_headers, json=payload)
        assert resp.status_code == 201

        resp = client.get(f"/api/v1/traces/{request_id}/spans", headers=viewer_headers)
        assert resp.status_code == 200

    def test_patch_span(self, client: TestClient, ingest_headers: dict, viewer_headers: dict) -> None:
        trace_id = str(uuid4().hex[:32])
        span_id = str(uuid4().hex[:16])
        request_id = str(uuid4().hex[:20])
        now = datetime.now(timezone.utc).isoformat()

        create_payload = {
            "trace_id": trace_id,
            "span_id": span_id,
            "trace_request_id": request_id,
            "name": "test-span",
            "span_type": "llm",
            "started_at": now,
        }
        client.post(f"/api/v1/traces/{request_id}/spans", headers=ingest_headers, json=create_payload)

        resp = client.patch(f"/api/v1/spans/{span_id}", headers=ingest_headers, json={"output": "updated"})
        assert resp.status_code == 200

    def test_span_tree(self, client: TestClient, ingest_headers: dict, viewer_headers: dict) -> None:
        trace_id = str(uuid4().hex[:32])
        parent_id = str(uuid4().hex[:16])
        child_id = str(uuid4().hex[:16])
        request_id = str(uuid4().hex[:20])
        now = datetime.now(timezone.utc).isoformat()

        for sid in [parent_id, child_id]:
            client.post(f"/api/v1/traces/{request_id}/spans", headers=ingest_headers, json={
                "trace_id": trace_id,
                "span_id": sid,
                "trace_request_id": request_id,
                "parent_span_id": None if sid == parent_id else parent_id,
                "name": f"span-{sid[:8]}",
                "span_type": "llm",
                "started_at": now,
            })
        resp = client.get(f"/api/v1/traces/{request_id}/spans/tree", headers=viewer_headers)
        assert resp.status_code == 200


class TestReplay:
    @pytest.mark.integration
    def test_replay_requires_existing_trace(self, client: TestClient, viewer_headers: dict) -> None:
        resp = client.post("/api/v1/traces/nonexistent/replay", headers=viewer_headers)
        assert resp.status_code == 404


class TestEscalatedReviews:
    def test_escalated_endpoint(self, client: TestClient, analyst_headers: dict) -> None:
        resp = client.get("/api/v1/reviews/escalated", headers=analyst_headers)
        assert resp.status_code == 200
