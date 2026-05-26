"""
Admin LLM Provider Management
- Xem cấu hình hiện tại (llama.cpp hoặc LM Studio)
- Chuyển đổi provider trong runtime
- Test kết nối đến provider
"""
from __future__ import annotations

import time
import logging
from typing import Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from config import settings
from dependencies import CurrentAdminUser
from runtime_config import runtime_config
from services.llm_service import _clients
from database import SessionLocal

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/llm", tags=["Admin - LLM Provider"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class LLMConfig(BaseModel):
    provider: str
    llama_base_url: str
    llama_model: str
    lm_studio_base_url: str
    lm_studio_model: str
    gemini_web_secure_1psid: str
    gemini_web_secure_1psidts: str
    active_base_url: str
    active_model: str


class SwitchProviderRequest(BaseModel):
    provider: Literal["llama", "lm_studio", "gemini_web"]
    lm_studio_base_url: str | None = None
    lm_studio_model: str | None = None
    gemini_web_secure_1psid: str | None = None
    gemini_web_secure_1psidts: str | None = None


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
    if rc.llm_provider == "lm_studio":
        active_url = rc.lm_studio_base_url
        active_model = rc.lm_studio_model
    elif rc.llm_provider == "gemini_web":
        active_url = "https://gemini.google.com"
        active_model = "gemini-web"
    else:
        active_url = rc.llama_base_url
        active_model = rc.llama_model

    return LLMConfig(
        provider=rc.llm_provider,
        llama_base_url=rc.llama_base_url,
        llama_model=rc.llama_model,
        lm_studio_base_url=rc.lm_studio_base_url,
        lm_studio_model=rc.lm_studio_model,
        gemini_web_secure_1psid=rc.gemini_web_secure_1psid,
        gemini_web_secure_1psidts=rc.gemini_web_secure_1psidts,
        active_base_url=active_url,
        active_model=active_model,
    )


@router.post("/switch", response_model=LLMConfig, summary="Chuyển provider (runtime, không cần restart)")
async def switch_provider(req: SwitchProviderRequest, current_admin: CurrentAdminUser):
    """
    Chuyển đổi LLM provider ngay lập tức trong runtime.

    - `provider: "llama"` → dùng llama.cpp server (docker service)
    - `provider: "lm_studio"` → dùng LM Studio trên host machine

    Thay đổi có hiệu lực ngay cho tất cả requests tiếp theo.
    **Được lưu vào database** nên tồn tại qua restart container.
    """
    rc = runtime_config
    db = SessionLocal()
    try:
        rc.set_provider(req.provider, db, current_admin.id)

        if req.lm_studio_base_url:
            # Evict cached client for OLD url before overwriting
            _clients.pop(rc.lm_studio_base_url, None)
            rc.set_lm_studio_base_url(req.lm_studio_base_url, db, current_admin.id)

        if req.lm_studio_model:
            rc.set_lm_studio_model(req.lm_studio_model, db, current_admin.id)

        if req.gemini_web_secure_1psid is not None or req.gemini_web_secure_1psidts is not None:
            psid = req.gemini_web_secure_1psid or rc.gemini_web_secure_1psid
            psidts = req.gemini_web_secure_1psidts or rc.gemini_web_secure_1psidts
            rc.set_gemini_web_cookies(psid, psidts, db, current_admin.id)
            # Push new cookies to gemini-proxy container immediately
            from services.gemini_web_service import configure as _configure_proxy
            await _configure_proxy(psid, psidts or "")

    finally:
        db.close()

    logger.info(
        "LLM provider switched to '%s' by admin user_id=%s",
        req.provider, current_admin.id,
    )

    return await get_llm_config(current_admin)


@router.post("/test", response_model=TestResult, summary="Test kết nối LLM provider")
async def test_llm_provider(current_admin: CurrentAdminUser):
    """
    Gửi một request đơn giản đến provider hiện tại để kiểm tra kết nối và tốc độ.
    Gemini Web: gửi prompt đơn giản, kiểm tra cookie có hợp lệ không.
    """
    if runtime_config.llm_provider == "gemini_web":
        start = time.monotonic()
        try:
            from services.gemini_web_service import chat as _gemini_chat
            text = await _gemini_chat("Reply with one word: OK")
            latency_ms = round((time.monotonic() - start) * 1000, 1)
            return TestResult(
                provider="gemini_web",
                base_url="https://gemini.google.com",
                model="gemini-web",
                success=True,
                latency_ms=latency_ms,
                response_preview=text[:200],
            )
        except Exception as exc:
            latency_ms = round((time.monotonic() - start) * 1000, 1)
            return TestResult(
                provider="gemini_web",
                base_url="https://gemini.google.com",
                model="gemini-web",
                success=False,
                latency_ms=latency_ms,
                error=str(exc),
            )

    if runtime_config.llm_provider == "lm_studio":
        base_url = runtime_config.lm_studio_base_url
        model = runtime_config.lm_studio_model
        payload: dict = {
            "model": model,
            "messages": [{"role": "user", "content": "Reply with one word: OK"}],
            "max_tokens": 10,
            "temperature": 0.0,
            "thinking": {"type": "disabled"},
        }
    else:
        base_url = runtime_config.llama_base_url
        model = runtime_config.llama_model
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "Reply with one word: OK"}],
            "max_tokens": 10,
            "temperature": 0.0,
            "chat_template_kwargs": {"thinking": False},
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
                provider=runtime_config.llm_provider,
                base_url=base_url,
                model=model,
                success=True,
                latency_ms=latency_ms,
                response_preview=content[:200],
            )
    except Exception as exc:
        latency_ms = round((time.monotonic() - start) * 1000, 1)
        return TestResult(
            provider=runtime_config.llm_provider,
            base_url=base_url,
            model=model,
            success=False,
            latency_ms=latency_ms,
            error=str(exc),
        )


@router.get("/models", summary="Lấy danh sách models từ provider hiện tại")
async def list_models(current_admin: CurrentAdminUser):
    """
    Gọi GET /v1/models từ provider hiện tại.
    LM Studio trả về danh sách models đã load.
    """
    if runtime_config.llm_provider == "lm_studio":
        base_url = runtime_config.lm_studio_base_url
    else:
        base_url = runtime_config.llama_base_url

    try:
        async with httpx.AsyncClient(base_url=base_url, timeout=10.0) as client:
            resp = await client.get("/v1/models")
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Không thể kết nối provider: {exc}")
