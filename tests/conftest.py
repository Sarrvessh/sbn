from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.mongo_models import TraceDocument
from app.repositories.trace_repository import TraceRepository
from app.schemas.trace import TraceIngestRequest

TEST_MONGODB_URL = "mongodb://localhost:27017/ai_observability_test"


@pytest_asyncio.fixture(scope="function")
async def mongo_db():
    client = AsyncIOMotorClient(TEST_MONGODB_URL)
    await init_beanie(
        database=client.get_default_database(),
        document_models=[TraceDocument],
    )
    yield
    await client.drop_database("ai_observability_test")
    client.close()


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest_asyncio.fixture
async def trace_repository(mongo_db) -> TraceRepository:
    return TraceRepository()


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
async def seeded_traces(trace_repository: TraceRepository) -> list[TraceDocument]:
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
