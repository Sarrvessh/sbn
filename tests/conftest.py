"""Test fixtures — uses SQLite in-memory for all database operations."""

from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import pytest
import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

if TYPE_CHECKING:
    from app.db.models import Trace

# Override settings for tests
from app import db  # noqa: F401
from app.db.base import Base
from app.repositories.trace_repository import TraceRepository
from app.schemas.trace import TraceIngestRequest


@pytest.fixture(scope="session")
def engine():
    eng = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=eng)
    return eng


@pytest.fixture
def db_session(engine) -> Generator[Session, None, None]:
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()


@pytest_asyncio.fixture
async def trace_repository(db_session: Session) -> TraceRepository:
    return TraceRepository(db=db_session)


@pytest.fixture
def sample_trace_payload() -> TraceIngestRequest:
    return TraceIngestRequest(
        request_id="test-req-001",
        project_name="test-project",
        prompt="What is the capital of France?",
        response="Paris",
        model_name="gpt-4o-mini",
        total_tokens=50,
        cost=0.002,
        latency_ms=350.0,
        status="success",
        flagged_for_governance=False,
        timestamp=datetime.now(timezone.utc),
    )


@pytest_asyncio.fixture
async def seeded_traces(trace_repository: TraceRepository) -> list[Trace]:
    traces_data = [
        TraceIngestRequest(
            request_id=f"seed-req-{i:03d}",
            project_name="test-project",
            prompt=f"Test prompt {i}",
            response=f"Response {i}",
            model_name="gpt-4o-mini",
            total_tokens=10 + i,
            cost=0.001 + (i * 0.0005),
            latency_ms=100.0 + (i * 20.0),
            status="success" if i % 5 != 0 else "error",
            flagged_for_governance=(i % 7 == 0),
            timestamp=datetime.now(timezone.utc),
        )
        for i in range(1, 21)
    ]
    results = []
    for p in traces_data:
        t = await trace_repository.create(p)
        results.append(t)
    return results
