"""LangChain integration via callback handler."""
from __future__ import annotations

import logging
from typing import Any

from sbn_sdk.integrations.base import IntegrationTracer

logger = logging.getLogger(__name__)

try:
    from langchain_core.callbacks.base import BaseCallbackHandler
    from langchain_core.messages import BaseMessage
except ImportError:
    BaseCallbackHandler = None
    BaseMessage = None


class SbnLangChainHandler(BaseCallbackHandler if BaseCallbackHandler is not None else object):
    """LangChain callback handler that creates SBN spans."""

    def __init__(self, tracer: IntegrationTracer) -> None:
        self.tracer = tracer
        self._run_spans: dict[str, Any] = {}

    def on_llm_start(
        self, serialized: dict, prompts: list[str], **kwargs: Any
    ) -> None:
        run_id = str(kwargs.get("run_id", ""))
        span = self.tracer.create_span(
            name=f"llm:{serialized.get('kwargs', {}).get('model_name', 'unknown')}",
            span_type="llm",
            input_text=prompts[0] if prompts else "",
        )
        self._run_spans[run_id] = span

    def on_llm_end(self, response, **kwargs: Any) -> None:
        run_id = str(kwargs.get("run_id", ""))
        span = self._run_spans.pop(run_id, None)
        if span is None:
            return
        generations = getattr(response, "generations", [])
        output_text = ""
        total_tokens = 0
        if generations and generations[0]:
            output_text = generations[0][0].text if hasattr(generations[0][0], "text") else str(generations[0][0])
        llm_output = getattr(response, "llm_output", {}) or {}
        if llm_output:
            token_usage = llm_output.get("token_usage", {}) or {}
            total_tokens = token_usage.get("total_tokens", 0)
        span.end(output=output_text, total_tokens=total_tokens)

    def on_llm_error(self, error: Exception, **kwargs: Any) -> None:
        run_id = str(kwargs.get("run_id", ""))
        span = self._run_spans.pop(run_id, None)
        if span:
            span.end_error(str(error))

    def on_chain_start(
        self, serialized: dict, inputs: dict, **kwargs: Any
    ) -> None:
        run_id = str(kwargs.get("run_id", ""))
        name = serialized.get("name", "chain")
        input_text = str(list(inputs.values())[0]) if inputs else ""
        span = self.tracer.create_span(
            name=f"chain:{name}", span_type="chain", input_text=input_text
        )
        self._run_spans[run_id] = span

    def on_chain_end(self, outputs: dict, **kwargs: Any) -> None:
        run_id = str(kwargs.get("run_id", ""))
        span = self._run_spans.pop(run_id, None)
        if span:
            span.end(output=str(outputs))

    def on_chain_error(self, error: Exception, **kwargs: Any) -> None:
        run_id = str(kwargs.get("run_id", ""))
        span = self._run_spans.pop(run_id, None)
        if span:
            span.end_error(str(error))

    def on_tool_start(
        self, serialized: dict, input_str: str, **kwargs: Any
    ) -> None:
        run_id = str(kwargs.get("run_id", ""))
        name = serialized.get("name", "tool")
        span = self.tracer.create_span(
            name=f"tool:{name}",
            span_type="tool",
            input_text=input_str,
            tool_name=name,
        )
        self._run_spans[run_id] = span

    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        run_id = str(kwargs.get("run_id", ""))
        span = self._run_spans.pop(run_id, None)
        if span:
            span.end(output=output)

    def on_tool_error(self, error: Exception, **kwargs: Any) -> None:
        run_id = str(kwargs.get("run_id", ""))
        span = self._run_spans.pop(run_id, None)
        if span:
            span.end_error(str(error))


def instrument(
    tracer: IntegrationTracer,
) -> SbnLangChainHandler:
    """Return a LangChain callback handler connected to the SBN tracer.

    Usage:
        from sbn_sdk.integrations.langchain import instrument
        tracer = instrument(backend_url="http://localhost:8000", api_key="...")
        # Pass tracer as callback to LangChain runs
    """
    if BaseCallbackHandler is None:
        raise ImportError(
            "langchain-core is not installed. Install with: pip install langchain-core"
        )
    return SbnLangChainHandler(tracer)
