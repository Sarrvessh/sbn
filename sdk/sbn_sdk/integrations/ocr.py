"""OCR/document-processing instrumentation for SBN SDK."""

from __future__ import annotations

import functools
import logging
from typing import Any, Callable

from sbn_sdk.integrations.base import IntegrationTracer

logger = logging.getLogger(__name__)

try:
    import pytesseract

    HAS_PYTESSERACT = True
except ImportError:
    HAS_PYTESSERACT = False


def ocr_span(
    tracer: IntegrationTracer,
    name: str | None = None,
    tool_name: str = "ocr",
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator that wraps any OCR function as an SBN span.

    Usage::

        tracer = IntegrationTracer(backend_url="http://...", api_key="...")

        @ocr_span(tracer, name="extract_id_card")
        def extract_text(image_path: str) -> str:
            return pytesseract.image_to_string(image_path)
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        span_name = name or func.__name__

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            input_text = _build_input_text(args, kwargs)
            span = tracer.create_span(
                name=span_name,
                span_type="ocr",
                input_text=input_text,
                tool_name=tool_name,
            )
            try:
                result = func(*args, **kwargs)
                if span is not None:
                    output = str(result)[:5000] if result else ""
                    span.end(output=output)
                return result
            except Exception as exc:
                if span is not None:
                    span.end_error(str(exc))
                raise

        return wrapper

    return decorator


def instrument_pytesseract(tracer: IntegrationTracer) -> None:
    """Monkey-patch ``pytesseract.image_to_string`` and ``pytesseract.image_to_data``.

    Requires ``pytesseract`` to be installed separately.
    """
    if not HAS_PYTESSERACT:
        logger.warning("pytesseract not installed — skipping OCR instrumentation")
        return

    _patch_image_to_string(tracer)
    _patch_image_to_data(tracer)


def _patch_image_to_string(tracer: IntegrationTracer) -> None:
    original = pytesseract.image_to_string

    @functools.wraps(original)
    def wrapper(image, lang=None, config="", **kwargs):
        input_text = f"image:{type(image).__name__}, lang:{lang}"
        span = tracer.create_span(
            name="pytesseract.image_to_string",
            span_type="ocr",
            input_text=input_text,
            tool_name="pytesseract",
        )
        try:
            result = original(image, lang=lang, config=config, **kwargs)
            if span is not None:
                span.end(output=str(result)[:5000])
            return result
        except Exception as exc:
            if span is not None:
                span.end_error(str(exc))
            raise

    pytesseract.image_to_string = wrapper


def _patch_image_to_data(tracer: IntegrationTracer) -> None:
    original = pytesseract.image_to_data

    @functools.wraps(original)
    def wrapper(image, lang=None, config="", **kwargs):
        input_text = f"image:{type(image).__name__}, lang:{lang}"
        span = tracer.create_span(
            name="pytesseract.image_to_data",
            span_type="ocr",
            input_text=input_text,
            tool_name="pytesseract",
        )
        try:
            result = original(image, lang=lang, config=config, **kwargs)
            if span is not None:
                span.end(output=f"<{len(result)} rows>")
            return result
        except Exception as exc:
            if span is not None:
                span.end_error(str(exc))
            raise

    pytesseract.image_to_data = wrapper


def _build_input_text(args: tuple[Any, ...], kwargs: dict[str, Any]) -> str:
    parts: list[str] = []
    if args:
        first = args[0]
        if isinstance(first, str):
            parts.append(f"input:{first[:200]}")
        else:
            parts.append(f"input:{type(first).__name__}")
    if kwargs:
        for k in ("image_path", "filename", "file"):
            if k in kwargs:
                parts.append(f"{k}:{str(kwargs[k])[:200]}")
                break
    return ", ".join(parts) or "ocr_call"
