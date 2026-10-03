"""Cache reuse must preserve evidence, versions, isolation and failure recovery."""
import asyncio
import json
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import create_engine, text

from config import settings
from database import SessionLocal
from models import Category, CategoryField, SystemConfig
from services import (result_cache, classifier, llm_service, embedder,
                      candidate_retrieval, attribute_selector, qdrant_service)
from routers import generate


@pytest.fixture
def cached(monkeypatch):
    monkeypatch.setattr(settings, "cache_enabled", True)
    revision = ["taxonomy-1"]
    async def version():
        return revision[0]
    for module in (result_cache, classifier, llm_service, candidate_retrieval, attribute_selector):
        monkeypatch.setattr(module, "taxonomy_version", version)
    return revision


@pytest.mark.asyncio
async def test_coalesces_identical_concurrent_requests_and_returns_copies(cached):
    cache = result_cache.ResultCache()
    started, release = asyncio.Event(), asyncio.Event()
    calls = 0
    async def producer():
        nonlocal calls
        calls += 1
        started.set()
        await release.wait()
        return {"nested": [1]}
    first = asyncio.create_task(cache.get_or_compute("test", "same", 10, producer))
    await started.wait()
    others = [asyncio.create_task(cache.get_or_compute("test", "same", 10, producer)) for _ in range(8)]
    await asyncio.sleep(0)
    release.set()
    values = await asyncio.gather(first, *others)
    values[0]["nested"].append(99)
    assert calls == 1
    assert all(value == {"nested": [1]} for value in values[1:])
    assert await cache.get_or_compute("test", "same", 10, producer) == {"nested": [1]}


@pytest.mark.asyncio
async def test_disconnect_does_not_cancel_other_waiters(cached):
    cache = result_cache.ResultCache()
    started, release = asyncio.Event(), asyncio.Event()
    async def producer():
        started.set()
        await release.wait()
        return {"ok": True}
    first = asyncio.create_task(cache.get_or_compute("test", 1, 10, producer))
    await started.wait()
    second = asyncio.create_task(cache.get_or_compute("test", 1, 10, producer))
    await asyncio.sleep(0)
    first.cancel()
    with pytest.raises(asyncio.CancelledError):
        await first
    release.set()
    assert await second == {"ok": True}


@pytest.mark.asyncio
async def test_expiration_and_bounded_memory(cached, monkeypatch):
    clock = [0.0]
    monkeypatch.setattr(result_cache.time, "monotonic", lambda: clock[0])
    cache = result_cache.ResultCache(max_entries=1, max_bytes=32)
    producer = AsyncMock(return_value={"ok": 1})
    await cache.get_or_compute("test", 1, 10, producer)
    await cache.get_or_compute("test", 1, 10, producer)
    assert producer.await_count == 1
    clock[0] = 11
    await cache.get_or_compute("test", 1, 10, producer)
    assert producer.await_count == 2
    await cache.get_or_compute("test", 2, 10, producer)
    assert len(cache._memory) == 1 and cache._bytes <= 32
    await cache.get_or_compute("test", 3, 10, AsyncMock(return_value="x" * 100))
    assert len(cache._memory) == 1 and cache._bytes <= 32


@pytest.mark.asyncio
async def test_failures_and_rejected_results_are_not_cached(cached):
    cache = result_cache.ResultCache()
    producer = AsyncMock(side_effect=[RuntimeError("upstream failed"), {}, {"ok": True}])
    with pytest.raises(RuntimeError):
        await cache.get_or_compute("test", 1, 10, producer, cacheable=bool)
    assert await cache.get_or_compute("test", 1, 10, producer, cacheable=bool) == {}
    assert await cache.get_or_compute("test", 1, 10, producer, cacheable=bool) == {"ok": True}
    assert producer.await_count == 3


@pytest.mark.asyncio
async def test_graceful_partial_fallback_is_not_cached_by_outer_pipeline(cached):
    cache = result_cache.ResultCache()
    calls = 0
    async def inner():
        result_cache.mark_uncacheable()
        return {"explicit_values_only": True}
    async def outer():
        nonlocal calls
        calls += 1
        return await cache.get_or_compute("inner", 1, 10, inner)
    for _ in range(2):
        assert await cache.get_or_compute("outer", 1, 10, outer) == {"explicit_values_only": True}
    assert calls == 2


@pytest.mark.asyncio
async def test_shared_failed_child_prevents_caching_each_waiting_parent(cached):
    cache = result_cache.ResultCache()
    calls = {1: 0, 2: 0}
    async def inner():
        await asyncio.sleep(0.001)
        result_cache.mark_uncacheable()
        return {"partial": True}
    async def run(key):
        async def outer():
            calls[key] += 1
            return await cache.get_or_compute("child", 1, 10, inner)
        return await cache.get_or_compute("parent", key, 10, outer)
    await asyncio.gather(run(1), run(2))
    await asyncio.gather(run(1), run(2))
    assert calls == {1: 2, 2: 2}


