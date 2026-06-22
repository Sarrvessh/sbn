"""AutoGen (v0.4+) integration via agent messaging hooks."""
from __future__ import annotations

import functools
import logging
from typing import Any

from sbn_sdk.integrations.base import IntegrationTracer

logger = logging.getLogger(__name__)


def instrument(
    tracer: IntegrationTracer,
) -> None:
    """Patch AutoGen agents to create SBN spans for agent runs and messages.

    Hooks into autogen.AgentBase.send() and autogen.AgentBase.receive().

    Usage:
        from sbn_sdk.integrations.autogen import instrument
        instrument(tracer)

    Note: This integration targets AutoGen v0.4+ (the `autogen-agentchat` package).
    For AutoGen v0.2.x, the API differs; use the lower-level monkey-patching approach.
    """
    try:
        from autogen import Agent
    except ImportError:
        Agent = None

    if Agent is None:
        raise ImportError(
            "autogen is not installed. Install with: pip install autogen-agentchat"
        )

    _patch_agent_class(Agent, tracer)
    logger.info("AutoGen patched: Agent.send/receive -> SBN spans")


def _patch_agent_class(cls: type, tracer: IntegrationTracer) -> None:
    """Patch send and receive on an AutoGen agent class."""
    if hasattr(cls, "send") and not getattr(cls.send, "_sbn_patched", False):
        original_send = cls.send

        @functools.wraps(original_send)
        def patched_send(self, message: Any, recipient: Any, *args: Any, **kwargs: Any) -> Any:
            msg_text = str(message)[:500] if message else ""
            span = tracer.create_span(
                name=f"send:{getattr(self, 'name', 'agent')}->{getattr(recipient, 'name', '?')}",
                span_type="agent_msg",
                input_text=msg_text,
                tool_name=getattr(self, "name", None),
            )
            try:
                result = original_send(self, message, recipient, *args, **kwargs)
                if span is not None:
                    span.end(output=str(result)[:500])
                return result
            except Exception as exc:
                if span is not None:
                    span.end_error(str(exc))
                raise

        patched_send._sbn_patched = True
        cls.send = patched_send

    if hasattr(cls, "receive") and not getattr(cls.receive, "_sbn_patched", False):
        original_receive = cls.receive

        @functools.wraps(original_receive)
        def patched_receive(self, message: Any, sender: Any, *args: Any, **kwargs: Any) -> Any:
            span = tracer.create_span(
                name=f"receive:{getattr(self, 'name', 'agent')}<-{getattr(sender, 'name', '?')}",
                span_type="agent_msg",
                input_text=str(message)[:500],
            )
            try:
                result = original_receive(self, message, sender, *args, **kwargs)
                if span is not None:
                    span.end(output=str(result)[:500])
                return result
            except Exception as exc:
                if span is not None:
                    span.end_error(str(exc))
                raise

        patched_receive._sbn_patched = True
        cls.receive = patched_receive
