"""Main router for v1 endpoints."""

from fastapi import APIRouter

from app.api.v1.endpoints.alert_rules import router as alert_rules_router
from app.api.v1.endpoints.analyzer import router as analyzer_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.cost_analytics import router as cost_router
from app.api.v1.endpoints.escalation import router as escalation_router
from app.api.v1.endpoints.oversight import router as oversight_router
from app.api.v1.endpoints.policies import router as policies_router
from app.api.v1.endpoints.projects import router as projects_router
from app.api.v1.endpoints.replay import router as replay_router
from app.api.v1.endpoints.settings import router as settings_router
from app.api.v1.endpoints.spans import router as spans_router
from app.api.v1.endpoints.telemetry import router as telemetry_router
from app.api.v1.endpoints.traces import router as traces_router
from app.api.v1.endpoints.webhooks import router as webhooks_router  # noqa: F401

api_router = APIRouter()
api_router.include_router(analyzer_router, tags=["analyzer"])
api_router.include_router(auth_router, tags=["auth"])
api_router.include_router(telemetry_router, tags=["telemetry"])
api_router.include_router(traces_router, tags=["traces"])
api_router.include_router(spans_router, tags=["spans"])
api_router.include_router(webhooks_router, tags=["webhooks"])
api_router.include_router(replay_router, tags=["replay"])
api_router.include_router(policies_router, tags=["policies"])
api_router.include_router(cost_router, tags=["cost"])
api_router.include_router(oversight_router, tags=["oversight"])
api_router.include_router(projects_router, tags=["projects"])
api_router.include_router(alert_rules_router, tags=["alert_rules"])
api_router.include_router(escalation_router, tags=["escalation"])
api_router.include_router(settings_router, tags=["settings"])
