"""Sample client demonstrating SDK interception for sync and async LLM calls."""

from __future__ import annotations

import asyncio
import os
import random
import time

from sbn_sdk import monitor_llm


API_KEY = os.getenv("SBN_API_KEY", "ingest-local-dev-key")


@monitor_llm(
    project_name="resume-star-project",
    backend_url="http://localhost:8000",
    api_key=API_KEY,
    model_name="gpt-4o-mini",
)
def generate_text_sync(prompt: str) -> dict[str, object]:
    """Simulate a synchronous LLM call."""

    time.sleep(random.uniform(0.05, 0.2))
    return {
        "response": f"Synchronous response for: {prompt}",
        "total_tokens": random.randint(40, 120),
        "cost": round(random.uniform(0.001, 0.02), 6),
        "model_name": "gpt-4o-mini",
    }


@monitor_llm(
    project_name="resume-star-project",
    backend_url="http://localhost:8000",
    api_key=API_KEY,
    model_name="gpt-4o-mini",
)
async def generate_text_async(prompt: str) -> dict[str, object]:
    """Simulate an asynchronous LLM call."""

    await asyncio.sleep(random.uniform(0.05, 0.2))
    return {
        "response": f"Asynchronous response for: {prompt}",
        "total_tokens": random.randint(30, 110),
        "cost": round(random.uniform(0.001, 0.015), 6),
        "model_name": "gpt-4o-mini",
    }


async def main() -> None:
    """Send sample traces, including one governance-flagged prompt."""

    print(generate_text_sync("Write a welcome email for onboarding."))
    print(generate_text_sync("Do not share this secret launch plan."))
    print(await generate_text_async("Summarize this quarterly report."))


if __name__ == "__main__":
    asyncio.run(main())
