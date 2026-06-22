"""LangGraph integration via node-level instrumentation."""
from __future__ import annotations

import functools
import logging
from typing import Any, Callable

from sbn_sdk.integrations.base import IntegrationTracer

logger = logging.getLogger(__name__)

try:
    from langgraph.graph import StateGraph
except ImportError:
    StateGraph = None


def _wrapped_node(original_node: Callable, tracer: IntegrationTracer, node_name: str) -> Callable:
    @functools.wraps(original_node)
    def wrapper(state: Any) -> Any:
        span = tracer.create_span(
            name=f"node:{node_name}",
            span_type="graph_node",
            input_text=str(state)[:500],
        )
        try:
            result = original_node(state)
            if span is not None:
                span.end(output=str(result)[:500])
            return result
        except Exception as exc:
            if span is not None:
                span.end_error(str(exc))
            raise
    return wrapper


def instrument_graph(
    graph: Any,
    tracer: IntegrationTracer,
) -> Any:
    """Patch a LangGraph StateGraph to create SBN spans for each node.

    Usage:
        from sbn_sdk.integrations.langgraph import instrument_graph
        instrument_graph(app, tracer)
    """
    if not hasattr(graph, "nodes"):
        logger.warning("Object does not appear to be a LangGraph graph")
        return graph

    for node_name, node_data in list(graph.nodes.items()):
        original = getattr(node_data, "func", None)
        if original is None:
            original = node_data
        if isinstance(original, functools.partial):
            original = original.func

        if hasattr(node_data, "func"):
            node_data.func = _wrapped_node(original, tracer, node_name)
        elif callable(node_data):
            graph.nodes[node_name] = _wrapped_node(original, tracer, node_name)

    return graph


def instrument(
    tracer: IntegrationTracer,
) -> Callable[[Any], Any]:
    """Return a function that instruments a LangGraph graph.

    Usage:
        from sbn_sdk.integrations.langgraph import instrument
        patcher = instrument(tracer)
        app = patcher(app)  # or instrument_graph(app, tracer)
    """
    if StateGraph is None:
        raise ImportError(
            "langgraph is not installed. Install with: pip install langgraph"
        )
    return lambda graph: instrument_graph(graph, tracer)
