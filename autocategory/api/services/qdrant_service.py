"""
Qdrant service – upsert và search category vectors.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from config import settings

logger = logging.getLogger(__name__)

_client: AsyncQdrantClient | None = None

VECTOR_SIZE = 768  # Alibaba-NLP/gte-multilingual-base output dim


def get_client() -> AsyncQdrantClient:
    global _client
    if _client is None:
        _client = AsyncQdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
        )
    return _client


async def ensure_collection() -> None:
    client = get_client()
    exists = await client.collection_exists(settings.qdrant_collection)
    if not exists:
        await client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
        logger.info("Created Qdrant collection: %s", settings.qdrant_collection)
    else:
        logger.info("Qdrant collection already exists: %s", settings.qdrant_collection)


async def upsert_categories(
    profiles: list[dict[str, Any]],
    vectors: list[list[float]],
) -> int:
    client = get_client()
    await ensure_collection()

    points = [
        PointStruct(
            id=str(uuid.uuid5(uuid.NAMESPACE_OID, str(p["category_id"]))),
            vector=vec,
            payload={k: v for k, v in p.items() if k != "category_document"},
        )
        for p, vec in zip(profiles, vectors)
    ]

    await client.upsert(
        collection_name=settings.qdrant_collection,
        points=points,
        wait=True,
    )
    logger.info("Upserted %d category vectors", len(points))
    return len(points)


async def search_categories(
    query_vector: list[float],
    top_k: int = 20,
) -> list[dict[str, Any]]:
    client = get_client()

    results = await client.search(
        collection_name=settings.qdrant_collection,
        query_vector=query_vector,
        query_filter=Filter(
            must=[
                FieldCondition(key="is_active", match=MatchValue(value=True)),
                FieldCondition(key="is_leaf", match=MatchValue(value=True)),
            ]
        ),
        limit=top_k,
        with_payload=True,
    )

    return [
        {
            **r.payload,
            "similarity_score": round(r.score, 4),
        }
        for r in results
    ]


async def delete_collection() -> None:
    client = get_client()
    await client.delete_collection(settings.qdrant_collection)
    logger.info("Deleted collection: %s", settings.qdrant_collection)


class QdrantService:
    """Wrapper class for Qdrant operations"""
    
    def __init__(self):
        self.client = get_client()
    
    async def ensure_collection(self) -> None:
        """Ensure collection exists"""
        await ensure_collection()
    
    async def upsert_categories(
        self,
        profiles: list[dict[str, Any]],
        vectors: list[list[float]],
    ) -> int:
        """Upsert category profiles with vectors"""
        return await upsert_categories(profiles, vectors)
    
    async def search_categories(
        self,
        query_vector: list[float],
        top_k: int = 20,
    ) -> list[dict[str, Any]]:
        """Search for similar categories"""
        return await search_categories(query_vector, top_k)
    
    async def delete_collection(self) -> None:
        """Delete the collection"""
        await delete_collection()
    
    async def get_collection_info(self) -> dict:
        """Get collection information"""
        try:
            info = await self.client.get_collection(settings.qdrant_collection)
            return {
                "name": settings.qdrant_collection,
                "vectors_count": info.vectors_count if hasattr(info, 'vectors_count') else 0,
                "points_count": info.points_count if hasattr(info, 'points_count') else 0,
                "status": "ready",
            }
        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            return {
                "name": settings.qdrant_collection,
                "vectors_count": 0,
                "points_count": 0,
                "status": "not_found",
                "error": str(e),
            }
