"""
Classifier – pipeline chính tích hợp tất cả service.
"""
from __future__ import annotations

import logging
import asyncio
from typing import Any, Literal

from services import embedder, llm_service, candidate_retrieval
from config import settings
from services.result_cache import cache, taxonomy_version

logger = logging.getLogger(__name__)

DecisionType = Literal["auto_assign", "preselect", "suggest_top3", "manual_select"]


def _apply_threshold(
    understanding: dict[str, Any],
    candidates: list[dict[str, Any]],
    rerank: dict[str, Any],
) -> DecisionType:
    rerank_conf: float = rerank.get("confidence", 0.0)
    consistency: str = understanding.get("text_image_consistency", "unknown")
    understand_conf: float = understanding.get("confidence", 0.0)

    if consistency == "conflict":
        return "manual_select"

    if not candidates:
        return "manual_select"

    top1_sim: float = candidates[0].get("similarity_score", 0.0)
    top2_sim: float = candidates[1].get("similarity_score", 0.0) if len(candidates) > 1 else 0.0
    margin = top1_sim - top2_sim

    if (
        understand_conf >= 0.75
        and rerank_conf >= 0.90
        and top1_sim >= 0.78
        and margin >= 0.06
    ):
        return "auto_assign"

    if rerank_conf >= 0.75:
        return "preselect"

    if rerank_conf >= 0.55:
        return "suggest_top3"

    return "manual_select"


async def classify_product(
    title: str,
    description: str = "",
    price: float | None = None,
    image_urls: list[str] | None = None,
    fast: bool = False,
    understanding: dict[str, Any] | None = None,
) -> dict[str, Any]:
    revision = await taxonomy_version() if not image_urls else None
    identity = ["hybrid-2", revision, embedder.model_name(),
                llm_service.cache_identity(llm_service.SYSTEM_UNDERSTAND, llm_service.SYSTEM_RERANK),
                title, description, price, fast,
                settings.qdrant_host, settings.qdrant_port, settings.qdrant_collection]
    return await cache.get_or_compute(
        "classification", identity, settings.cache_classification_ttl,
        lambda: _classify_product_uncached(title, description, price, image_urls, fast, understanding),
        enabled=revision is not None,
        cacheable=lambda value: bool(value.get("selected_category") and
                                     (value.get("rerank") or {}).get("category_id")),
    )


async def _classify_product_uncached(
    title: str,
    description: str = "",
    price: float | None = None,
    image_urls: list[str] | None = None,
    fast: bool = False,
    understanding: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Full pipeline:
    1. LLM product understanding (skipped in fast mode)
    2. Build product_embedding_text
    3. Embed product
    4. Qdrant vector search top K
    5. LLM rerank
    6. Apply threshold → decision
    """

    if fast:
        # Fast mode: bỏ qua LLM call 1, embed thẳng title+description
        product_embedding_text = f"Tiêu đề: {title}\nMô tả: {description}".strip()
        understanding = {
            "normalized_product_text": title,
            "confidence": 0.5,
            "text_image_consistency": "text_only",
        }
        understand_conf: float = 0.5
    else:
        # Step 1 – Product understanding
        if understanding is None:
            understanding = await llm_service.understand_product(
                title=title,
                description=description,
                price=price,
                image_urls=image_urls,
            )
        understand_conf = understanding.get("confidence", 0.5)

        # Step 2 – Build enriched embedding text từ kết quả understanding
        normalized_text: str = understanding.get("normalized_product_text", title)
        product_embedding_text = (
            f"Tiêu đề gốc: {title}\n"
            f"Mô tả gốc: {description}\n"
            f"Nội dung chuẩn hóa: {normalized_text}"
        ).strip()

    # Step 4 – Search categories and options concurrently, preserving evidence.
    top_k = 20 if fast else (30 if understand_conf < 0.75 else 20)
    option_query = understanding.get("product_type") or understanding.get("suggested_title") or title
    product_vector, option_vector = await asyncio.gather(
        embedder.embed_single(product_embedding_text),
        embedder.embed_single(option_query or product_embedding_text),
    )
    candidates = await candidate_retrieval.retrieve_candidates(
        product_vector, option_vector, title, description, top_k,
    )

    if not candidates:
        return {
            "decision": "manual_select",
            "message": "Vector index trống. Chạy /api/admin/build-index trước.",
            "understanding": understanding,
            "product_embedding_text": product_embedding_text,
            "candidates": [],
            "rerank": None,
            "selected_category": None,
        }

    # Step 5 – Rerank every merged candidate, including option-only categories.
    rerank = await llm_service.rerank_categories(
        product_embedding_text=product_embedding_text,
        understanding_confidence=understand_conf,
        text_image_consistency=understanding.get("text_image_consistency", "unknown"),
        candidates=candidates,
    )

    # Step 6 – Threshold
    decision = _apply_threshold(understanding, candidates, rerank)

    # Lookup selected category detail
    selected_id = rerank.get("category_id")
    selected_category = next(
        (c for c in candidates if c["category_id"] == selected_id), None
    )

    # Build top3 for suggest mode
    top3 = []
    if decision in ("suggest_top3", "preselect"):
        alt_ids = {a["category_id"] for a in rerank.get("alternatives", [])}
        alt_ids.add(selected_id)
        top3 = [c for c in candidates if c["category_id"] in alt_ids][:3]

    return {
        "decision": decision,
        "understanding": understanding,
        "product_embedding_text": product_embedding_text,
        "vector_top_k": top_k,
        "candidates": candidates,
        "rerank": rerank,
        "selected_category": selected_category,
        "top3": top3,
        "llm_reason": rerank.get("reason"),  # LLM reasoning from rerank step
    }
