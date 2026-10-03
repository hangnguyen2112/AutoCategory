"""Regression tests for option selection without positional truncation."""

from unittest.mock import AsyncMock

import pytest

from services import llm_service


def _option(value: str, **extra) -> dict:
    return {"value": value, "label": value, **extra}


@pytest.mark.asyncio
async def test_explicit_brand_is_selected_even_after_old_cutoff(monkeypatch):
    options = [_option(f"Brand {index}") for index in range(21)]
    options += [_option("Honor")]
    options += [_option(f"Brand {index}") for index in range(22, 73)]
    chat = AsyncMock(return_value="{}")
    monkeypatch.setattr(llm_service, "_chat", chat)

    result = await llm_service.suggest_field_values(
        "Honor Win 12GB/256GB",
        "",
        [{
            "field_key": "brand",
            "field_label": "Thương hiệu",
            "field_type": "select",
            "parent_field_id": None,
            "field_options": options,
        }],
    )

    assert result["brand"] == "Honor"
    chat.assert_not_awaited()


@pytest.mark.asyncio
async def test_complete_brand_list_is_sent_when_brand_is_not_explicit(monkeypatch):
    options = [_option(f"Brand {index}") for index in range(72)] + [_option("Honor")]
    chat = AsyncMock(return_value='{"brand": "Honor"}')
    monkeypatch.setattr(llm_service, "_chat", chat)

    result = await llm_service.suggest_field_values(
        "Điện thoại cần bán",
        "",
        [{
            "field_key": "brand",
            "field_label": "Thương hiệu",
            "field_type": "select",
            "parent_field_id": None,
            "field_options": options,
        }],
    )

    prompt = chat.await_args.args[1]
    assert "'Brand 71' (Brand 71)" in prompt
    assert "'Honor' (Honor)" in prompt
    assert result["brand"] == "Honor"


@pytest.mark.asyncio
async def test_explicit_model_is_selected_beyond_old_300_option_cutoff(monkeypatch):
    options = [_option(f"Model {index}") for index in range(328)]
    options.append(_option("Redmi Note 11T Pro+"))
    options.append(_option("Redmi Note 14 Pro+"))
    chat = AsyncMock(return_value="{}")
    monkeypatch.setattr(llm_service, "_chat", chat)

    result = await llm_service.suggest_field_values(
        "Xiaomi Redmi Note 14 Pro+ 12GB/256GB",
        "",
        [{
            "id": 1,
            "omni_field_id": 1,
            "field_key": "brand",
            "field_label": "Hãng",
            "field_type": "select",
            "field_options": [_option("Xiaomi")],
        }, {
            "field_key": "dong_may_Xiaomi",
            "field_label": "Dòng máy Xiaomi",
            "field_type": "select",
            "parent_field_id": 1,
            "parent_field_value": "Xiaomi",
            "field_options": options,
        }],
    )

    assert result["dong_may_Xiaomi"] == "Redmi Note 14 Pro+"
    chat.assert_not_awaited()


def test_large_model_list_uses_relevance_instead_of_source_position():
    options = [_option(f"Model {index}") for index in range(330)]
    target = _option("Redmi Note 14 Pro")
    options[325] = target
    field = {"field_options": options}

    selected = llm_service._options_for_prompt(
        field,
        "Xiaomi Redmi Ntoe 14 Pro 12GB/256GB",
        "",
    )

    assert target in selected
    assert len(selected) <= 50


def test_large_model_list_does_not_match_lite_from_elite():
    options = [_option(f"Model {index}") for index in range(150)]
    options += [_option("50 Lite"), _option("90 Lite"), _option("X8")]
    field = {"field_options": options}

    selected = llm_service._options_for_prompt(
        field,
        "Honor Win 12GB/256GB, Snapdragon 8 Elite Gen 5",
        "",
    )

    assert selected == []
