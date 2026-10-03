"""Cross-category option evidence survives retrieval without polluting decisions."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from services import candidate_retrieval as retrieval, classifier, llm_service, qdrant_service


def option_field(fid, cid, key="device", value="Thẻ Nhớ", label="Loại thiết bị"):
    return {"id": fid, "category_id": cid, "field_key": key, "field_label": label,
            "field_type": "select", "field_options": [{"value": value, "label": value}],
            "parent_field_value": "Phụ kiện điện thoại"}


def category(cid):
    return {"category_id": cid, "name": f"Category {cid}", "is_active": True,
            "is_leaf": True, "similarity_score": .6}


@pytest.mark.asyncio
async def test_parallel_option_search_adds_missing_category_and_retains_vector_candidates(monkeypatch):
    categories_started, options_started = asyncio.Event(), asyncio.Event()
    async def search_categories(*args, **kwargs):
        categories_started.set()
        await options_started.wait()
        return [category(99)]
    async def search_options(*args, **kwargs):
        options_started.set()
        await categories_started.wait()
        return []
    monkeypatch.setattr(retrieval, "_load_option_catalog", lambda: [option_field(311, 98)])
    monkeypatch.setattr(qdrant_service, "search_categories", search_categories)
    monkeypatch.setattr(qdrant_service, "search_options_global", search_options)
    profiles = AsyncMock(return_value=[category(98)])
    monkeypatch.setattr(qdrant_service, "get_category_profiles", profiles)
    result = await asyncio.wait_for(retrieval.retrieve_candidates([1], [2], "Bán thẻ nhớ", "", 30), 2)
    assert [c["category_id"] for c in result] == [98, 99]
    assert result[0]["matched_options"][0]["parent_field_value"] == "Phụ kiện điện thoại"
    assert result[0]["retrieval_sources"] == ["option"]
    # The option score must never masquerade as category-vector confidence.
    assert result[0]["similarity_score"] == 0
    profiles.assert_awaited_once_with([98])


@pytest.mark.asyncio
async def test_shared_option_keeps_all_related_categories(monkeypatch):
    monkeypatch.setattr(retrieval, "_load_option_catalog", lambda: [option_field(1, 98), option_field(2, 8)])
    monkeypatch.setattr(qdrant_service, "search_options_global", AsyncMock(return_value=[]))
    hits = await retrieval.search_option_evidence([1], "Bán thẻ nhớ", "")
    assert {h["category_id"] for h in hits} == {98, 8}


@pytest.mark.asyncio
@pytest.mark.parametrize("text", ["Bán máy ảnh không kèm thẻ nhớ", "Bán máy ảnh kèm thẻ nhớ"])
async def test_negated_and_accompanying_options_do_not_add_category(monkeypatch, text):
    monkeypatch.setattr(retrieval, "_load_option_catalog", lambda: [option_field(311, 98)])
    monkeypatch.setattr(qdrant_service, "search_options_global", AsyncMock(return_value=[
        {"field_id": 311, "category_id": 98, "option_value": "Thẻ Nhớ", "score": .99},
    ]))
    assert await retrieval.search_option_evidence([1], text, "") == []


@pytest.mark.asyncio
async def test_generic_fields_removed_and_stale_option_ids_ignored(monkeypatch):
    monkeypatch.setattr(retrieval, "_load_option_catalog", lambda: [
        option_field(1, 2, "condition", "Mới", "Tình trạng"),
        option_field(2, 2, "storage", "64 GB", "Dung lượng"),
        option_field(3, 98),
        option_field(4, 129, "loai_san_pham", "Không rõ", "Loại sản phẩm"),
        option_field(5, 2, "dong_may", "15", "Dòng máy"),
        option_field(6, 21, "chat_lieu", "Mây", "Chất liệu"),
    ])
    monkeypatch.setattr(qdrant_service, "search_options_global", AsyncMock(return_value=[
        {"field_id": 1, "category_id": 2, "option_value": "Mới", "score": .99},
        {"field_id": 2, "category_id": 2, "option_value": "64 GB", "score": .99},
        {"field_id": 999, "category_id": 98, "option_value": "Thẻ Nhớ", "score": .99},
    ]))
    assert await retrieval.search_option_evidence([1], "Máy mới 64 GB, không rõ dung lượng, model 15", "") == []


@pytest.mark.asyncio
async def test_option_vector_failure_keeps_exact_evidence(monkeypatch):
    monkeypatch.setattr(retrieval, "_load_option_catalog", lambda: [option_field(311, 98)])
    monkeypatch.setattr(qdrant_service, "search_options_global", AsyncMock(side_effect=RuntimeError("missing index")))
    hits = await retrieval.search_option_evidence([1], "Bán thẻ nhớ", "")
    assert len(hits) == 1 and hits[0]["category_id"] == 98


@pytest.mark.asyncio
async def test_semantic_option_supports_different_language(monkeypatch):
    monkeypatch.setattr(retrieval, "_load_option_catalog", lambda: [option_field(311, 98)])
    monkeypatch.setattr(qdrant_service, "search_options_global", AsyncMock(return_value=[
        {"field_id": 311, "category_id": 98, "option_value": "Thẻ Nhớ", "score": .9},
    ]))
    hits = await retrieval.search_option_evidence([1], "Selling a memory card", "")
    assert hits[0]["match_type"] == "semantic"


@pytest.mark.asyncio
async def test_option_profiles_must_be_active_and_leaf(monkeypatch):
    client = SimpleNamespace(retrieve=AsyncMock(return_value=[
        SimpleNamespace(payload=category(98)),
        SimpleNamespace(payload={**category(8), "is_active": False}),
        SimpleNamespace(payload={**category(1), "is_leaf": False}),
    ]))
    monkeypatch.setattr(qdrant_service, "get_client", lambda: client)
    assert [c["category_id"] for c in await qdrant_service.get_category_profiles([98, 8, 1])] == [98]


@pytest.mark.asyncio
@pytest.mark.parametrize("fast", [False, True])
async def test_classifier_reranks_all_merged_candidates(monkeypatch, fast):
    candidates = [category(cid) for cid in range(35)]
    understand = AsyncMock(return_value={"product_type": "thẻ nhớ", "normalized_product_text": "thẻ nhớ", "confidence": .9})
    monkeypatch.setattr(llm_service, "understand_product", understand)
    monkeypatch.setattr(classifier.embedder, "embed_single", AsyncMock(return_value=[1]))
    monkeypatch.setattr(retrieval, "retrieve_candidates", AsyncMock(return_value=candidates))
    rerank = AsyncMock(return_value={"category_id": 34, "confidence": .9})
    monkeypatch.setattr(llm_service, "rerank_categories", rerank)
    result = await classifier.classify_product("Bán thẻ nhớ", fast=fast)
    assert rerank.await_args.kwargs["candidates"] == candidates
    assert result["selected_category"]["category_id"] == 34
    if fast:
        understand.assert_not_awaited()


@pytest.mark.asyncio
async def test_rerank_rejects_invented_category_and_exposes_option_evidence(monkeypatch):
    chat = AsyncMock(return_value='{"category_id":999,"confidence":1,"alternatives":[{"category_id":98,"confidence":0.8},{"category_id":777,"confidence":0.5}]}')
    monkeypatch.setattr(llm_service, "_chat", chat)
    candidates = [{**category(98), "matched_options": [{"option_value": "Thẻ Nhớ", "parent_field_value": "Phụ kiện điện thoại"}]}]
    result = await llm_service.rerank_categories("Thẻ nhớ", .8, "text_only", candidates)
    assert result["category_id"] is None and result["confidence"] == 0
    assert result["alternatives"] == [{"category_id": 98, "confidence": .8}]
    assert "Phụ kiện điện thoại" in chat.await_args.args[1]