@pytest.mark.asyncio
@pytest.mark.parametrize("quick", [False, True])
async def test_attribute_llm_failure_recovers_instead_of_caching_partial_values(cached, monkeypatch, quick):
    fields = [
        {"id": 1, "field_key": "device", "field_label": "Thiết bị", "field_type": "select",
         "field_options": [{"value": "Thẻ Nhớ"}]},
        {"id": 2, "field_key": "condition", "field_label": "Tình trạng", "field_type": "select",
         "field_options": [{"value": "Đã sử dụng"}]},
    ]
    chat = AsyncMock(side_effect=[RuntimeError("temporary upstream failure"), '{"f0":"Đã sử dụng"}'])
    monkeypatch.setattr(llm_service, "_chat", chat)
    async def run():
        if quick:
            return await attribute_selector.select_attributes(fields, "Bán thẻ nhớ", "", {})
        return await llm_service.suggest_field_values("Bán thẻ nhớ", "", fields)
    first = await run()
    second = await run()
    assert first == {"device": "Thẻ Nhớ"}
    assert second == {"device": "Thẻ Nhớ", "condition": "Đã sử dụng"}
    assert chat.await_count == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("quick", [False, True])
async def test_valid_unknown_attributes_are_cached(cached, monkeypatch, quick):
    fields = [{"id": 1, "field_key": "brand", "field_label": "Thương hiệu", "field_type": "select",
               "field_options": [{"value": "Apple"}]}]
    chat = AsyncMock(return_value='{"f0":null}')
    monkeypatch.setattr(llm_service, "_chat", chat)
    for _ in range(2):
        if quick:
            result = await attribute_selector.select_attributes(fields, "Bán thẻ nhớ", "", {})
        else:
            result = await llm_service.suggest_field_values("Bán thẻ nhớ", "", fields)
        assert result == {}
    chat.assert_awaited_once()


class FakeRedis:
    def __init__(self):
        self.data = {}
    async def set(self, key, value, ex):
        self.data[key] = (value, result_cache.time.monotonic() + ex)
    def pipeline(self, transaction=False):
        redis = self
        class Pipe:
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass
            def get(self, key):
                self.key = key
                return self
            def pttl(self, key):
                return self
            async def execute(self):
                payload, deadline = redis.data.get(self.key, (None, 0))
                return payload, int((deadline - result_cache.time.monotonic()) * 1000)
        return Pipe()


@pytest.mark.asyncio
async def test_shared_results_preserve_remaining_ttl_and_hide_input_in_keys(cached, monkeypatch):
    clock = [0.0]
    monkeypatch.setattr(result_cache.time, "monotonic", lambda: clock[0])
    redis = FakeRedis()
    first, second = result_cache.ResultCache(), result_cache.ResultCache()
    first.redis = second.redis = redis
    producer = AsyncMock(return_value={"category_id": 98})
    identity = "Bán thẻ nhớ, không rõ thương hiệu"
    await first.get_or_compute("test", identity, 10, producer)
    clock[0] = 8
    assert await second.get_or_compute("test", identity, 10, producer) == {"category_id": 98}
    assert producer.await_count == 1
    assert all(identity not in key for key in redis.data)
    clock[0] = 11
    await second.get_or_compute("test", identity, 10, producer)
    assert producer.await_count == 2  # Shared hit must not reset TTL to 10s.


@pytest.mark.asyncio
async def test_redis_outage_falls_back_to_memory(cached):
    cache = result_cache.ResultCache()
    cache.redis = FakeRedis()
    cache.redis.pipeline = lambda **kwargs: (_ for _ in ()).throw(ConnectionError())
    cache.redis.set = AsyncMock(side_effect=ConnectionError())
    producer = AsyncMock(return_value={"ok": True})
    assert await cache.get_or_compute("test", 1, 10, producer) == {"ok": True}
    assert await cache.get_or_compute("test", 1, 10, producer) == {"ok": True}
    producer.assert_awaited_once()


@pytest.mark.asyncio
async def test_embedding_reuse_and_model_change(cached, monkeypatch):
    encode = AsyncMock(return_value=[[1.0, 2.0]])
    monkeypatch.setattr(embedder, "embed_texts", encode)
    first = await embedder.embed_single("Thẻ nhớ")
    first[0] = 9
    assert await embedder.embed_single("Thẻ nhớ") == [1.0, 2.0]
    encode.assert_awaited_once()
    monkeypatch.setenv("EMBEDDING_MODEL", "other-model")
    await embedder.embed_single("Thẻ nhớ")
    assert encode.await_count == 2


