"""
Gemini Web Service — HTTP client gọi container gemini-proxy.

Container `gemini-proxy` chạy song song, import gemini-webapi trong môi trường riêng
để tránh xung đột dependency với main api container.

Các function này giữ nguyên interface cũ nên llm_service.py và admin_llm.py
không cần refactor nhiều.
"""
from __future__ import annotations

import logging
import os

import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)

PROXY_URL = os.getenv("GEMINI_PROXY_URL", "http://gemini-proxy:8001")


# ── Cookie push ───────────────────────────────────────────────────────────────

async def _push_cookies_from_runtime() -> None:
    """Đọc cookie từ DB (runtime_config) và đẩy sang proxy."""
    from runtime_config import runtime_config

    psid = runtime_config.gemini_web_secure_1psid
    psidts = runtime_config.gemini_web_secure_1psidts
    if not psid:
        raise RuntimeError(
            "Gemini Web cookie chưa được cấu hình. "
            "Vào Admin > System Control > LLM Provider để nhập __Secure-1PSID."
        )
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"{PROXY_URL}/configure",
            json={"secure_1psid": psid, "secure_1psidts": psidts or ""},
        )
        resp.raise_for_status()
    logger.info("Pushed Gemini cookies to proxy")


async def configure(secure_1psid: str, secure_1psidts: str = "") -> None:
    """Đẩy cookie mới sang proxy — gọi khi admin lưu cookie mới."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"{PROXY_URL}/configure",
            json={"secure_1psid": secure_1psid, "secure_1psidts": secure_1psidts},
        )
        resp.raise_for_status()
    logger.info("Gemini proxy cookie updated")


async def reset_client() -> None:
    """Reset proxy client (giữ cookie). Backward-compat."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(f"{PROXY_URL}/reset")
    except Exception as exc:
        logger.warning("Could not reset gemini proxy: %s", exc)


# ── Core chat ──────────────────────────────────────────────────────────────────

async def chat(prompt: str, image_urls: list[str] | None = None, model: str | None = None) -> str:
    """
    Gửi prompt (và ảnh nếu có) đến gemini-proxy container.
    image_urls: http/https URL hoặc data: base64 URL.
    model: tên Gemini model (để trống = dùng default proxy).
    Ảnh được decode/download rồi gửi dưới dạng binary multipart.
    Trả về text response.
    """
    import base64

    # Build danh sách (filename, bytes, mimetype) từ image_urls
    file_tuples: list[tuple[str, bytes, str]] = []
    for url in (image_urls or []):
        try:
            if url.startswith("data:"):
                header, b64data = url.split(",", 1)
                mime = header.split(";")[0].split(":")[1]  # image/jpeg
                ext = mime.split("/")[1].replace("jpeg", "jpg")
                raw = base64.b64decode(b64data)
                file_tuples.append((f"image.{ext}", raw, mime))
            elif url.startswith(("http://", "https://")):
                async with httpx.AsyncClient(timeout=30, follow_redirects=True) as dl:
                    r = await dl.get(url)
                    r.raise_for_status()
                    ct = r.headers.get("content-type", "image/jpeg").split(";")[0]
                    ext = ct.split("/")[1].replace("jpeg", "jpg")
                    file_tuples.append((f"image.{ext}", r.content, ct))
        except Exception as exc:
            logger.warning("Bỏ qua ảnh (không đọc được): %s", exc)

    # Multipart form-data: always pass files= (even if empty) so httpx sends
    # multipart/form-data instead of application/x-www-form-urlencoded.
    # FastAPI endpoints that mix Form + File params require multipart.
    multipart_files = [("files", (name, raw, mime)) for name, raw, mime in file_tuples]
    form_data: dict = {"prompt": prompt}
    if model:
        form_data["model"] = model

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{PROXY_URL}/chat",
            data=form_data,
            files=multipart_files,
        )

        if resp.status_code == 503:
            logger.info("Proxy unconfigured, pushing cookies and retrying...")
            await _push_cookies_from_runtime()
            resp = await client.post(
                f"{PROXY_URL}/chat",
                data=form_data,
                files=multipart_files,
            )

        if not resp.is_success:
            detail = resp.json().get("detail", resp.text) if resp.headers.get("content-type", "").startswith("application/json") else resp.text
            raise HTTPException(status_code=resp.status_code, detail=detail)

        return resp.json()["text"]
