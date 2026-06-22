"""Decorator-based LLM call interception for telemetry and governance."""

from __future__ import annotations

import asyncio
import functools
import inspect
import uuid
from collections.abc import Awaitable, Callable, Mapping
from datetime import datetime, timezone
from time import perf_counter
from typing import Any, ParamSpec, TypeVar, cast

from sbn_sdk.client import get_or_create_client
from sbn_sdk.governance import is_prompt_flagged
from sbn_sdk.models import TracePayload

P = ParamSpec("P")
R = TypeVar("R")
ResultMetadataExtractor = Callable[[Any], Mapping[str, Any]]


def monitor_llm(
    project_name: str,
    backend_url: str,
    api_key: str | None = None,
    model_name: str | None = None,
    prompt_arg_name: str = "prompt",
    metadata_extractor: ResultMetadataExtractor | None = None,
) -> Callable[[Callable[P, R] | Callable[P, Awaitable[R]]], Callable[P, R] | Callable[P, Awaitable[R]]]:
    """Monitor wrapped LLM-like function and emit telemetry traces.

    Supports both synchronous and asynchronous functions. Payload delivery is
    scheduled in a non-blocking fashion using either `asyncio.create_task`
    (when event loop is available) or a background thread pool.
    """

    def decorator(
        func: Callable[P, R] | Callable[P, Awaitable[R]],
    ) -> Callable[P, R] | Callable[P, Awaitable[R]]:
        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                prompt = _extract_prompt(func, args, kwargs, prompt_arg_name)
                flagged = is_prompt_flagged(prompt)
                started_at = perf_counter()
                timestamp = datetime.now(timezone.utc)

                try:
                    result = await cast(Callable[P, Awaitable[R]], func)(*args, **kwargs)
                    latency_ms = (perf_counter() - started_at) * 1000
                    try:
                        payload = _build_payload(
                            project_name=project_name,
                            prompt=prompt,
                            result=result,
                            model_name=model_name,
                            latency_ms=latency_ms,
                            flagged_for_governance=flagged,
                            timestamp=timestamp,
                            metadata_extractor=metadata_extractor,
                        )
                        _dispatch_payload(backend_url, payload, api_key)
                    except Exception:
                        pass
                    return result
                except Exception as exc:
                    latency_ms = (perf_counter() - started_at) * 1000
                    try:
                        payload = _build_error_payload(
                            project_name=project_name,
                            prompt=prompt,
                            error=exc,
                            model_name=model_name,
                            latency_ms=latency_ms,
                            flagged_for_governance=flagged,
                            timestamp=timestamp,
                        )
                        _dispatch_payload(backend_url, payload, api_key)
                    except Exception:
                        pass
                    raise

            return async_wrapper

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            prompt = _extract_prompt(func, args, kwargs, prompt_arg_name)
            flagged = is_prompt_flagged(prompt)
            started_at = perf_counter()
            timestamp = datetime.now(timezone.utc)

            try:
                result = cast(Callable[P, R], func)(*args, **kwargs)
                latency_ms = (perf_counter() - started_at) * 1000
                try:
                    payload = _build_payload(
                        project_name=project_name,
                        prompt=prompt,
                        result=result,
                        model_name=model_name,
                        latency_ms=latency_ms,
                        flagged_for_governance=flagged,
                        timestamp=timestamp,
                        metadata_extractor=metadata_extractor,
                    )
                    _dispatch_payload(backend_url, payload, api_key)
                except Exception:
                    pass
                return result
            except Exception as exc:
                latency_ms = (perf_counter() - started_at) * 1000
                try:
                    payload = _build_error_payload(
                        project_name=project_name,
                        prompt=prompt,
                        error=exc,
                        model_name=model_name,
                        latency_ms=latency_ms,
                        flagged_for_governance=flagged,
                        timestamp=timestamp,
                    )
                    _dispatch_payload(backend_url, payload, api_key)
                except Exception:
                    pass
                raise

        return sync_wrapper

    return decorator


