from app.db.mongo_models import TraceDocument
from app.repositories.trace_repository import TraceRepository
from app.schemas.metrics import MetricsResponse
from app.schemas.trace import TraceIngestRequest
from app.services.span_service import SpanService, generate_trace_id


class TraceService:
    def __init__(self, trace_repository: TraceRepository) -> None:
        self._trace_repository = trace_repository

    async def ingest_trace(
        self,
        payload: TraceIngestRequest,
        span_service: SpanService | None = None,
    ) -> TraceDocument:
        trace = await self._trace_repository.create(payload)

        if span_service is not None:
            await span_service.record_root_span(
                trace_request_id=trace.request_id,
                trace_id=generate_trace_id(),
                name=f"llm-{trace.model_name}",
                span_type="llm",
                model_name=trace.model_name,
                input_text=trace.prompt,
            )

        return trace

    async def get_metrics(
        self,
        window_size: int = 50,
        project_names: list[str] | None = None,
    ) -> MetricsResponse:
        return MetricsResponse(
            total_cost=await self._trace_repository.get_total_cost(project_names=project_names),
            average_latency_last_50_ms=await self._trace_repository.get_average_latency_last_n(
                window_size, project_names=project_names,
            ),
            governance_flagged_count=await self._trace_repository.get_governance_flagged_count(
                project_names=project_names,
            ),
        )
