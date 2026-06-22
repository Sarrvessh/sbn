"""CrewAI integration via task/agent execution hooks."""
from __future__ import annotations

import logging
from typing import Any

from sbn_sdk.integrations.base import IntegrationTracer, IntegrationSpan

logger = logging.getLogger(__name__)

try:
    from crewai import Agent as CrewAgent, Task as CrewTask, Crew
    from crewai.tasks.task_output import TaskOutput
except ImportError:
    CrewAgent = None
    CrewTask = None
    Crew = None
    TaskOutput = None


class SbnCrewAIHandler:
    """Patches CrewAI agent/task execution to create SBN spans."""

    def __init__(self, tracer: IntegrationTracer) -> None:
        self.tracer = tracer
        self._task_spans: dict[str, IntegrationSpan] = {}
        self._agent_spans: dict[str, IntegrationSpan] = {}

    def _original_execute_task(self, crew: Any, task: Any) -> Any:
        """Execute a task with SBN tracing."""
        task_id = getattr(task, "id", str(id(task)))
        agent = getattr(task, "agent", None)
        agent_role = getattr(agent, "role", "unknown") if agent else "unknown"

        span = self.tracer.create_span(
            name=f"crewai:task:{task_id[:8]}",
            span_type="task",
            input_text=getattr(task, "description", "")[:500],
            tool_name=f"agent:{agent_role}",
        )
        self._task_spans[task_id] = span

        try:
            from crewai.task import Task as InternalTask
            if hasattr(task, "execute") and callable(task.execute):
                result = task.execute()
            elif hasattr(task, "_execute") and callable(task._execute):
                result = task._execute()
            else:
                result = None

            if hasattr(result, "raw_output"):
                output = result.raw_output
            elif hasattr(result, "output"):
                output = result.output
            elif isinstance(result, str):
                output = result
            elif result is not None:
                output = str(result)
            else:
                output = ""

            if span:
                span.end(output=output[:1000], status_code="OK")
            return result
        except Exception as exc:
            if span:
                span.end_error(str(exc))
            raise

    def instrument_crew(self, crew: Any) -> Any:
        """Patch a Crew instance to trace all task executions."""
        original_kickoff = getattr(crew, "kickoff", None)
        if original_kickoff is None:
            logger.warning("Crew object has no kickoff method")
            return crew

        handler = self

        def traced_kickoff(*args, **kwargs):
            tasks = getattr(crew, "tasks", [])
            for task in tasks:
                handler._execute_task(crew, task)
            return original_kickoff(*args, **kwargs)

        crew.kickoff = traced_kickoff
        return crew


def instrument(
    tracer: IntegrationTracer,
    crew: Any = None,
) -> SbnCrewAIHandler:
    """Instrument CrewAI with SBN tracing.

    Usage:
        from sbn_sdk.integrations.crewai import instrument
        tracer = IntegrationTracer(backend_url="http://localhost:8000", api_key="...")
        handler = instrument(tracer)
        handler.instrument_crew(my_crew)
        my_crew.kickoff()
    """
    if Crew is None:
        raise ImportError(
            "crewai is not installed. Install with: pip install crewai"
        )
    handler = SbnCrewAIHandler(tracer)
    if crew is not None:
        handler.instrument_crew(crew)
    return handler
