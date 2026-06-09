"""
Classifier – pipeline chính tích hợp tất cả service.
"""
from __future__ import annotations

import logging
from typing import Any, Literal

from services import embedder, llm_service, qdrant_service

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
        product_vector = await embedder.embed_single(product_embedding_text)
        understand_conf: float = 0.5
    else:
        # Step 1 – Product understanding
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

        # Step 3 – Embed product_embedding_text (đã có normalized text)
        product_vector = await embedder.embed_single(product_embedding_text)

    # Step 4 – Vector search
    top_k = 20 if fast else (30 if understand_conf < 0.75 else 20)
    candidates = await qdrant_service.search_categories(product_vector, top_k=top_k)

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

    # Step 5 – LLM rerank với top 20
    rerank = await llm_service.rerank_categories(
        product_embedding_text=product_embedding_text,
        understanding_confidence=understand_conf,
        text_image_consistency=understanding.get("text_image_consistency", "unknown"),
        candidates=candidates[:20],
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
