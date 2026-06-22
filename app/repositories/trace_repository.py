"""Data access layer for trace telemetry — MongoDB via Beanie."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.db.mongo_models import TraceDocument
from app.schemas.trace import TraceIngestRequest


class TraceRepository:
    async def create(self, payload: TraceIngestRequest) -> TraceDocument:
        trace = TraceDocument(
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
        return await trace.insert()

    async def get_total_cost(self, project_names: list[str] | None = None) -> float:
        pipeline = self._build_cost_pipeline(project_names)
        pipeline.append({"$group": {"_id": None, "total": {"$sum": "$cost"}}})
        results = await TraceDocument.aggregate(pipeline).to_list()
        return float(results[0]["total"]) if results else 0.0

    async def get_average_latency_last_n(
        self, n: int, project_names: list[str] | None = None,
    ) -> float:
        query = self._apply_project_filter({}, project_names)
        cursor = TraceDocument.find(query).sort("-timestamp").limit(n)
        traces = await cursor.to_list()
        if not traces:
            return 0.0
        return sum(t.latency_ms for t in traces) / len(traces)

    async def get_governance_flagged_count(self, project_names: list[str] | None = None) -> int:
        query = {"flagged_for_governance": True}
        query = self._apply_project_filter(query, project_names)
        return await TraceDocument.find(query).count()

    async def list_recent(self, limit: int = 100, project_names: list[str] | None = None) -> list[TraceDocument]:
        query = self._apply_project_filter({}, project_names)
        cursor = TraceDocument.find(query).sort("-timestamp").limit(limit)
        return await cursor.to_list()

    async def list_flagged(self, limit: int = 500, project_names: list[str] | None = None) -> list[TraceDocument]:
        query = {"flagged_for_governance": True}
        query = self._apply_project_filter(query, project_names)
        cursor = TraceDocument.find(query).sort("-timestamp").limit(limit)
        return await cursor.to_list()

    async def get_recent_latencies(
        self, limit: int = 50, project_names: list[str] | None = None,
    ) -> list[float]:
        query = self._apply_project_filter({}, project_names)
        cursor = TraceDocument.find(query).sort("-timestamp").limit(limit)
        traces = await cursor.to_list()
        return [t.latency_ms for t in traces]

    async def get_error_rate_last_n(
        self, n: int = 50, project_names: list[str] | None = None,
    ) -> float:
        query = self._apply_project_filter({}, project_names)
        cursor = TraceDocument.find(query).sort("-timestamp").limit(n)
        traces = await cursor.to_list()
        if not traces:
            return 0.0
        error_count = sum(1 for t in traces if t.status == "error")
        return round((error_count / len(traces)) * 100, 2)

    async def get_trace_count_last_24h(self, project_names: list[str] | None = None) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        query = {"timestamp": {"$gte": cutoff}}
        query = self._apply_project_filter(query, project_names)
        return await TraceDocument.find(query).count()

    async def get_by_request_id(self, request_id: str) -> TraceDocument | None:
        return await TraceDocument.find_one({"request_id": request_id})

    async def list_project_names(self) -> list[str]:
        pipeline = [{"$group": {"_id": "$project_name"}}, {"$sort": {"_id": 1}}]
        results = await TraceDocument.aggregate(pipeline).to_list()
        return [r["_id"] for r in results]

    async def get_daily_costs(self, project_names: list[str] | None = None) -> list[dict]:
        match = self._build_project_match(project_names)
        pipeline = [
            {"$match": match},
            {
                "$group": {
                    "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}},
                    "cost": {"$sum": "$cost"},
                    "cnt": {"$sum": 1},
                },
            },
            {"$sort": {"_id": 1}},
        ]
        return await TraceDocument.aggregate(pipeline).to_list()

    async def get_costs_by_model(self, project_names: list[str] | None = None) -> list[dict]:
        match = self._build_project_match(project_names)
        pipeline = [
            {"$match": match},
            {
                "$group": {
                    "_id": "$model_name",
                    "cost": {"$sum": "$cost"},
                    "tokens": {"$sum": "$total_tokens"},
                    "cnt": {"$sum": 1},
                },
            },
            {"$sort": {"cost": -1}},
        ]
        return await TraceDocument.aggregate(pipeline).to_list()

    async def get_costs_by_project(self, project_names: list[str] | None = None) -> list[dict]:
        match = self._build_project_match(project_names)
        pipeline = [
            {"$match": match},
            {
                "$group": {
                    "_id": "$project_name",
                    "cost": {"$sum": "$cost"},
                    "tokens": {"$sum": "$total_tokens"},
                    "cnt": {"$sum": 1},
                },
            },
            {"$sort": {"cost": -1}},
        ]
        return await TraceDocument.aggregate(pipeline).to_list()

    async def get_total_tokens(self, project_names: list[str] | None = None) -> int:
        pipeline = self._build_cost_pipeline(project_names)
        pipeline.append({"$group": {"_id": None, "total": {"$sum": "$total_tokens"}}})
        results = await TraceDocument.aggregate(pipeline).to_list()
        return int(results[0]["total"]) if results else 0

    async def get_trace_count(self, project_names: list[str] | None = None) -> int:
        pipeline = self._build_cost_pipeline(project_names)
        pipeline.append({"$group": {"_id": None, "total": {"$sum": 1}}})
        results = await TraceDocument.aggregate(pipeline).to_list()
        return int(results[0]["total"]) if results else 0

    async def get_cost_this_month(self, project_names: list[str] | None = None) -> float:
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        match = self._build_project_match(project_names)
        match["timestamp"] = {"$gte": month_start}
        pipeline = [{"$match": match}, {"$group": {"_id": None, "total": {"$sum": "$cost"}}}]
        results = await TraceDocument.aggregate(pipeline).to_list()
        return float(results[0]["total"]) if results else 0.0

    async def get_trace_count_this_month(self, project_names: list[str] | None = None) -> int:
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        match = self._build_project_match(project_names)
        match["timestamp"] = {"$gte": month_start}
        pipeline = [{"$match": match}, {"$group": {"_id": None, "total": {"$sum": 1}}}]
        results = await TraceDocument.aggregate(pipeline).to_list()
        return int(results[0]["total"]) if results else 0

    async def get_project_stats(self, project_name: str) -> dict:
        match = {"project_name": project_name}
        pipeline = [
            {"$match": match},
            {
                "$group": {
                    "_id": None,
                    "total_tokens": {"$sum": "$total_tokens"},
                    "total_cost": {"$sum": "$cost"},
                    "total_traces": {"$sum": 1},
                    "success_count": {"$sum": {"$cond": [{"$eq": ["$status", "success"]}, 1, 0]}},
                    "avg_latency": {"$avg": "$latency_ms"},
                    "first_trace": {"$min": "$timestamp"},
                    "models": {"$addToSet": "$model_name"},
                },
            },
        ]
        results = await TraceDocument.aggregate(pipeline).to_list()
        if not results:
            return {
                "total_tokens": 0, "total_cost": 0.0, "total_traces": 0,
                "success_count": 0, "avg_latency": 0.0,
                "first_trace": None, "models": [],
            }
        r = results[0]
        return {
            "total_tokens": int(r.get("total_tokens", 0)),
            "total_cost": float(r.get("total_cost", 0.0)),
            "total_traces": int(r.get("total_traces", 0)),
            "success_count": int(r.get("success_count", 0)),
            "avg_latency": float(r.get("avg_latency", 0.0)),
            "first_trace": r.get("first_trace"),
            "models": list(r.get("models", [])),
        }

    async def delete_by_project(self, project_name: str) -> int:
        result = await TraceDocument.find({"project_name": project_name}).delete()
        return result.deleted_count

    async def get_team_project_cost(
        self, team_project_names: list[str],
    ) -> tuple[float, int, int]:
        query = self._apply_project_filter({}, team_project_names)
        traces = await TraceDocument.find(query).to_list()
        total_cost = sum(t.cost for t in traces)
        total_tokens = sum(t.total_tokens for t in traces)
        return float(total_cost), int(total_tokens), len(traces)

    async def get_team_project_cost_this_month(
        self, team_project_names: list[str], month_start: datetime,
    ) -> float:
        query = self._apply_project_filter({}, team_project_names)
        query["timestamp"] = {"$gte": month_start}
        traces = await TraceDocument.find(query).to_list()
        return float(sum(t.cost for t in traces))

    def _build_cost_pipeline(self, project_names: list[str] | None) -> list[dict]:
        pipeline: list[dict] = []
        if project_names:
            if len(project_names) == 1:
                pipeline.append({"$match": {"project_name": project_names[0]}})
            else:
                pipeline.append({"$match": {"project_name": {"$in": project_names}}})
        return pipeline

    def _build_project_match(self, project_names: list[str] | None) -> dict:
        if not project_names:
            return {}
        if len(project_names) == 1:
            return {"project_name": project_names[0]}
        return {"project_name": {"$in": project_names}}

    def _apply_project_filter(self, query: dict, project_names: list[str] | None) -> dict:
        if not project_names:
            return query
        if len(project_names) == 1:
            query["project_name"] = project_names[0]
        else:
            query["project_name"] = {"$in": project_names}
        return query
