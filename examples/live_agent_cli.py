"""Interactive CLI for running real agent prompts through analyzer backend."""

from __future__ import annotations

import json
import os

import requests


BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("SBN_API_KEY", "analyst-local-dev-key")
RUN_ENDPOINT = f"{BACKEND_BASE_URL.rstrip('/')}/api/v1/agent/run"


def run_prompt(
    api_key: str,
    project_name: str,
    model_name: str,
    prompt: str,
    max_tokens: int = 512,
    temperature: float = 0.2,
) -> dict[str, object]:
    """Send prompt to live backend agent endpoint."""

    payload = {
        "project_name": project_name,
        "prompt": prompt,
        "model_name": model_name,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    response = requests.post(
        RUN_ENDPOINT,
        json=payload,
        headers={"X-API-Key": api_key},
        timeout=120,
    )
    response.raise_for_status()
    return response.json()


def main() -> None:
    """Run interactive prompt loop until user exits."""

    print("Realtime Agent Analyzer CLI")
    print(f"Backend: {RUN_ENDPOINT}")
    print("Type 'exit' to quit.\n")

    api_key = input("API key [analyst-local-dev-key]: ").strip() or API_KEY
    project_name = input("Project name [resume-star-project]: ").strip() or "resume-star-project"
    model_name = input("Model name [gpt-4o-mini]: ").strip() or "gpt-4o-mini"

    while True:
        prompt = input("\nPrompt> ").strip()
        if not prompt:
            continue
        if prompt.lower() in {"exit", "quit"}:
            print("Bye.")
            return

        try:
            result = run_prompt(
                api_key=api_key,
                project_name=project_name,
                model_name=model_name,
                prompt=prompt,
            )
        except requests.HTTPError as exc:
            detail = ""
            if exc.response is not None:
                try:
                    detail = json.dumps(exc.response.json(), indent=2)
                except ValueError:
                    detail = exc.response.text
            print(f"Agent execution failed:\n{detail or exc}")
            continue
        except requests.RequestException as exc:
            print(f"Request failed: {exc}")
            continue

        print("\nResponse:")
        print(result.get("response", ""))
        print("\nTelemetry:")
        print(
            f"latency_ms={result.get('latency_ms')} total_tokens={result.get('total_tokens')} "
            f"cost={result.get('cost')} flagged={result.get('flagged_for_governance')}"
        )
        reasons = result.get("governance_reasons", [])
        if reasons:
            print("Governance reasons: " + " | ".join(str(item) for item in reasons))


if __name__ == "__main__":
    main()