@pytest.mark.asyncio
async def test_understanding_cache_invalidates_on_prompt_model_and_taxonomy(cached, monkeypatch):
    value = {"normalized_product_text": "thẻ nhớ", "product_type": "thẻ nhớ", "confidence": .9}
    chat = AsyncMock(return_value=json.dumps(value))
    monkeypatch.setattr(llm_service, "_chat", chat)
    await llm_service.understand_product("Bán thẻ nhớ")
    await llm_service.understand_product("Bán thẻ nhớ")
    assert chat.await_count == 1
    cached[0] = "taxonomy-2"
    await llm_service.understand_product("Bán thẻ nhớ")
    monkeypatch.setattr(llm_service, "SYSTEM_UNDERSTAND", "new prompt")
    await llm_service.understand_product("Bán thẻ nhớ")
    monkeypatch.setitem(llm_service.runtime_config._data, "llm.deepseek_model", "other-model")
    await llm_service.understand_product("Bán thẻ nhớ")
    assert chat.await_count == 4


@pytest.mark.asyncio
async def test_understanding_fallback_and_image_urls_are_not_cached(cached, monkeypatch):
    chat = AsyncMock(return_value="invalid JSON")
    monkeypatch.setattr(llm_service, "_chat", chat)
    await llm_service.understand_product("Bán thẻ nhớ")
    await llm_service.understand_product("Bán thẻ nhớ")
    assert chat.await_count == 2
    chat.return_value = '{"product_type":"thẻ nhớ","normalized_product_text":"thẻ nhớ"}'
    for _ in range(2):
        await llm_service.understand_product("Bán thẻ nhớ", image_urls=["https://example.test/photo.jpg"])
    assert chat.await_count == 4


@pytest.mark.asyncio
async def test_classification_cache_respects_facts_mode_and_revision(cached, monkeypatch):
    compute = AsyncMock(return_value={"selected_category": {"category_id": 98}, "rerank": {"category_id": 98}})
    monkeypatch.setattr(classifier, "_classify_product_uncached", compute)
    await classifier.classify_product("Bán thẻ nhớ")
    await classifier.classify_product("Bán thẻ nhớ")
    assert compute.await_count == 1
    await classifier.classify_product("Bán thẻ nhớ", description="không kèm thẻ nhớ")
    await classifier.classify_product("Bán thẻ nhớ", price=100000)
    await classifier.classify_product("Bán thẻ nhớ", fast=True)
    cached[0] = "taxonomy-2"
    await classifier.classify_product("Bán thẻ nhớ")
    assert compute.await_count == 5
    for _ in range(2):
        await classifier.classify_product("Bán thẻ nhớ", image_urls=["https://example.test/photo.jpg"])
    assert compute.await_count == 7


@pytest.mark.asyncio
async def test_failed_taxonomy_read_bypasses_classification_cache(cached, monkeypatch):
    cached[0] = None
    compute = AsyncMock(return_value={"selected_category": {"category_id": 98}, "rerank": {"category_id": 98}})
    monkeypatch.setattr(classifier, "_classify_product_uncached", compute)
    for _ in range(2):
        await classifier.classify_product("Bán thẻ nhớ")
    assert compute.await_count == 2


@pytest.mark.asyncio
async def test_empty_index_result_is_not_cached(cached, monkeypatch):
    compute = AsyncMock(return_value={"selected_category": None, "rerank": None})
    monkeypatch.setattr(classifier, "_classify_product_uncached", compute)
    await classifier.classify_product("Bán thẻ nhớ")
    compute.return_value = {"selected_category": {"category_id": 98}, "rerank": {"category_id": 98}}
    await classifier.classify_product("Bán thẻ nhớ")
    assert compute.await_count == 2


@pytest.mark.asyncio
async def test_catalog_reuse_still_matches_each_requests_evidence(cached, monkeypatch):
    field = {"id": 311, "category_id": 98, "field_key": "device", "field_label": "Thiết bị",
             "field_type": "select", "field_options": [{"value": "Thẻ Nhớ", "label": "Thẻ Nhớ"}]}
    calls = []
    def load():
        calls.append(1)
        return [field]
    monkeypatch.setattr(candidate_retrieval, "_load_option_catalog", load)
    monkeypatch.setattr(qdrant_service, "search_options_global", AsyncMock(return_value=[]))
    assert await candidate_retrieval.search_option_evidence([1], "Bán thẻ nhớ", "")
    assert not await candidate_retrieval.search_option_evidence([1], "Bán máy ảnh không kèm thẻ nhớ", "")
    assert len(calls) == 1
    assert "_normalized_names" not in field["field_options"][0]
    cached[0] = "taxonomy-2"
    assert await candidate_retrieval.search_option_evidence([1], "Bán thẻ nhớ", "")
    assert len(calls) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("quick", [False, True])