def _extract_prompt(
    func: Callable[..., Any],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    prompt_arg_name: str,
) -> str:
    """Extract prompt argument by name; falls back to an empty string."""

    if prompt_arg_name in kwargs:
        return str(kwargs[prompt_arg_name])

    try:
        bound = inspect.signature(func).bind_partial(*args, **kwargs)
        if prompt_arg_name in bound.arguments:
            return str(bound.arguments[prompt_arg_name])
    except TypeError:
        pass

    return ""


def _build_payload(
    project_name: str,
    prompt: str,
    result: Any,
    model_name: str | None,
    latency_ms: float,
    flagged_for_governance: bool,
    timestamp: datetime,
    metadata_extractor: ResultMetadataExtractor | None,
) -> TracePayload:
    """Build success payload from function result and optional metadata extractor."""

    extracted = _extract_result_fields(result, model_name, metadata_extractor)
    return TracePayload(
        request_id=uuid.uuid4().hex,
        project_name=project_name,
        prompt=prompt,
        response=extracted["response"],
        model_name=extracted["model_name"],
        total_tokens=extracted["total_tokens"],
        cost=extracted["cost"],
        latency_ms=max(latency_ms, 0.001),
        status="success",
        flagged_for_governance=flagged_for_governance,
        timestamp=timestamp,
    )


def _build_error_payload(
    project_name: str,
    prompt: str,
    error: Exception,
    model_name: str | None,
    latency_ms: float,
    flagged_for_governance: bool,
    timestamp: datetime,
) -> TracePayload:
    """Build telemetry payload for failed LLM execution."""

    return TracePayload(
        request_id=uuid.uuid4().hex,
        project_name=project_name,
        prompt=prompt,
        response=f"{type(error).__name__}: {error}",
        model_name=model_name or "unknown",
        total_tokens=0,
        cost=0.0,
        latency_ms=max(latency_ms, 0.001),
        status="error",
        flagged_for_governance=flagged_for_governance,
        timestamp=timestamp,
    )


def _extract_result_fields(
    result: Any,
    default_model_name: str | None,
    metadata_extractor: ResultMetadataExtractor | None,
) -> dict[str, Any]:
    """Normalize wrapped result into canonical telemetry fields."""

    if metadata_extractor is not None:
        metadata = dict(metadata_extractor(result))
    elif isinstance(result, Mapping):
        metadata = dict(result)
    else:
        metadata = {
            "response": getattr(result, "response", None)
            or getattr(result, "content", None)
            or getattr(result, "text", None)
            or str(result),
            "model_name": getattr(result, "model_name", None)
            or getattr(result, "model", None),
            "total_tokens": getattr(result, "total_tokens", None)
            or getattr(result, "tokens", None),
            "cost": getattr(result, "cost", None),
        }

    response_value = (
        metadata.get("response")
        or metadata.get("content")
        or metadata.get("text")
        or metadata.get("output")
        or str(result)
    )
    model_name_value = metadata.get("model_name") or metadata.get("model") or default_model_name
    tokens_value = metadata.get("total_tokens") if metadata.get("total_tokens") is not None else (metadata.get("tokens") or 0)
    cost_value = metadata.get("cost") if metadata.get("cost") is not None else 0.0

    return {
        "response": str(response_value),
        "model_name": str(model_name_value or "unknown"),
        "total_tokens": int(tokens_value),
        "cost": float(cost_value),
    }


def _dispatch_payload(backend_url: str, payload: TracePayload, api_key: str | None) -> None:
    """Send payload asynchronously without delaying caller execution."""

    client = get_or_create_client(backend_url, api_key=api_key)

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        client.send_non_blocking(payload)
        return

    try:
        task = loop.create_task(client.send_async(payload))
        task.add_done_callback(_handle_task_exception)
    except RuntimeError:
        client.send_non_blocking(payload)


def _handle_task_exception(task: asyncio.Task[None]) -> None:
    exc = task.exception()
    if exc is not None:
        import logging
        logging.getLogger(__name__).warning("Async telemetry send failed: %s", exc)
