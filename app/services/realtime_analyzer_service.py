"""Realtime analysis logic for metrics, traces, and alerts — async with MongoDB."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import AlertRule
from app.repositories.trace_repository import TraceRepository
from app.schemas.analytics import AlertResponse, RealtimeMetricsResponse, RecentTraceResponse
from app.services.cache_service import metrics_cache


class RealtimeAnalyzerService:
    def __init__(self, trace_repository: TraceRepository) -> None:
        self._trace_repository = trace_repository

    async def get_realtime_metrics(
        self, window_size: int = 50, project_names: list[str] | None = None,
    ) -> RealtimeMetricsResponse:
        cache_key = f"metrics:{window_size}:{sorted(project_names) if project_names else 'all'}"
        cached = metrics_cache.get(cache_key)
        if cached is not None:
            return cached

        latencies = await self._trace_repository.get_recent_latencies(window_size, project_names=project_names)
        p95_latency = 0.0
        if latencies:
            sorted_latencies = sorted(latencies)
            idx = int(round((len(sorted_latencies) - 1) * 0.95))
            p95_latency = float(sorted_latencies[idx])

        total_cost = await self._trace_repository.get_total_cost(project_names=project_names)
        avg_latency = await self._trace_repository.get_average_latency_last_n(
            window_size, project_names=project_names,
        )
        flagged = await self._trace_repository.get_governance_flagged_count(project_names=project_names)
        err_rate = await self._trace_repository.get_error_rate_last_n(
            window_size, project_names=project_names,
        )
        traces_24h = await self._trace_repository.get_trace_count_last_24h(project_names=project_names)
        result = RealtimeMetricsResponse(
            total_cost=total_cost,
            average_latency_last_50_ms=avg_latency,
            p95_latency_last_50_ms=p95_latency,
            governance_flagged_count=flagged,
            error_rate_last_50_percent=err_rate,
            traces_last_24h=traces_24h,
        )
        metrics_cache.set(cache_key, result, ttl_seconds=30)
        return result

    async def get_recent_traces(
        self, limit: int = 100, project_names: list[str] | None = None,
    ) -> list[RecentTraceResponse]:
        traces = await self._trace_repository.list_recent(limit, project_names=project_names)
        return [
            RecentTraceResponse(
                request_id=t.request_id,
                project_name=t.project_name,
                model_name=t.model_name,
                total_tokens=t.total_tokens,
                cost=t.cost,
                latency_ms=t.latency_ms,
                status=t.status,  # type: ignore[arg-type]
                flagged_for_governance=t.flagged_for_governance,
                prompt_preview=_safe_preview(t.prompt),
                response_preview=_safe_preview(t.response),
                timestamp=t.timestamp,
            )
            for t in traces
        ]

    async def get_alerts(
        self,
        limit: int = 50,
        project_names: list[str] | None = None,
        db: Session | None = None,
    ) -> list[AlertResponse]:
        traces_key = f"traces:{limit}:{sorted(project_names) if project_names else 'all'}"
        cached_traces = metrics_cache.get(traces_key)
        if cached_traces is not None:
            traces = cached_traces
        else:
            traces = await self._trace_repository.list_recent(limit, project_names=project_names)
            metrics_cache.set(traces_key, traces, ttl_seconds=30)
        alerts: list[AlertResponse] = []

        rule_repo: "AlertRuleRepository | None" = None
        if db is not None:
            from app.repositories.alert_rule_repository import AlertRuleRepository  # noqa: C0415
            rule_repo = AlertRuleRepository(db)

        for trace in traces:
            project = trace.project_name or ""

            latency_rules: list[AlertRule] = []
            cost_rules: list[AlertRule] = []
            gov_rules: list[AlertRule] = []
            if rule_repo is not None:
                latency_rules = rule_repo.get_matching(project, "high_latency")
                cost_rules = rule_repo.get_matching(project, "high_cost")
                gov_rules = rule_repo.get_matching(project, "governance")

            if trace.status == "error":
                severity = "high"
                if gov_rules:
                    severity = gov_rules[0].severity
                alert = AlertResponse(
                    request_id=trace.request_id, project_name=trace.project_name,
                    severity=severity, alert_type="execution_error",
                    message="Agent call failed. Inspect response payload for error details.",
                    latency_ms=trace.latency_ms, cost=trace.cost,
                    status=trace.status,  # type: ignore[arg-type]
                    timestamp=trace.timestamp,
                )
                alerts.append(alert)
                if db is not None:
                    await self._fire_webhook(alert, db)

            latency_threshold = latency_rules[0].threshold_value if latency_rules else settings.latency_alert_threshold_ms
            if trace.latency_ms >= latency_threshold:
                severity = latency_rules[0].severity if latency_rules else "medium"
                alert = AlertResponse(
                    request_id=trace.request_id, project_name=trace.project_name,
                    severity=severity, alert_type="high_latency",
                    message=(
                        f"Latency {trace.latency_ms:.2f} ms exceeds threshold "
                        f"{latency_threshold:.2f} ms"
                    ),
                    latency_ms=trace.latency_ms, cost=trace.cost,
                    status=trace.status,  # type: ignore[arg-type]
                    timestamp=trace.timestamp,
                )
                alerts.append(alert)
                if db is not None:
                    await self._fire_webhook(alert, db)

            cost_threshold = cost_rules[0].threshold_value if cost_rules else settings.cost_alert_threshold
            if trace.cost >= cost_threshold:
                severity = cost_rules[0].severity if cost_rules else "medium"
                alert = AlertResponse(
                    request_id=trace.request_id, project_name=trace.project_name,
                    severity=severity, alert_type="high_cost",
                    message=f"Cost {trace.cost:.6f} exceeds threshold {cost_threshold:.6f}",
                    latency_ms=trace.latency_ms, cost=trace.cost,
                    status=trace.status,  # type: ignore[arg-type]
                    timestamp=trace.timestamp,
                )
                alerts.append(alert)
                if db is not None:
                    await self._fire_webhook(alert, db)

            if trace.flagged_for_governance:
                severity = gov_rules[0].severity if gov_rules else "high"
                alert = AlertResponse(
                    request_id=trace.request_id, project_name=trace.project_name,
                    severity=severity, alert_type="governance",
                    message="Prompt matched one or more governance policy checks.",
                    latency_ms=trace.latency_ms, cost=trace.cost,
                    status=trace.status,  # type: ignore[arg-type]
                    timestamp=trace.timestamp,
                )
                alerts.append(alert)
                if db is not None:
                    await self._fire_webhook(alert, db)

        alerts.sort(key=lambda item: item.timestamp, reverse=True)
        return alerts[:limit]

    async def _fire_webhook(self, alert: AlertResponse, db: Session) -> None:
        from app.services.webhook_service import deliver_event

        await deliver_event(
            event_type=f"alert.{alert.alert_type}",
            payload={
                "event_type": f"alert.{alert.alert_type}",
                "data": alert.model_dump(mode="json"),
            },
            db=db,
        )


def _safe_preview(value: str, max_chars: int = 180) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max_chars - 3] + "..."
