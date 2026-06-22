"""MongoDB async connection and Beanie initialization."""

from __future__ import annotations

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings


async def init_mongodb() -> None:
    client: AsyncIOMotorClient = AsyncIOMotorClient(settings.mongodb_url)
    await init_beanie(
        database=client.get_default_database(),
        document_models=[
            "app.db.mongo_models.TraceDocument",
        ],
    )
