"""Evidence, wire keys, and dependency invariants shared by both modes."""
from unittest.mock import AsyncMock

import pytest

from services import attribute_rules as rules, attribute_selector, llm_service


def field(key, options, *, oid=None, parent=None, required=None):
    return {"id": oid, "omni_field_id": oid, "field_key": key, "field_label": key,
            "field_type": "select", "field_options": [{"value": o, "label": o} for o in options],
            "parent_field_id": parent, "parent_field_value": required}


@pytest.fixture
def accessories():
    return [field("loai_phu_kien", ["Phụ kiện máy tính", "Phụ kiện điện thoại", "Khác"], oid=309),
            field("Nhap_thiet_bi", ["USB", "Giá đỡ"], oid=310, parent=309, required="Phụ kiện máy tính"),
            field("nhap_thiet_bi 2", ["Thẻ Nhớ", "Giá đỡ"], oid=311, parent=309, required="Phụ kiện điện thoại")]


@pytest.mark.asyncio
@pytest.mark.parametrize("full", [False, True])
@pytest.mark.parametrize("title, parent, child", [
    ("mình cần bán thẻ nhớ, không rõ dung lượng và thương hiệu", "Phụ kiện điện thoại", "nhap_thiet_bi 2"),
    ("Bán USB", "Phụ kiện máy tính", "Nhap_thiet_bi"),
])
async def test_explicit_child_resolves_parent_without_llm_or_option_index(monkeypatch, accessories, full, title, parent, child):
    chat = AsyncMock(return_value='{"f0":"Khác"}')
    monkeypatch.setattr(llm_service, "_chat", chat)
    monkeypatch.setattr(attribute_selector, "_ensure_qdrant_ready", AsyncMock(side_effect=RuntimeError("no index")))
    if full:
        result = await llm_service.suggest_field_values(title, "", accessories)
    else:
        result = await attribute_selector.select_attributes(accessories, title, "", {})
    assert result["loai_phu_kien"] == parent
    assert child in result
    assert len(result) == 2
    chat.assert_not_awaited()


def test_explicit_parent_conflict_drops_incompatible_child(accessories):
    result = rules.resolve_explicit_values(accessories, "Phụ kiện máy tính: thẻ nhớ", "")
    assert result == {"loai_phu_kien": "Phụ kiện máy tính"}


@pytest.mark.asyncio
@pytest.mark.parametrize("full", [False, True])
async def test_shared_child_option_waits_for_parent_then_uses_exact_evidence(monkeypatch, accessories, full):
    assert rules.resolve_explicit_values(accessories, "Bán giá đỡ", "") == {}
    chat = AsyncMock(return_value='{"f0": "Phụ kiện điện thoại"}')
    monkeypatch.setattr(llm_service, "_chat", chat)
    if full:
        result = await llm_service.suggest_field_values("Bán giá đỡ", "", accessories)
    else:
        result = await attribute_selector.select_attributes(accessories, "Bán giá đỡ", "", {})
    assert result == {"loai_phu_kien": "Phụ kiện điện thoại", "nhap_thiet_bi 2": "Giá đỡ"}
    assert chat.await_count == 1


def test_label_to_value_mapping_and_three_dependency_levels():
    root = field("type", ["phone"], oid=1)
    root["field_options"][0]["label"] = "Phụ kiện điện thoại"
    middle = field("device", ["Thẻ Nhớ"], oid=2, parent=1, required="Phụ kiện điện thoại")
    leaf = field("model", ["Ultra A1"], oid=3, parent=2, required="Thẻ Nhớ")
    result = rules.resolve_explicit_values([root, middle, leaf], "Bán Ultra A1", "")
    assert result == {"type": "phone", "device": "Thẻ Nhớ", "model": "Ultra A1"}


@pytest.mark.parametrize("text", [
    "Bán máy ảnh không kèm thẻ nhớ", "Bán máy ảnh, không có thẻ nhớ",
    "Máy ảnh kèm thẻ nhớ", "Cần mua thẻ nhớ",
])
def test_negated_or_accompanying_child_does_not_infer_parent(accessories, text):
    assert rules.resolve_explicit_values(accessories, text, "") == {}


def test_positive_clause_after_negation_is_retained(accessories):
    result = rules.resolve_explicit_values(accessories, "Không bán USB nhưng bán thẻ nhớ", "")
    assert result == {"loai_phu_kien": "Phụ kiện điện thoại", "nhap_thiet_bi 2": "Thẻ Nhớ"}


def test_invalid_parent_missing_parent_and_cycles_are_not_emitted():
    root = field("brand", ["Honda"], oid=1)
    invalid = field("ktm_model", ["Duke"], oid=2, parent=1, required="KTM")
    orphan = field("orphan", ["Orphan"], oid=3, parent=99, required="KTM")
    first = field("a", ["A1"], oid=4, parent=5, required="B1")
    second = field("b", ["B1"], oid=5, parent=4, required="A1")
    result = rules.resolve_explicit_values([root, invalid, orphan, first, second], "Duke Orphan A1 B1", "")
    assert result == {}


def test_unknown_fields_invalid_values_and_wrong_branches_are_removed(accessories):
    result = rules.validate_values(accessories, {
        "loai_phu_kien": "Khác", "nhap_thiet_bi 2": "Thẻ Nhớ",
        "Nhap_thiet_bi": "invented", "unknown": "anything",
    })
    assert result == {"loai_phu_kien": "Khác"}


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["extract_attribute_values", "extract_attribute_values_direct", "suggest_field_values"])
async def test_alias_preserves_arbitrary_original_key(monkeypatch, method):
    chat = AsyncMock(return_value='{"f0": "Thẻ Nhớ", "nhap_thiet_bi": "USB", "f99": "invented"}')
    monkeypatch.setattr(llm_service, "_chat", chat)
    fields = [field("nhap_thiet_bi 2", ["Thẻ Nhớ", "USB"])]
    result = await getattr(llm_service, method)("Thiết bị lưu trữ", "", fields)
    assert result == {"nhap_thiet_bi 2": "Thẻ Nhớ"}
    assert "f0" in chat.await_args.args[1]


@pytest.mark.asyncio
async def test_qdrant_ambiguous_or_stale_option_is_not_accepted(monkeypatch):
    f = field("model", ["A1", "B1"], oid=1)
    monkeypatch.setattr(attribute_selector, "embed_single", AsyncMock(return_value=[1.0]))
    search = AsyncMock(return_value=[{"score": .9, "option_value": "A1"}, {"score": .89, "option_value": "B1"}])
    monkeypatch.setattr(attribute_selector.qdrant_service, "search_attribute_options", search)
    assert await attribute_selector._match_via_qdrant([f], {"model": "almost A1"}) == {}
    search.return_value = [{"score": .99, "option_value": "removed model"}]
    assert await attribute_selector._match_via_qdrant([f], {"model": "almost A1"}) == {}