async def test_attribute_results_invalidate_when_field_definitions_change(cached, monkeypatch, quick):
    process = AsyncMock(return_value={"device": "Thẻ Nhớ"})
    monkeypatch.setattr(llm_service.attribute_rules, "select_with_dependencies", process)
    fields = [{"id": 311, "field_key": "device", "field_options": [{"value": "Thẻ Nhớ"}]}]
    async def run():
        if quick:
            return await attribute_selector.select_attributes(fields, "Bán thẻ nhớ", "", {})
        return await llm_service.suggest_field_values("Bán thẻ nhớ", "", fields)
    await run()
    await run()
    assert process.await_count == 1
    fields[0]["parent_field_value"] = "new parent option"
    await run()
    assert process.await_count == 2


@pytest.mark.asyncio
async def test_from_text_uses_classifiers_understanding_without_duplicate_call(monkeypatch):
    understand = AsyncMock()
    monkeypatch.setattr(generate, "understand_product", understand)
    classify = AsyncMock(return_value={
        "selected_category": {"category_id": 98},
        "understanding": {"suggested_title": "Thẻ nhớ", "suggested_description": "Thông tin gốc"},
    })
    monkeypatch.setattr(generate.classifier, "classify_product", classify)
    monkeypatch.setattr(generate, "get_attributes_for_category", lambda *args: [])
    response = await generate.generate_from_text(generate.GenerateFromTextRequest(title="Bán thẻ nhớ"), object())
    assert response["suggested"]["title"] == "Thẻ nhớ"
    assert classify.await_args.kwargs["title"] == "Bán thẻ nhớ"
    understand.assert_not_awaited()


@pytest.mark.asyncio
async def test_classifier_reuses_understanding_from_stream(monkeypatch):
    understanding = {"product_type": "thẻ nhớ", "normalized_product_text": "thẻ nhớ", "confidence": .9}
    understand = AsyncMock()
    monkeypatch.setattr(llm_service, "understand_product", understand)
    monkeypatch.setattr(embedder, "embed_single", AsyncMock(return_value=[1]))
    monkeypatch.setattr(candidate_retrieval, "retrieve_candidates", AsyncMock(return_value=[{"category_id": 98}]))
    monkeypatch.setattr(llm_service, "rerank_categories", AsyncMock(return_value={"category_id": 98, "confidence": .9}))
    result = await classifier.classify_product("Bán thẻ nhớ", understanding=understanding)
    assert result["selected_category"]["category_id"] == 98
    understand.assert_not_awaited()


@pytest.fixture
def taxonomy_db():
    engine = create_engine("sqlite://")
    for model in (Category, CategoryField, SystemConfig):
        model.__table__.create(engine)
    with SessionLocal(bind=engine) as db:
        yield db
    engine.dispose()


def revision(db):
    return db.execute(text("SELECT value FROM system_config WHERE key='cache.taxonomy_version'")).scalar()


def test_committed_orm_and_bulk_taxonomy_writes_publish_revision(taxonomy_db):
    db = taxonomy_db
    db.add(Category(id=98, name="Phụ kiện"))
    db.commit()
    first = revision(db)
    assert first
    db.query(Category).filter_by(id=98).update({"name": "Phụ kiện điện thoại"})
    db.commit()
    second = revision(db)
    assert second != first
    db.add(CategoryField(category_id=98, field_key="device", field_label="Thiết bị", field_type="select"))
    db.commit()
    third = revision(db)
    assert third != second
    db.query(CategoryField).delete()
    db.commit()
    assert revision(db) != third


def test_rollback_and_unrelated_writes_do_not_invalidate(taxonomy_db):
    db = taxonomy_db
    db.add(Category(id=98, name="Phụ kiện"))
    db.commit()
    before = revision(db)
    db.query(Category).update({"name": "temporary"})
    db.rollback()
    db.add(SystemConfig(key="unrelated", value="1"))
    db.commit()
    assert revision(db) == before
    assert db.get(Category, 98).name == "Phụ kiện"


@pytest.mark.asyncio
async def test_partial_index_failure_still_invalidates(monkeypatch):
    invalidate = AsyncMock()
    monkeypatch.setattr(qdrant_service, "invalidate_taxonomy", invalidate)
    with pytest.raises(RuntimeError):
        async with qdrant_service._index_change():
            raise RuntimeError("partial write")
    assert invalidate.await_count == 2
