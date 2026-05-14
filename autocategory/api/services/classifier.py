"""
Classifier – pipeline chính tích hợp tất cả service.
"""
from __future__ import annotations

import asyncio
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
        # Step 1+3 – Product understanding & embed raw text in parallel
        raw_embed_text = f"Tiêu đề gốc: {title}\nMô tả gốc: {description}".strip()
        understanding, product_vector = await asyncio.gather(
            llm_service.understand_product(
                title=title,
                description=description,
                price=price,
                image_urls=image_urls,
            ),
            embedder.embed_single(raw_embed_text),
        )
        understand_conf = understanding.get("confidence", 0.5)

    # Step 2 – Build embedding text (for context in rerank prompt)
    normalized_text: str = understanding.get("normalized_product_text", title)
    product_embedding_text = (
        f"Tiêu đề gốc: {title}\n"
        f"Mô tả gốc: {description}\n"
        f"Nội dung chuẩn hóa: {normalized_text}"
    ).strip() if not fast else product_embedding_text

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

    top1 = candidates[0]
    top2_sim: float = candidates[1].get("similarity_score", 0.0) if len(candidates) > 1 else 0.0
    top1_sim: float = top1.get("similarity_score", 0.0)
    margin = top1_sim - top2_sim

    # Shortcut: vector đã chắc chắn, bỏ qua LLM rerank
    if top1_sim >= 0.57 and margin >= 0.06:
        rerank = {
            "category_id": top1["category_id"],
            "confidence": round(min(top1_sim + 0.05, 0.99), 4),
            "reason": "vector similarity high, rerank skipped",
            "alternatives": [
                {"category_id": c["category_id"], "confidence": round(c.get("similarity_score", 0.0), 4)}
                for c in candidates[1:3]
            ],
        }
    else:
        # Step 5 – LLM rerank với top 5
        rerank = await llm_service.rerank_categories(
            product_embedding_text=product_embedding_text,
            understanding_confidence=understand_conf,
            text_image_consistency=understanding.get("text_image_consistency", "unknown"),
            candidates=candidates[:5],
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
