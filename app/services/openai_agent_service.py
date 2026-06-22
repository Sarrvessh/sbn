"""Service for executing live LLM agent calls (OpenAI / OpenRouter)."""

from __future__ import annotations

from dataclasses import dataclass

from openai import OpenAI

from app.core.config import settings


class AgentExecutionError(RuntimeError):
    """Raised when live agent execution fails."""


@dataclass(slots=True)
class AgentExecutionResult:
    """Normalized output from an LLM execution."""

    response_text: str
    total_tokens: int
    cost: float


_MODEL_ALIASES: dict[str, str] = {
    "openai/gpt-4o-mini": "gpt-4o-mini",
    "openai/gpt-4o": "gpt-4o",
}
_COST_PER_MILLION_INPUT: dict[str, float] = {
    "gpt-4o-mini": 0.15,
    "gpt-4o": 2.50,
}
_COST_PER_MILLION_OUTPUT: dict[str, float] = {
    "gpt-4o-mini": 0.60,
    "gpt-4o": 10.00,
}


class OpenAIAgentService:
    """Thin service wrapper around OpenAI-compatible APIs (OpenAI, OpenRouter, etc.)."""

    def __init__(self) -> None:
        if not settings.openai_api_key:
            raise AgentExecutionError(
                "OPENAI_API_KEY is not configured. Set it in your environment or .env file."
            )

        client_kwargs: dict[str, str] = {"api_key": settings.openai_api_key}
        if settings.openai_base_url:
            client_kwargs["base_url"] = settings.openai_base_url

        default_headers: dict[str, str] = {}
        if settings.openai_referer:
            default_headers["HTTP-Referer"] = settings.openai_referer
        if settings.openai_app_title:
            default_headers["X-Title"] = settings.openai_app_title
        if default_headers:
            client_kwargs["default_headers"] = default_headers

        self._client = OpenAI(**client_kwargs)

    def run_prompt(
        self,
        prompt: str,
        model_name: str,
        max_tokens: int,
        temperature: float,
    ) -> AgentExecutionResult:
        """Execute one prompt against an OpenAI-compatible API and return normalized telemetry."""

        effective_model = _MODEL_ALIASES.get(model_name, model_name)

        try:
            result = self._client.responses.create(
                model=effective_model,
                input=prompt,
                max_output_tokens=max_tokens,
                temperature=temperature,
            )
        except Exception as exc:
            raise AgentExecutionError(f"LLM execution failed: {exc}") from exc

        usage = getattr(result, "usage", None)
        input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
        output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
        total_tokens = int(getattr(usage, "total_tokens", input_tokens + output_tokens) or 0)

        response_text = getattr(result, "output_text", "") or ""
        if not response_text:
            response_text = "No textual response returned by model."

        cost = self._estimate_cost(model_name, input_tokens, output_tokens)
        return AgentExecutionResult(
            response_text=response_text,
            total_tokens=total_tokens,
            cost=cost,
        )

    def _estimate_cost(self, model_name: str, input_tokens: int, output_tokens: int) -> float:
        """Estimate request cost from known per-token prices; unknown models default to zero."""

        base = _MODEL_ALIASES.get(model_name, model_name)
        input_price = _COST_PER_MILLION_INPUT.get(base, 0.0)
        output_price = _COST_PER_MILLION_OUTPUT.get(base, 0.0)

        input_cost = (input_tokens / 1_000_000) * input_price
        output_cost = (output_tokens / 1_000_000) * output_price
        return round(input_cost + output_cost, 6)
