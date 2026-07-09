"""Haystack integration via pipeline component tracing."""
from __future__ import annotations

import logging
from typing import Any

from sbn_sdk.integrations.base import IntegrationTracer

logger = logging.getLogger(__name__)

try:
    from haystack.core.component import Component
    from haystack.core.pipeline import Pipeline
except ImportError:
    Pipeline = None
    Component = None


def instrument(
    tracer: IntegrationTracer,
    pipeline: Any = None,
) -> None:
    """Patch Haystack Pipeline.run to create SBN spans for each component.

    Usage:
        from sbn_sdk.integrations.haystack import instrument
        tracer = IntegrationTracer(backend_url="http://localhost:8000", api_key="...")
        instrument(tracer)
        # All Pipeline.run() calls are now traced
    """
    if Pipeline is None:
        raise ImportError(
            "haystack-ai is not installed. Install with: pip install haystack-ai"
        )

    original_run = Pipeline.run

    def traced_run(self, data: dict, *args, **kwargs):
        components = getattr(self, "components", {})
        inputs = {k: str(v)[:200] for k, v in (data or {}).items()}
        span = tracer.create_span(
            name="haystack:pipeline",
            span_type="haystack",
            input_text=str(inputs)[:500],
        )
        try:
            result = original_run(self, data, *args, **kwargs)

            for comp_name, comp_instance in components.items():
                comp_inputs = _get_component_inputs(comp_instance, data)
                comp_span = tracer.create_span(
                    name=f"haystack:{comp_name}",
                    span_type="haystack_component",
                    input_text=str(comp_inputs)[:300],
                    tool_name=comp_name,
                )
                if comp_span:
                    comp_output = str(result.get(comp_name, ""))[:500] if isinstance(result, dict) else ""
                    comp_span.end(output=comp_output, status_code="OK")

            if span:
                span.end(output=str(result)[:1000], status_code="OK")
            return result
        except Exception as exc:
            if span:
                span.end_error(str(exc))
            raise

    Pipeline.run = traced_run
    logger.info("haystack Pipeline.run patched for SBN tracing")


def _get_component_inputs(component: Any, data: dict) -> dict:
    """Extract component-relevant inputs from pipeline data."""
    if hasattr(component, "__class__"):
        name = type(component).__name__.lower()
        return {k: v for k, v in data.items() if name in k.lower()}
    return {}
