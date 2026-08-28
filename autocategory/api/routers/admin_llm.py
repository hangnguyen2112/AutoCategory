"""DeepSeek-only runtime configuration for administrators."""
from __future__ import annotations

import time
import logging
from typing import Literal

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import settings
from dependencies import CurrentAdminUser
from runtime_config import runtime_config
from database import SessionLocal

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/llm", tags=["Admin - LLM Provider"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class LLMConfig(BaseModel):
    provider: str
    deepseek_api_key_configured: bool
    deepseek_api_key_hint: str | None
    deepseek_model: str
    active_base_url: str
    active_model: str


class SwitchProviderRequest(BaseModel):
    provider: Literal["deepseek"]
    deepseek_api_key: str | None = None
    deepseek_model: str | None = None


class TestResult(BaseModel):
    provider: str
    base_url: str
    model: str
    success: bool
    latency_ms: float | None = None
    response_preview: str | None = None
    error: str | None = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/config", response_model=LLMConfig, summary="Xem cấu hình LLM hiện tại")
async def get_llm_config(current_admin: CurrentAdminUser):
    """Trả về cấu hình LLM hiện tại (đọc từ runtime_config - nguồn là DB)."""
    rc = runtime_config
    key = rc.deepseek_api_key

    return LLMConfig(
        provider="deepseek",
        deepseek_api_key_configured=bool(key),
        deepseek_api_key_hint=f"••••{key[-4:]}" if key else None,
        deepseek_model=rc.deepseek_model,
        active_base_url=settings.deepseek_proxy_url,
        active_model=rc.deepseek_model,
    )


@router.post("/switch", response_model=LLMConfig, summary="Chuyển provider (runtime, không cần restart)")
async def switch_provider(req: SwitchProviderRequest, current_admin: CurrentAdminUser):
    """Persist and apply DeepSeek credentials/model without a restart."""
    rc = runtime_config
    api_key = req.deepseek_api_key.strip() if req.deepseek_api_key is not None else rc.deepseek_api_key
    model = req.deepseek_model.strip() if req.deepseek_model is not None else rc.deepseek_model
    if not api_key:
        raise HTTPException(status_code=422, detail="DeepSeek API key không được để trống")
    if not model:
        raise HTTPException(status_code=422, detail="DeepSeek model không được để trống")

    # Persist first, then release the DB connection before network I/O.
    with SessionLocal() as db:
        rc.set_provider(req.provider, db, current_admin.id)
        rc.set_deepseek_config(api_key, model, db, current_admin.id)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{settings.deepseek_proxy_url}/configure",
                json={"api_key": api_key, "model": model},
            )
            response.raise_for_status()
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Đã lưu DB nhưng không cập nhật được DeepSeek proxy: {exc}",
        ) from exc

    logger.info(
        "LLM provider switched to '%s' by admin user_id=%s",
        req.provider, current_admin.id,
    )

    return await get_llm_config(current_admin)


@router.post("/test", response_model=TestResult, summary="Test kết nối LLM provider")
async def test_llm_provider(current_admin: CurrentAdminUser):
    """Send a small DeepSeek request and report latency."""
    base_url = settings.deepseek_proxy_url
    model = runtime_config.deepseek_model
    payload: dict = {
        "model": model,
        "messages": [{"role": "user", "content": "What is your exact model version? Reply in one short sentence."}],
        "max_tokens": 60,
        "temperature": 0.0,
        "thinking": {"type": "disabled"},
    }

    start = time.monotonic()
    try:
        async with httpx.AsyncClient(base_url=base_url, timeout=15.0) as client:
            resp = await client.post("/v1/chat/completions", json=payload)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            latency_ms = round((time.monotonic() - start) * 1000, 1)
            return TestResult(
                provider="deepseek",
                base_url="https://api.deepseek.com",
                model=model,
                success=True,
                latency_ms=latency_ms,
                response_preview=content[:200],
            )
    except Exception as exc:
        latency_ms = round((time.monotonic() - start) * 1000, 1)
        return TestResult(
            provider="deepseek",
            base_url="https://api.deepseek.com",
            model=model,
            success=False,
            latency_ms=latency_ms,
            error=str(exc),
        )


@router.get("/models", summary="Lấy danh sách models từ provider hiện tại")
async def list_models(current_admin: CurrentAdminUser):
    """Return models exposed by the DeepSeek proxy."""
    try:
        async with httpx.AsyncClient(base_url=settings.deepseek_proxy_url, timeout=10.0) as client:
            resp = await client.get("/v1/models")
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Không thể lấy danh sách model DeepSeek: {exc}")
