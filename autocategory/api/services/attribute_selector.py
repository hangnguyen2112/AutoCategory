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
from services import qdrant_service

logger = logging.getLogger(__name__)

_OPT_MATCH_THRESHOLD = 0.70   # Qdrant cosine score để chấp nhận option
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
        try:
            vec = await embed_single(raw)
            hits = await qdrant_service.search_attribute_options(
                query_vector=vec,
                field_id=field_id,
                top_k=1,
            )
            if hits and hits[0]["score"] >= _OPT_MATCH_THRESHOLD:
                result[fkey] = hits[0]["option_value"]
                logger.debug(
                    "qdrant match: field '%s' raw='%s' → '%s' (score=%.3f)",
                    fkey, raw, hits[0]["option_value"], hits[0]["score"],
                )
        except Exception as exc:
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

    await _ensure_qdrant_ready()

    field_by_id: dict[int, dict] = {f["id"]: f for f in attributes if f.get("id")}

    # ── Pass 1: root fields ───────────────────────────────────────────────────
    root_fields = [f for f in attributes if not f.get("parent_field_id")]
    result = await _process_fields(root_fields, title, description)
    logger.info("attribute_selector pass1: %s", result)

    # ── Pass 2: conditional fields whose parent condition is satisfied ─────────
    active_conditional: list[dict] = []
    for f in attributes:
        parent_id = f.get("parent_field_id")
        if not parent_id:
            continue
        parent_field = field_by_id.get(parent_id)
        if not parent_field:
            continue
        required_val = f.get("parent_field_value")
        selected_val = result.get(parent_field["field_key"])
        if selected_val and required_val and str(selected_val) == str(required_val):
            active_conditional.append(f)

    if active_conditional:
        cond_result = await _process_fields(active_conditional, title, description)
        result.update(cond_result)
        logger.info("attribute_selector pass2 added: %s", cond_result)

    logger.info("attribute_selector final: %s", result)
    return result

