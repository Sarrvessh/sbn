"""OpenAI Agents SDK integration."""
from __future__ import annotations

import functools
import inspect
import logging
from typing import Any

from sbn_sdk.integrations.base import IntegrationTracer

logger = logging.getLogger(__name__)


def instrument(
    tracer: IntegrationTracer,
) -> None:
    """Patch the openai.Agents SDK to create SBN spans for agent runs.

    Hooks into agents.Agent.run() and agents.Agent.run_streamed().

    Usage:
        from sbn_sdk.integrations.openai_agents import instrument
        instrument(tracer)
    """
    try:
        from agents import Agent, Runner
    except ImportError:
        raise ImportError(
            "openai-agents is not installed. Install with: pip install openai-agents"
        )

    original_run = Runner.run

    if inspect.iscoroutinefunction(original_run):
        @functools.wraps(original_run)
        async def patched_run(agent: Agent, input: str, *args: Any, **kwargs: Any) -> Any:
            span = tracer.create_span(
                name=f"agent:{agent.name}",
                span_type="agent",
                input_text=str(input)[:1000],
                model_name=agent.model or "",
            )
            try:
                result = await original_run(agent, input, *args, **kwargs)
                output = result.final_output if hasattr(result, "final_output") else str(result)
                total_tokens = 0
                cost = 0.0
                if hasattr(result, "usage"):
                    usage = result.usage
                    total_tokens = getattr(usage, "total_tokens", 0) or 0
                    cost = getattr(usage, "cost", 0.0) or 0.0
                if span is not None:
                    span.end(output=str(output)[:1000], total_tokens=total_tokens, cost=cost)
                return result
            except Exception as exc:
                if span is not None:
                    span.end_error(str(exc))
                raise
    else:
        @functools.wraps(original_run)
        def patched_run(agent: Agent, input: str, *args: Any, **kwargs: Any) -> Any:
            span = tracer.create_span(
                name=f"agent:{agent.name}",
                span_type="agent",
                input_text=str(input)[:1000],
                model_name=agent.model or "",
            )
            try:
                result = original_run(agent, input, *args, **kwargs)
                output = result.final_output if hasattr(result, "final_output") else str(result)
                total_tokens = 0
                cost = 0.0
                if hasattr(result, "usage"):
                    usage = result.usage
                    total_tokens = getattr(usage, "total_tokens", 0) or 0
                    cost = getattr(usage, "cost", 0.0) or 0.0
                if span is not None:
                    span.end(output=str(output)[:1000], total_tokens=total_tokens, cost=cost)
                return result
            except Exception as exc:
                if span is not None:
                    span.end_error(str(exc))
                raise

    Runner.run = patched_run
    logger.info("OpenAI Agents SDK patched: Runner.run -> SBN spans")

    try:
        original_run_streamed = Runner.run_streamed

        @functools.wraps(original_run_streamed)
        async def patched_run_streamed(
            agent: Agent, input: str, *args: Any, **kwargs: Any
        ) -> Any:
            span = tracer.create_span(
                name=f"agent:{agent.name}",
                span_type="agent",
                input_text=str(input)[:1000],
                model_name=agent.model or "",
            )
            try:
                result = await original_run_streamed(agent, input, *args, **kwargs)
                if span is not None:
                    span.end(output="(streamed)", total_tokens=0, cost=0)
                return result
            except Exception as exc:
                if span is not None:
                    span.end_error(str(exc))
                raise

        Runner.run_streamed = patched_run_streamed
        logger.info("OpenAI Agents SDK patched: Runner.run_streamed -> SBN spans")
    except AttributeError:
        pass
