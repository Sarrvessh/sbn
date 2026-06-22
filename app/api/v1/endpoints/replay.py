from __future__ import annotations

from time import perf_counter
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import Principal, require_roles
from app.db.session import get_db
from app.repositories.span_repository import SpanRepository
from app.repositories.trace_repository import TraceRepository
from app.services.openai_agent_service import AgentExecutionError, OpenAIAgentService
from app.services.span_service import SpanService, generate_trace_id

router = APIRouter(prefix="")


@router.post("/traces/{trace_request_id}/replay", status_code=status.HTTP_200_OK)
async def replay_trace(
    trace_request_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles("analyst")),
) -> dict:
    trace_repo = TraceRepository()
    trace = await trace_repo.get_by_request_id(trace_request_id)
    if trace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trace not found")

    agent = OpenAIAgentService()

    new_trace_id = generate_trace_id()
    new_request_id = uuid4().hex
    span_service = SpanService(SpanRepository())

    root_span = await span_service.record_root_span(
        trace_request_id=new_request_id,
        trace_id=new_trace_id,
        name=f"replay-{trace.model_name}",
        span_type="llm",
        model_name=trace.model_name,
        input_text=trace.prompt,
    )

    started_at = perf_counter()
    original_response: str = trace.response
    original_tokens: int = trace.total_tokens
    original_cost: float = trace.cost
    original_latency: float = trace.latency_ms

    try:
        result = agent.run_prompt(
            prompt=trace.prompt,
            model_name=trace.model_name,
            max_tokens=512,
            temperature=0.0,
        )
    except AgentExecutionError as exc:
        await span_service.finalize_span(
            root_span.span_id,
            output=str(exc),
            status_code="ERROR",
            status_message=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Replay execution failed: {exc}",
        ) from exc

    replay_latency = (perf_counter() - started_at) * 1000

    await span_service.finalize_span(
        root_span.span_id,
        output=result.response_text,
        total_tokens=result.total_tokens,
        cost=result.cost,
    )

    return {
        "replay_request_id": new_request_id,
        "original": {
            "response": original_response,
            "total_tokens": original_tokens,
            "cost": original_cost,
            "latency_ms": original_latency,
        },
        "replay": {
            "response": result.response_text,
            "total_tokens": result.total_tokens,
            "cost": result.cost,
            "latency_ms": max(replay_latency, 0.001),
        },
        "diff": {
            "response_match": result.response_text.strip() == original_response.strip(),
            "tokens_diff": result.total_tokens - original_tokens,
            "cost_diff": round(result.cost - original_cost, 6),
            "latency_diff_ms": round(max(replay_latency, 0.001) - original_latency, 2),
        },
    }
