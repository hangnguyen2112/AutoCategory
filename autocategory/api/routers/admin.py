"""
Admin router: build/rebuild vector index từ JSON.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from config import settings
from services import category_builder, embedder, qdrant_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/build-index", summary="Build/rebuild vector index từ categories JSON")
async def build_index():
    try:
        categories = category_builder.load_categories(settings.categories_json_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    profiles = category_builder.build_leaf_profiles(categories)
    if not profiles:
        raise HTTPException(status_code=400, detail="Không tìm thấy leaf category active nào.")

    logger.info("Building embeddings for %d leaf categories...", len(profiles))

    # Embed theo batch 32 để tránh timeout
    batch_size = 32
    all_vectors: list[list[float]] = []
    for i in range(0, len(profiles), batch_size):
        batch = profiles[i : i + batch_size]
        docs = [p["category_document"] for p in batch]
        vecs = await embedder.embed_texts(docs)
        all_vectors.extend(vecs)

    # Xóa collection cũ rồi upsert mới
    await qdrant_service.delete_collection()
    upserted = await qdrant_service.upsert_categories(profiles, all_vectors)

    return {
        "status": "ok",
        "total_categories_in_file": len(categories),
        "leaf_categories_indexed": upserted,
    }


@router.get("/index-info", summary="Thông tin collection Qdrant")
async def index_info():
    from qdrant_client.http.exceptions import UnexpectedResponse
    try:
        client = qdrant_service.get_client()
        info = await client.get_collection(settings.qdrant_collection)
        return {
            "collection": settings.qdrant_collection,
            "vectors_count": info.vectors_count,
            "status": info.status,
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Qdrant error: {exc}") from exc
