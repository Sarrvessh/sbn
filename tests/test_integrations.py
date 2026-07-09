"""Tests for SDK framework integrations."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from sbn_sdk.integrations.base import IntegrationTracer


@pytest.fixture
def tracer():
    return IntegrationTracer(
        backend_url="http://localhost:8000",
        api_key="test-key",
        project_name="test",
        model_name="gpt-4",
    )


class MockSpan:
    def __init__(self):
        self._span_id = "mock-span-id"
        self._span_stack = []

    def end(self, output="", total_tokens=0, cost=0, **kwargs):
        self.ended = True
        self.end_output = output

    def end_error(self, message=""):
        self.errored = True
        self.error_message = message


@patch("sbn_sdk.integrations.base.get_or_create_client")
class TestIntegrationTracer:
    def test_create_span(self, mock_client, tracer):
        span = tracer.create_span(name="test-span", span_type="test")
        assert span is not None
        assert span._name == "test-span"
        assert span._span_type == "test"
        assert tracer._span_stack == [span._span_id]
        mock_client.return_value.send_span_non_blocking.assert_called_once()

    def test_parent_child_span(self, mock_client, tracer):
        parent = tracer.create_span(name="parent")
        child = tracer.create_span(name="child")
        assert child._parent_span_id == parent._span_id
        assert tracer._span_stack == [parent._span_id, child._span_id]

    def test_end_span_removes_from_stack(self, mock_client, tracer):
        span = tracer.create_span(name="test")
        assert tracer._span_stack == [span._span_id]
        tracer.end_span(span)
        assert tracer._span_stack == []

    def test_current_parent_span_id_none_when_empty(self, mock_client, tracer):
        assert tracer.current_parent_span_id is None

    def test_current_parent_span_id_returns_top(self, mock_client, tracer):
        tracer.create_span(name="first")
        top = tracer.current_parent_span_id
        tracer.create_span(name="second")
        assert tracer.current_parent_span_id != top


@patch("sbn_sdk.integrations.base.get_or_create_client")
class TestIntegrationSpan:
    def test_end_calls_finalize(self, mock_client, tracer):
        span = tracer.create_span(name="test")
        span.end(output="hello", total_tokens=10, cost=0.01)
        mock_client.return_value.send_span_finalize_non_blocking.assert_called_once()
        args = mock_client.return_value.send_span_finalize_non_blocking.call_args[1]
        assert args["output"] == "hello"

    def test_end_error_sets_error_status(self, mock_client, tracer):
        span = tracer.create_span(name="test")
        span.end_error("something went wrong")
        args = mock_client.return_value.send_span_finalize_non_blocking.call_args[1]
        assert args["status_code"] == "ERROR"
        assert args["status_message"] == "something went wrong"


class TestLangChainIntegration:
    def test_handler_creation(self, tracer):
        from sbn_sdk.integrations.langchain import SbnLangChainHandler, instrument
        handler = instrument(tracer)
        assert isinstance(handler, SbnLangChainHandler)

    def test_on_llm_start_end(self, tracer):
        from sbn_sdk.integrations.langchain import SbnLangChainHandler
        handler = SbnLangChainHandler(tracer)
        with patch.object(tracer, "create_span", return_value=MockSpan()) as mock_create:
            handler.on_llm_start({"kwargs": {"model_name": "gpt-4"}}, ["hello"], run_id="run-1")
            mock_create.assert_called_once()


class TestLangGraphIntegration:
    def test_instrument_graph(self, tracer):
        from sbn_sdk.integrations.langgraph import instrument
        patcher = instrument(tracer)
        graph = MagicMock()
        graph.nodes = {"node1": MagicMock()}
        result = patcher(graph)
        assert result is graph


@pytest.mark.skip(reason="requires openai-agents")
class TestOpenAIAgentsIntegration:
    def test_instrument_patches_runner(self, tracer):
        from sbn_sdk.integrations.openai_agents import instrument
        with patch("sbn_sdk.integrations.openai_agents.Runner") as MockRunner:
            instrument(tracer)
            assert MockRunner.run != MockRunner.run


@pytest.mark.skip(reason="requires pyautogen")
class TestAutoGenIntegration:
    def test_instrument_patches_send(self, tracer):
        from sbn_sdk.integrations.autogen import instrument
        with patch("sbn_sdk.integrations.autogen.Agent") as MockAgent:
            instrument(tracer)
            assert hasattr(MockAgent.send, "_sbn_patched")
