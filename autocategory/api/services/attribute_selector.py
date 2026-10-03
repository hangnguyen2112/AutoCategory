"""
Attribute selector — 3-bước pipeline:

  Bước 1 (LLM):   Trích xuất raw values từ title/description
                   → {"brand": "Apple", "dong_may_iphone": "iPhone 14 Pro Max", ...}

  Bước 2 (Embed):  Embed từng raw value thành vector

  Bước 3 (Qdrant): Tìm option gần nhất trong collection attribute_options
                   (filter by field_id để chỉ search trong options của field đó)
                   → option_value thực sự có trong DB

Xử lý 2-pass để tôn trọng parent_field:
  Pass 1: root fields (không có parent_field_id)
  Pass 2: conditional fields có parent_field_value khớp kết quả Pass 1

Index phải được build trước qua /api/admin/categories/rebuild-attribute-index.
Fallback về in-memory cosine nếu Qdrant chưa có index.
"""
from __future__ import annotations

import logging
from typing import Any

from services.embedder import embed_single
from services.llm_service import extract_attribute_values, extract_attribute_values_direct
from services import qdrant_service, attribute_rules
from config import settings
from services import embedder, llm_service
from services.result_cache import cache, taxonomy_version, mark_uncacheable

logger = logging.getLogger(__name__)

_OPT_MATCH_THRESHOLD = 0.75
_DIRECT_THRESHOLD = 20        # fields với ≤ n options → LLM chọn trực tiếp


# ─── helpers ──────────────────────────────────────────────────────────────────

async def _ensure_qdrant_ready() -> None:
    """Raise RuntimeError nếu collection attribute_options chưa có data."""
    try:
        client = qdrant_service.get_client()
        info = await client.get_collection(qdrant_service.ATTR_COLLECTION)
        count = getattr(info, "points_count", None) or 0
    except Exception as exc:
        raise RuntimeError(
            "Qdrant attribute_options collection không tồn tại. "
            "Vui lòng gọi POST /api/admin/categories/rebuild-attribute-index trước."
        ) from exc
    if count == 0:
        raise RuntimeError(
            "Qdrant attribute_options index chưa được build. "
            "Vui lòng gọi POST /api/admin/categories/rebuild-attribute-index trước."
        )


async def _match_via_qdrant(
    fields: list[dict],
    raw_values: dict[str, str],
) -> dict[str, Any]:
    """
    Bước 3: Embed raw_value rồi search Qdrant để tìm option gần nhất.
    fields: chỉ các fields có field_options và có raw value từ LLM.
    """
    result: dict[str, Any] = {}
    for field in fields:
        fkey = field["field_key"]
        raw = raw_values.get(fkey)
        if not raw:
            continue
        field_id = field.get("id")
        opts = field.get("field_options") or []
        if not opts:
            # text field — dùng raw value trực tiếp
            result[fkey] = raw
            continue
        if not field_id:
            continue
        exact = attribute_rules.canonical_value(field, raw)
        if exact is not None:
            result[fkey] = exact
            continue
        try:
            vec = await embed_single(raw)
            hits = await qdrant_service.search_attribute_options(
                query_vector=vec,
                field_id=field_id,
                top_k=2,
            )
            margin = hits[0]["score"] - hits[1]["score"] if len(hits) > 1 else 1.0
            value = attribute_rules.canonical_value(field, hits[0].get("option_value")) if hits else None
            if value is not None and hits[0]["score"] >= _OPT_MATCH_THRESHOLD and margin >= 0.05:
                result[fkey] = value
                logger.debug(
                    "qdrant match: field '%s' raw='%s' → '%s' (score=%.3f)",
                    fkey, raw, hits[0]["option_value"], hits[0]["score"],
                )
        except Exception as exc:
            mark_uncacheable()
            logger.warning("qdrant search failed for field '%s': %s", fkey, exc)
    return result


# ─── core per-pass logic ──────────────────────────────────────────────────────

async def _process_fields(
    fields: list[dict],
    title: str,
    description: str,
) -> dict[str, Any]:
    """
    Hybrid: fields ≤ _DIRECT_THRESHOLD options → LLM chọn từ options trực tiếp.
            fields > _DIRECT_THRESHOLD options → LLM extract raw → Qdrant search.
    """
    if not fields:
        return {}

    direct_fields: list[dict] = []   # text + ít options → LLM chọn trực tiếp
    qdrant_fields: list[dict] = []   # nhiều options → raw extract + Qdrant

    for field in fields:
        opts = field.get("field_options") or []
        if len(opts) <= _DIRECT_THRESHOLD:
            direct_fields.append(field)
        else:
            qdrant_fields.append(field)

    result: dict[str, Any] = {}

    # ── Đường 1: LLM chọn trực tiếp từ options ───────────────────────────────
    if direct_fields:
        direct_result = await extract_attribute_values_direct(title, description, direct_fields)
        logger.info("LLM direct result: %s", direct_result)
        for field in direct_fields:
            fkey = field["field_key"]
            if fkey not in direct_result:
                continue
            val = direct_result[fkey]
            opts = field.get("field_options") or []
            if not opts:
                result[fkey] = val
                continue
            # Validate: phải là một trong các options (exact hoặc case-insensitive)
            valid = {o["value"]: o["value"] for o in opts}
            valid_lower = {o["value"].lower(): o["value"] for o in opts}
            if val in valid:
                result[fkey] = val
            elif val.lower() in valid_lower:
                result[fkey] = valid_lower[val.lower()]
            else:
                logger.debug("direct: '%s' returned '%s' not in options — skipping", fkey, val)

    # ── Đường 2: LLM extract raw → Qdrant ────────────────────────────────────
    if qdrant_fields:
        field_defs = [{"field_key": f["field_key"], "field_label": f.get("field_label", "")}
                      for f in qdrant_fields]
        raw_values = await extract_attribute_values(title, description, field_defs)
        logger.info("LLM raw values (qdrant path): %s", raw_values)
        if raw_values:
            matched = await _match_via_qdrant(qdrant_fields, raw_values)
            result.update(matched)

    return result


# ─── main ─────────────────────────────────────────────────────────────────────

async def select_attributes(
    attributes: list[dict],
    title: str,
    description: str,
    detected_attributes: dict[str, Any],
) -> dict[str, Any]:
    """
    Pipeline chính: LLM extract → embed → Qdrant search → selected values.
    """
    if not attributes or not (title or description):
        return {}

    # Exact evidence is resolved before LLM calls, so child options can identify
    # their parent without requiring the LLM to guess the parent first.
    revision = await taxonomy_version()
    return await cache.get_or_compute(
        "attributes_quick", [revision, embedder.model_name(),
            llm_service.cache_identity(llm_service.SYSTEM_EXTRACT_ATTRS, llm_service.SYSTEM_EXTRACT_DIRECT),
            title, description, attributes, detected_attributes],
        settings.cache_llm_ttl,
        lambda: attribute_rules.select_with_dependencies(attributes, title, description, _process_fields),
        enabled=revision is not None,
    )

