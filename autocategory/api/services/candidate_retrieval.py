"""Merge category vectors with validated lexical and semantic option evidence."""
from __future__ import annotations

import asyncio
import logging
import re

from database import SessionLocal
from config import settings
from models import Category, CategoryField
from services import qdrant_service
from services.attribute_rules import (
    canonical_value, explicit_value, normalize_text, option_names, positive_option_mention,
    prepare_mentions,
)
from services.result_cache import cache, taxonomy_version, mark_uncacheable
from services.omni_sync_service import _field_to_dict

logger = logging.getLogger(__name__)


def _load_option_catalog() -> list[dict]:
    # Detach all JSON values and return the connection before any network awaits.
    with SessionLocal() as db:
        cats = db.query(Category).filter(Category.is_active == 1).all()
        parent_ids = {c.parent_id for c in cats}
        leaves = {c.id for c in cats if c.id not in parent_ids}
        return [{**_field_to_dict(f), "category_id": f.category_id}
                for f in db.query(CategoryField).filter(CategoryField.category_id.in_(leaves)).all()]


def _discriminating_field(field: dict) -> bool:
    name = normalize_text(f"{field.get('field_key', '')} {field.get('field_label', '')}")
    return field.get("field_type") in {"select", "radio"} and not re.search(
        r"\b(?:tinh trang|condition|bao hanh|warranty|mau sac|color|colour|"
        r"dung luong|capacity|storage|ram|kich thuoc|size|nam san xuat|year|"
        r"so km|mileage|dien tich|area|gia|price|chat lieu|material|"
        r"nguon dien|nguon nang luong|power source)\b", name,
    )


def _useful_value(value: str) -> bool:
    normalized = normalize_text(value)
    return any(c.isalpha() for c in normalized) and normalized not in {
        "khac", "other", "moi", "new", "da su dung", "used", "khong", "co", "yes", "no",
        "khong ro", "chua ro", "khong xac dinh", "khong biet", "unknown", "none", "n a",
    }


async def search_option_evidence(vector: list[float], title: str, description: str) -> list[dict]:
    async def load_catalog():
        revision = await taxonomy_version()
        def prepare():
            return [{**f, "field_options": [
                {**o, "_normalized_names": option_names(o)} for o in f.get("field_options") or []
            ]} for f in _load_option_catalog() if _discriminating_field(f)]
        return await cache.get_or_compute(
            "option_catalog", revision, settings.cache_catalog_ttl,
            lambda: asyncio.to_thread(prepare), enabled=revision is not None,
        )
    catalog, vector_hits = await asyncio.gather(
        load_catalog(),
        qdrant_service.search_options_global(vector), return_exceptions=True,
    )
    if isinstance(catalog, BaseException):
        mark_uncacheable()
        logger.warning("Option catalog unavailable; continuing category search: %s", catalog)
        return []
    if isinstance(vector_hits, BaseException):
        mark_uncacheable()
        logger.warning("Option vectors unavailable; using exact option evidence: %s", vector_hits)
        vector_hits = []
    fields = {f["id"]: f for f in catalog}
    text = f"{title}\n{description}"
    clauses = prepare_mentions(text)
    matches = {}
    for field in fields.values():
        value = explicit_value(field, title, description, prepared=clauses)
        if value is not None and _useful_value(value):
            matches[(field["id"], value)] = {
                "category_id": field["category_id"], "field_key": field["field_key"],
                "field_label": field["field_label"], "option_value": value,
                "parent_field_value": field.get("parent_field_value"),
                "match_type": "exact", "score": 1.0,
            }
    normalized = normalize_text(text)
    for hit in vector_hits:
        field = fields.get(hit.get("field_id"))
        if field is None or field["category_id"] != hit.get("category_id"):
            continue  # Includes stale IDs left behind by an Omni sync.
        value = canonical_value(field, hit.get("option_value"))
        if value is None or not _useful_value(value) or hit.get("score", 0) < 0.80:
            continue
        option = next(o for o in field["field_options"] if str(o.get("value")) == value)
        names = option_names(option)
        mentioned = [n for n in names if re.search(rf"(?<!\w){re.escape(n)}(?!\w)", normalized)]
        if mentioned and not any(positive_option_mention(text, n, prepared=clauses) for n in mentioned):
            continue
        matches.setdefault((field["id"], value), {
            "category_id": field["category_id"], "field_key": field["field_key"],
            "field_label": field["field_label"], "option_value": value,
            "parent_field_value": field.get("parent_field_value"),
            "match_type": "semantic", "score": hit["score"],
        })
    return sorted(matches.values(), key=lambda m: (m["match_type"] != "exact", -m["score"],
                                                  -len(normalize_text(m["option_value"]))))


async def retrieve_candidates(category_vector: list[float], option_vector: list[float],
                              title: str, description: str, top_k: int) -> list[dict]:
    categories, evidence = await asyncio.gather(
        qdrant_service.search_categories(category_vector, top_k=top_k),
        search_option_evidence(option_vector, title, description),
    )
    # Count ranks per category, not per option: large model lists must not win by size.
    evidence_by_category = {}
    for match in evidence:
        evidence_by_category.setdefault(match["category_id"], []).append(match)
    option_ids = list(evidence_by_category)[:15]
    known = {c["category_id"] for c in categories}
    try:
        profiles = await qdrant_service.get_category_profiles([cid for cid in option_ids if cid not in known])
    except Exception as exc:
        mark_uncacheable()
        logger.warning("Option category lookup unavailable; keeping category candidates: %s", exc)
        profiles = []
    merged = {c["category_id"]: {**c, "retrieval_sources": ["category"],
                                "retrieval_score": 1 / (60 + rank)}
              for rank, c in enumerate(categories, 1)}
    for c in profiles:
        merged[c["category_id"]] = {**c, "similarity_score": 0.0,
                                    "retrieval_sources": [], "retrieval_score": 0.0}
    for rank, cid in enumerate(option_ids, 1):
        candidate = merged.get(cid)
        if candidate is None:
            continue
        matches = evidence_by_category[cid]
        weight = 3.0 if matches[0]["match_type"] == "exact" else 1.0
        candidate["retrieval_score"] += weight / (60 + rank)
        candidate["retrieval_sources"].append("option")
        candidate["matched_options"] = matches[:5]
    return sorted(merged.values(), key=lambda c: -c["retrieval_score"])[:40]
