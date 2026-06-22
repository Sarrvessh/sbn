# AI Observability and Governance Platform

Enterprise-grade realtime analyzer for AI agents. This project combines live model execution, telemetry ingestion, governance checks, anomaly alerts, and dashboarding.

## Realtime Capabilities

- Execute real agent prompts through backend endpoint using OpenAI.
- Persist every call as a trace with latency, token usage, cost estimate, status, and governance flags.
- Detect governance risks with mock policy checks for secret keyword and common PII-like patterns.
- Generate alert feed for high latency, high cost, governance hits, and execution errors.
- Stream latest traces and metrics over SSE push to an event-driven Streamlit view.
- Enforce API key authentication with role-based access control and optional project scoping.

## Stack

- Backend: FastAPI, Pydantic, SQLAlchemy
- Database: MySQL
- Agent Runtime: OpenAI Responses API
- SDK: Python decorator interception package
- Dashboard: Streamlit
- Infra: Docker and Docker Compose

## Project Structure

.
├── app/
│   ├── api/v1/endpoints/
│   │   ├── analyzer.py
│   │   ├── auth.py
│   │   └── telemetry.py
│   ├── core/config.py
│   ├── db/{base.py,models.py,session.py,init_db.py}
│   ├── repositories/{api_key_repository.py,trace_repository.py}
│   ├── schemas/{agent.py,analytics.py,auth.py,metrics.py,trace.py}
│   ├── services/
│   │   ├── event_stream_service.py
│   │   ├── governance_service.py
│   │   ├── openai_agent_service.py
│   │   ├── realtime_event_publisher.py
│   │   ├── realtime_analyzer_service.py
│   │   └── trace_service.py
│   └── main.py
├── dashboard/app.py
├── sdk/sbn_sdk/
├── examples/live_agent_cli.py
├── requirements/{backend.txt,dashboard.txt}
├── Dockerfile.backend
├── Dockerfile.dashboard
└── docker-compose.yml

## Core Data Model

Trace entity fields:

- request_id
- project_name
- prompt
- response
- model_name
- total_tokens
- cost
- latency_ms
- status
- flagged_for_governance
- timestamp

## API Endpoints

- POST /api/v1/ingest
  - Ingest telemetry from SDK-decorated applications.

- GET /api/v1/metrics
  - Legacy aggregate metrics endpoint.

- POST /api/v1/agent/run
  - Runs a real LLM request using your OpenAI API key.
  - Persists trace automatically.
  - Returns response plus telemetry and governance reasons.

- GET /api/v1/analytics/realtime
  - Returns dashboard cards:
    - total cost
    - average latency last 50 calls
    - p95 latency last 50 calls
    - governance flagged count
    - error rate last 50 calls
    - trace count in last 24h

- GET /api/v1/traces/recent?limit=100
  - Returns newest traces for live stream table.

- GET /api/v1/alerts?limit=50
  - Returns generated alerts from recent traces.

- GET /api/v1/events/stream
  - SSE endpoint that pushes trace-ingested events to connected clients.

- POST /api/v1/auth/api-keys
  - Admin-only endpoint to mint new API keys by role and optional project scope.

- GET /api/v1/auth/api-keys
  - Admin-only endpoint to list API key metadata.

## Authentication and RBAC

All non-health endpoints require header X-API-Key.

Bootstrap keys are seeded on startup from environment:

- BOOTSTRAP_ADMIN_API_KEY
- BOOTSTRAP_ANALYST_API_KEY
- BOOTSTRAP_VIEWER_API_KEY
- BOOTSTRAP_INGEST_API_KEY

Supported roles:

- admin: full access, including API key management
- analyst: run live agent, read analytics, ingest telemetry
- viewer: read analytics, traces, alerts, SSE stream
- ingest: telemetry ingest and legacy metrics access

Project scoping:

- API keys can be restricted to a specific project via project_scope.
- Bootstrap/project scopes support comma-separated values, for example project_alpha,project_beta.
- Query filters and payload project_name are validated against the scope.

Example admin key creation request:

curl -X POST http://localhost:8000/api/v1/auth/api-keys \
  -H "Content-Type: application/json" \
  -H "X-API-Key: admin-local-dev-key" \
  -d '{"role":"viewer","project_scope":"resume-star-project","description":"read-only scoped key"}'

Example scoped analytics request:

curl "http://localhost:8000/api/v1/analytics/realtime?project_name=resume-star-project" \
  -H "X-API-Key: viewer-local-dev-key"

## Local Run Without Docker

1. Install and start local MySQL 8.x.
2. Create database and user:

   CREATE DATABASE ai_observability;
   CREATE USER 'sbn'@'localhost' IDENTIFIED BY 'sbn_password';
   GRANT ALL PRIVILEGES ON ai_observability.* TO 'sbn'@'localhost';
   FLUSH PRIVILEGES;

3. Set up Python environment:

   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   pip install -r requirements/backend.txt
   pip install -r requirements/dashboard.txt
   pip install -e .\sdk

4. Configure environment:

   Copy .env.example to .env and set:

   - DATABASE_URL=mysql+pymysql://sbn:sbn_password@localhost:3306/ai_observability
   - BACKEND_BASE_URL=http://localhost:8000
   - OPENAI_API_KEY=your_real_key
   - DEFAULT_AGENT_MODEL=gpt-4o-mini
  - BOOTSTRAP_ADMIN_API_KEY=your-admin-key
  - BOOTSTRAP_ANALYST_API_KEY=your-analyst-key
  - BOOTSTRAP_VIEWER_API_KEY=your-viewer-key
  - BOOTSTRAP_INGEST_API_KEY=your-ingest-key

5. Start backend:

   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

6. Start dashboard in another terminal:

   streamlit run dashboard/app.py

7. Open dashboard and enter API key in sidebar.
8. Run live prompts from Run Live Agent panel.

## Optional CLI Runner

Use this for terminal-driven live execution instead of dashboard input:

python examples/live_agent_cli.py

## SDK Interceptor

The SDK still provides monitor_llm decorator for instrumenting external apps. It supports sync and async wrappers and non-blocking telemetry delivery.

When backend auth is enabled, pass api_key to monitor_llm so SDK ingestion requests include X-API-Key.

## Resume Narrative Suggestion

Built a realtime AI observability and governance platform with FastAPI, MySQL, Streamlit, and a Python SDK that captures LLM telemetry, runs policy checks, emits live anomaly alerts, and supports production-style agent execution via OpenAI.
