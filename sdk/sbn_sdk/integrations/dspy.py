"""DSPy integration via module execution hooks."""
from __future__ import annotations

import logging

from sbn_sdk.integrations.base import IntegrationTracer

logger = logging.getLogger(__name__)

try:
    import dspy
except ImportError:
    dspy = None


def instrument(
    tracer: IntegrationTracer,
) -> None:
    """Patch dspy.forward to create SBN spans for every module call.

    Usage:
        from sbn_sdk.integrations.dspy import instrument
        tracer = IntegrationTracer(backend_url="http://localhost:8000", api_key="...")
        instrument(tracer)
        # Now every dspy module forward() call is traced
    """
    if dspy is None:
        raise ImportError(
            "dspy is not installed. Install with: pip install dspy"
        )

    original_forward = dspy.Module.forward

    def traced_forward(self, *args, **kwargs):
        class_name = type(self).__name__
        input_text = str(args[0]) if args else str(kwargs)
        span = tracer.create_span(
            name=f"dspy:{class_name}",
            span_type="dspy",
            input_text=input_text[:500],
        )
        try:
            result = original_forward(self, *args, **kwargs)
            output = str(result)[:1000] if result else ""
            if span:
                span.end(output=output, status_code="OK")
            return result
        except Exception as exc:
            if span:
                span.end_error(str(exc))
            raise

    dspy.Module.forward = traced_forward
    logger.info("dspy.Module.forward patched for SBN tracing")
