# SBN SDK

Python SDK for intercepting LLM calls, collecting telemetry, applying governance checks, and forwarding traces to the backend.

## Authenticated Usage

When backend API key auth is enabled, pass `api_key` to `monitor_llm`:

```python
from sbn_sdk import monitor_llm

@monitor_llm(
	project_name="resume-star-project",
	backend_url="http://localhost:8000",
	api_key="ingest-local-dev-key",
	model_name="gpt-4o-mini",
)
def call_model(prompt: str) -> dict[str, object]:
	return {"response": "ok", "total_tokens": 10, "cost": 0.001, "model_name": "gpt-4o-mini"}
```
