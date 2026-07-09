"""Data access layer for trace telemetry — PostgreSQL via SQLAlchemy."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, TypeVar

from sqlalchemy import Date, case, cast, func
from sqlalchemy.orm import Session

from app.db.models import Trace
from app.db.session import SessionLocal
from app.schemas.trace import TraceIngestRequest

T = TypeVar("T")


class TraceRepository:
    def __init__(self, db: Session | None = None) -> None:
        self._db = db

    def _session(self) -> Session:
        if self._db is not None:
            return self._db
        return SessionLocal()

    def _cleanup(self, session: Session) -> None:
        if self._db is None:
            session.close()

    async def _run_async(self, fn: Callable[[], T]) -> T:
        if self._db is not None:
            return fn()
        return await asyncio.to_thread(fn)

    def _apply_project_filter(self, query: Any, project_names: list[str] | None) -> Any:
        if not project_names:
            return query
        if len(project_names) == 1:
            return query.where(Trace.project_name == project_names[0])
        return query.where(Trace.project_name.in_(project_names))

    async def create(self, payload: TraceIngestRequest) -> Trace:
        def _fn():
            session = self._session()
            try:
                trace = Trace(
                    request_id=payload.request_id,
                    project_name=payload.project_name,
                    prompt=payload.prompt,
                    response=payload.response,
                    model_name=payload.model_name,
                    total_tokens=payload.total_tokens,
                    cost=payload.cost,
                    latency_ms=payload.latency_ms,
                    status=payload.status,
                    flagged_for_governance=payload.flagged_for_governance,
                    timestamp=payload.timestamp,
                )
                session.add(trace)
                session.flush()
                return trace
            finally:
                self._cleanup(session)
        return await self._run_async(_fn)

    async def get_total_cost(self, project_names: list[str] | None = None) -> float:
        def _fn():
            session = self._session()
            try:
                query = self._apply_project_filter(session.query(func.sum(Trace.cost)), project_names)
                result = query.scalar()
                return float(result) if result is not None else 0.0
            finally:
                self._cleanup(session)
        return await self._run_async(_fn)

    async def get_average_latency_last_n(self, n: int, project_names: list[str] | None = None) -> float:
        def _fn():
            session = self._session()
            try:
                query = self._apply_project_filter(session.query(Trace.latency_ms).order_by(Trace.timestamp.desc()).limit(n), project_names)
                results = query.all()
                if not results:
                    return 0.0
                return sum(r[0] for r in results) / len(results)
            finally:
                self._cleanup(session)
        return await self._run_async(_fn)

    async def get_governance_flagged_count(self, project_names: list[str] | None = None) -> int:
        def _fn():
            session = self._session()
            try:
                query = session.query(func.count(Trace.id)).where(Trace.flagged_for_governance == True)
                query = self._apply_project_filter(query, project_names)
                result = query.scalar()
                return int(result or 0)
            finally:
                self._cleanup(session)
        return await self._run_async(_fn)

    async def list_recent(self, limit: int = 100, project_names: list[str] | None = None) -> list[Trace]:
        def _fn():
            session = self._session()
            try:
                query = self._apply_project_filter(session.query(Trace), project_names)
                return query.order_by(Trace.timestamp.desc()).limit(limit).all()
            finally:
                self._cleanup(session)
        return await self._run_async(_fn)

    async def list_flagged(self, limit: int = 500, project_names: list[str] | None = None) -> list[Trace]:
        def _fn():
            session = self._session()
            try:
                query = session.query(Trace).where(Trace.flagged_for_governance == True)
                query = self._apply_project_filter(query, project_names)
                return query.order_by(Trace.timestamp.desc()).limit(limit).all()
            finally:
                self._cleanup(session)
        return await self._run_async(_fn)

    async def get_recent_latencies(self, limit: int = 50, project_names: list[str] | None = None) -> list[float]:
        def _fn():
            session = self._session()
            try:
                query = self._apply_project_filter(session.query(Trace.latency_ms).order_by(Trace.timestamp.desc()).limit(limit), project_names)
                return [r[0] for r in query.all()]
            finally:
                self._cleanup(session)
        return await self._run_async(_fn)

    async def get_error_rate_last_n(self, n: int = 50, project_names: list[str] | None = None) -> float:
        def _fn():
            session = self._session()
            try:
                query = self._apply_project_filter(session.query(Trace.status).order_by(Trace.timestamp.desc()).limit(n), project_names)
                traces = query.all()
                if not traces:
                    return 0.0
                error_count = sum(1 for r in traces if r[0] == "error")
                return round((error_count / len(traces)) * 100, 2)
            finally:
                self._cleanup(session)
        return await self._run_async(_fn)

    async def get_trace_count_last_24h(self, project_names: list[str] | None = None) -> int:
        def _fn():
            session = self._session()
            try:
                cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
                query = session.query(func.count(Trace.id)).where(Trace.timestamp >= cutoff)
                query = self._apply_project_filter(query, project_names)
                result = query.scalar()
                return int(result or 0)
            finally:
                self._cleanup(session)
        return await self._run_async(_fn)

    async def get_by_request_id(self, request_id: str) -> Trace | None:
        def _fn():
            session = self._session()
            try:
                return session.query(Trace).where(Trace.request_id == request_id).first()
            finally:
                self._cleanup(session)
        return await self._run_async(_fn)

    async def list_project_names(self) -> list[str]:
        def _fn():
            session = self._session()
            try:
                results = session.query(Trace.project_name).distinct().order_by(Trace.project_name).all()
                return [r[0] for r in results]
            finally:
                self._cleanup(session)
        return await self._run_async(_fn)

    async def get_daily_costs(self, project_names: list[str] | None = None) -> list[dict]:
        def _fn():
            session = self._session()
            try:
                query = session.query(cast(Trace.timestamp, Date).label('day'), func.sum(Trace.cost).label('cost'), func.count(Trace.id).label('cnt'))
                if project_names:
                    if len(project_names) == 1:
                        query = query.where(Trace.project_name == project_names[0])
                    else:
                        query = query.where(Trace.project_name.in_(project_names))
                query = query.group_by(cast(Trace.timestamp, Date)).order_by(cast(Trace.timestamp, Date))
                results = query.all()
                return [{"_id": str(r[0]) if r[0] else "unknown", "cost": float(r[1] or 0), "cnt": int(r[2] or 0)} for r in results]
            finally:
                self._cleanup(session)
        return await self._run_async(_fn)

    async def get_costs_by_model(self, project_names: list[str] | None = None) -> list[dict]:
        def _fn():
            session = self._session()
            try:
                query = session.query(Trace.model_name.label('_id'), func.sum(Trace.cost).label('cost'), func.sum(Trace.total_tokens).label('tokens'), func.count(Trace.id).label('cnt'))
                if project_names:
                    if len(project_names) == 1:
                        query = query.where(Trace.project_name == project_names[0])
                    else:
                        query = query.where(Trace.project_name.in_(project_names))
                query = query.group_by(Trace.model_name).order_by(func.sum(Trace.cost).desc())
                results = query.all()
                return [{"_id": r[0], "cost": float(r[1] or 0), "tokens": int(r[2] or 0), "cnt": int(r[3] or 0)} for r in results]
            finally:
                self._cleanup(session)
        return await self._run_async(_fn)

    async def get_costs_by_project(self, project_names: list[str] | None = None) -> list[dict]:
        def _fn():
            session = self._session()
            try:
                query = session.query(Trace.project_name.label('_id'), func.sum(Trace.cost).label('cost'), func.sum(Trace.total_tokens).label('tokens'), func.count(Trace.id).label('cnt'))
                if project_names:
                    if len(project_names) == 1:
                        query = query.where(Trace.project_name == project_names[0])
                    else:
                        query = query.where(Trace.project_name.in_(project_names))
                query = query.group_by(Trace.project_name).order_by(func.sum(Trace.cost).desc())
                results = query.all()
                return [{"_id": r[0], "cost": float(r[1] or 0), "tokens": int(r[2] or 0), "cnt": int(r[3] or 0)} for r in results]
            finally:
                self._cleanup(session)
        return await self._run_async(_fn)

    async def get_total_tokens(self, project_names: list[str] | None = None) -> int:
        def _fn():
            session = self._session()
            try:
                query = self._apply_project_filter(session.query(func.sum(Trace.total_tokens)), project_names)
                result = query.scalar()
                return int(result or 0)
            finally:
                self._cleanup(session)
        return await self._run_async(_fn)

    async def get_trace_count(self, project_names: list[str] | None = None) -> int:
        def _fn():
            session = self._session()
            try:
                query = self._apply_project_filter(session.query(func.count(Trace.id)), project_names)
                result = query.scalar()
                return int(result or 0)
            finally:
                self._cleanup(session)
        return await self._run_async(_fn)

    async def get_cost_this_month(self, project_names: list[str] | None = None) -> float:
        def _fn():
            session = self._session()
            try:
                now = datetime.now(timezone.utc)
                month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                query = session.query(func.sum(Trace.cost)).where(Trace.timestamp >= month_start)
                query = self._apply_project_filter(query, project_names)
                result = query.scalar()
                return float(result or 0.0)
            finally:
                self._cleanup(session)
        return await self._run_async(_fn)

    async def get_trace_count_this_month(self, project_names: list[str] | None = None) -> int:
        def _fn():
            session = self._session()
            try:
                now = datetime.now(timezone.utc)
                month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                query = session.query(func.count(Trace.id)).where(Trace.timestamp >= month_start)
                query = self._apply_project_filter(query, project_names)
                result = query.scalar()
                return int(result or 0)
            finally:
                self._cleanup(session)
        return await self._run_async(_fn)

    async def get_project_stats(self, project_name: str) -> dict:
        def _fn():
            session = self._session()
            try:
                query = session.query(func.sum(Trace.total_tokens).label('total_tokens'), func.sum(Trace.cost).label('total_cost'), func.count(Trace.id).label('total_traces'), func.sum(case((Trace.status == "success", 1), else_=0)).label('success_count'), func.avg(Trace.latency_ms).label('avg_latency'), func.min(Trace.timestamp).label('first_trace')).where(Trace.project_name == project_name)
                r = query.first()
                if r is None or r.total_traces is None or r.total_traces == 0:
                    return {"total_tokens": 0, "total_cost": 0.0, "total_traces": 0, "success_count": 0, "avg_latency": 0.0, "first_trace": None, "models": []}
                models_result = session.query(Trace.model_name).where(Trace.project_name == project_name).distinct().all()
                models = list(set(m[0] for m in models_result if m[0]))
                return {"total_tokens": int(r.total_tokens or 0), "total_cost": float(r.total_cost or 0.0), "total_traces": int(r.total_traces or 0), "success_count": int(r.success_count or 0), "avg_latency": float(r.avg_latency or 0.0), "first_trace": r.first_trace, "models": models}
            finally:
                self._cleanup(session)
        return await self._run_async(_fn)

    async def delete_by_project(self, project_name: str) -> int:
        def _fn():
            session = self._session()
            try:
                count = session.query(Trace).where(Trace.project_name == project_name).delete()
                return count
            finally:
                self._cleanup(session)
        return await self._run_async(_fn)

    async def get_team_project_cost(self, team_project_names: list[str]) -> tuple[float, int, int]:
        def _fn():
            session = self._session()
            try:
                query = session.query(func.sum(Trace.cost), func.sum(Trace.total_tokens), func.count(Trace.id))
                if len(team_project_names) == 1:
                    query = query.where(Trace.project_name == team_project_names[0])
                else:
                    query = query.where(Trace.project_name.in_(team_project_names))
                r = query.first()
                return float(r[0] or 0.0), int(r[1] or 0), int(r[2] or 0)
            finally:
                self._cleanup(session)
        return await self._run_async(_fn)

    async def get_team_project_cost_this_month(self, team_project_names: list[str], month_start: datetime) -> float:
        def _fn():
            session = self._session()
            try:
                query = session.query(func.sum(Trace.cost)).where(Trace.timestamp >= month_start)
                if len(team_project_names) == 1:
                    query = query.where(Trace.project_name == team_project_names[0])
                else:
                    query = query.where(Trace.project_name.in_(team_project_names))
                result = query.scalar()
                return float(result or 0.0)
            finally:
                self._cleanup(session)
        return await self._run_async(_fn)