"""Integration for Google Agent Development Kit (ADK)."""

from __future__ import annotations

import inspect
import logging
from typing import Any

from sbn_sdk.integrations.base import IntegrationTracer

logger = logging.getLogger(__name__)

try:
    from google.adk.agents import Agent as ADKAgent
    from google.adk.runners import Runner as ADKRunner
    HAS_ADK = True
except ImportError:
    ADKAgent = None  # type: ignore
    ADKRunner = None  # type: ignore
    HAS_ADK = False


def instrument_runner(tracer: IntegrationTracer) -> None:
    """Patch ADK Runner.run to add tracing spans around agent execution."""

    if not HAS_ADK:
        logger.warning("google-adk not installed; ADK instrumentation unavailable")
        return

    original_run = ADKRunner.run  # type: ignore

    if inspect.iscoroutinefunction(original_run):
        async def traced_run(self, *args: Any, **kwargs: Any) -> Any:
            agent_name = getattr(self, "agent_name", "adk-agent")
            span = tracer.create_span(name=f"adk-run-{agent_name}", span_type="adk")
            try:
                result = await original_run(self, *args, **kwargs)
                if span is not None:
                    span.end(output=str(result)[:1000])
                return result
            except Exception as exc:
                if span is not None:
                    span.end_error(str(exc))
                raise
    else:
        def traced_run(self, *args: Any, **kwargs: Any) -> Any:
            agent_name = getattr(self, "agent_name", "adk-agent")
            span = tracer.create_span(name=f"adk-run-{agent_name}", span_type="adk")
            try:
                result = original_run(self, *args, **kwargs)
                if span is not None:
                    span.end(output=str(result)[:1000])
                return result
            except Exception as exc:
                if span is not None:
                    span.end_error(str(exc))
                raise

    ADKRunner.run = traced_run  # type: ignore
