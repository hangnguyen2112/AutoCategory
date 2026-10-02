"""Ensure SSE responses include the field definitions needed by the form."""

import json
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from routers import generate


@pytest.mark.asyncio
@pytest.mark.parametrize("full", [False, True])
@pytest.mark.parametrize("has_fields", [False, True])
async def test_stream_returns_attributes_and_selected_values(monkeypatch, full, has_fields):
    attributes = [{
        "id": 1,
        "field_key": "brand",
        "field_label": "Thương hiệu",
        "field_type": "select",
        "field_options": ["Apple", "Samsung"],
        "is_required": True,
    }] if has_fields else []
    selected_values = {"brand": "Apple"} if has_fields else {}
    monkeypatch.setattr(generate, "understand_product", AsyncMock(return_value={}))
    monkeypatch.setattr(generate.classifier, "classify_product", AsyncMock(return_value={
        "selected_category": {"category_id": 2, "name": "Điện thoại"},
    }))
    monkeypatch.setattr(generate, "_load_attributes", lambda category_id: attributes)
    monkeypatch.setattr(generate, "suggest_field_values", AsyncMock(return_value=selected_values))
    monkeypatch.setattr(generate.attribute_selector, "select_attributes", AsyncMock(return_value=selected_values))

    app = FastAPI()
    app.include_router(generate.router, prefix="/api")
    app.dependency_overrides[generate.require_api_key] = lambda: object()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/generate/stream", json={"title": "iPhone", "full": full})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
    assert not any(event["step"] == "error" for event in events)
    fields_event = next(event for event in events if event["step"] == "attributes")
    assert "attributes" not in fields_event
    assert fields_event["selected_values"] == selected_values
    assert events[-1]["step"] == "done"

