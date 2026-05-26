"""
Gemini Web Proxy — FastAPI microservice wrapping gemini-webapi v2.x

Chạy trong container riêng biệt. Container `api` gọi HTTP đến đây thay vì
import trực tiếp gemini-webapi (tránh xung đột dependency).

Endpoints:
  GET  /health          — health check
  POST /configure       — cập nhật cookie, reset client
  POST /reset           — reset client (giữ cookie)
  POST /chat            — chat với Gemini (+ download ảnh từ URLs nếu có)
"""
from __future__ import annotations

import asyncio
import io
import logging
import os
import tempfile
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

_client: Any | None = None
_client_lock = asyncio.Lock()
_cookies: dict[str, str] = {"secure_1psid": "", "secure_1psidts": ""}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load cookies from env vars nếu có (tiện khi chạy standalone)
    psid = os.getenv("GEMINI_PSID", "")
    psidts = os.getenv("GEMINI_PSIDTS", "")
    if psid:
        _cookies["secure_1psid"] = psid
        _cookies["secure_1psidts"] = psidts
        logger.info("Loaded Gemini cookies from env vars")
    yield
    # Graceful shutdown
    global _client
    async with _client_lock:
        if _client is not None:
            close_fn = getattr(_client, "close", None)
            if close_fn and asyncio.iscoroutinefunction(close_fn):
                try:
                    await close_fn()
                except Exception:
                    pass
            _client = None


app = FastAPI(title="Gemini Web Proxy", version="1.0.0", lifespan=lifespan)


# ── Client lifecycle ───────────────────────────────────────────────────────────

async def _get_client() -> Any:
    """Trả về GeminiClient singleton, lazy-init."""
    from gemini_webapi import GeminiClient

    global _client
    psid = _cookies["secure_1psid"]
    psidts = _cookies["secure_1psidts"]

    if not psid:
        raise HTTPException(
            status_code=503,
            detail="Gemini cookie chưa được cấu hình. Gọi POST /configure trước.",
        )

    async with _client_lock:
        if _client is None:
            logger.info(
                "Khởi tạo GeminiClient... psid_len=%d psidts_len=%d",
                len(psid), len(psidts or ""),
            )
            client = GeminiClient(psid, psidts or None)
            await client.init(timeout=30, auto_close=False, auto_refresh=True)
            _client = client
            logger.info("GeminiClient sẵn sàng")

    return _client


async def _evict_client() -> None:
    """Đóng và xoá cached client."""
    global _client
    async with _client_lock:
        if _client is not None:
            close_fn = getattr(_client, "close", None)
            if close_fn and asyncio.iscoroutinefunction(close_fn):
                try:
                    await close_fn()
                except Exception:
                    pass
            _client = None


# ── HTML error classifier ──────────────────────────────────────────────────────

def _html_to_http_exception(html: str) -> HTTPException:
    lower = html.lower()
    if "sign in" in lower or "accounts.google.com" in lower or "myaccount.google" in lower:
        logger.error("Gemini cookie hết hạn (nhận HTML login page)")
        return HTTPException(status_code=401, detail="Gemini cookie hết hạn — cần cập nhật __Secure-1PSID")
    if "429" in html or "too many" in lower or "rate limit" in lower:
        return HTTPException(status_code=429, detail="Gemini rate limit — thử lại sau")
    if "503" in html or "unavailable" in lower or "service error" in lower:
        return HTTPException(status_code=503, detail="Gemini service tạm thời không khả dụng")
    if "403" in html or "forbidden" in lower or "captcha" in lower:
        return HTTPException(status_code=403, detail="Gemini từ chối request (IP block/captcha)")
    snippet = html[:300].replace("\n", " ")
    logger.error("Gemini trả HTML không rõ lý do: %s", snippet)
    return HTTPException(status_code=502, detail=f"Gemini trả HTML: {snippet}")


# ── Request / Response schemas ─────────────────────────────────────────────────

class ConfigureRequest(BaseModel):
    secure_1psid: str
    secure_1psidts: str = ""


class ChatResponse(BaseModel):
    text: str


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    psid_len = len(_cookies["secure_1psid"])
    return {"status": "ok", "configured": psid_len > 0, "psid_len": psid_len}


@app.post("/configure")
async def configure(req: ConfigureRequest):
    """Cập nhật cookie và reset GeminiClient."""
    _cookies["secure_1psid"] = req.secure_1psid
    _cookies["secure_1psidts"] = req.secure_1psidts
    await _evict_client()
    logger.info(
        "Cookie updated — psid_len=%d psidts_len=%d, client evicted",
        len(req.secure_1psid), len(req.secure_1psidts or ""),
    )
    return {"ok": True}


@app.post("/reset")
async def reset():
    """Reset GeminiClient (cookie giữ nguyên)."""
    await _evict_client()
    logger.info("Client reset")
    return {"ok": True}


@app.get("/debug-auth")
async def debug_auth():
    """So sánh fake cookie vs real cookie để xác nhận auth mode."""
    from gemini_webapi import GeminiClient

    results = {}

    # Test 1: fake cookie
    try:
        c = GeminiClient("fake_invalid_xxxxx", None)
        await c.init(timeout=15, auto_close=False, auto_refresh=False)
        r = await c.generate_content("Reply with exactly one word: GUESTOK")
        results["fake_cookie"] = {"success": True, "text": r.text[:80]}
        await c.close()
    except Exception as e:
        results["fake_cookie"] = {"success": False, "error": str(e)}

    # Test 2: real cookie (từ memory)
    psid = _cookies["secure_1psid"]
    psidts = _cookies["secure_1psidts"]
    results["real_cookie_lens"] = {"psid": len(psid), "psidts": len(psidts)}
    if psid:
        try:
            c2 = GeminiClient(psid, psidts or None)
            await c2.init(timeout=15, auto_close=False, auto_refresh=False)
            r2 = await c2.generate_content("Reply with exactly one word: AUTHOK")
            results["real_cookie"] = {"success": True, "text": r2.text[:80]}
            await c2.close()
        except Exception as e:
            results["real_cookie"] = {"success": False, "error": str(e)}
    else:
        results["real_cookie"] = {"skipped": "no cookie configured"}

    # Kết luận
    fake_ok = results.get("fake_cookie", {}).get("success", False)
    real_ok = results.get("real_cookie", {}).get("success", False)
    if fake_ok and real_ok:
        results["conclusion"] = "GUEST_MODE — cả 2 đều OK, cookie không có tác dụng xác thực"
    elif real_ok and not fake_ok:
        results["conclusion"] = "AUTHENTICATED — chỉ cookie thật mới hoạt động"
    elif fake_ok and not real_ok:
        results["conclusion"] = "GUEST_MODE — fake OK nhưng cookie thật lỗi (cookie hết hạn?)"
    else:
        results["conclusion"] = "BOTH_FAILED — có vấn đề mạng hoặc Gemini service"

    return results


@app.post("/chat", response_model=ChatResponse)
async def chat(
    prompt: str = Form(...),
    files: list[UploadFile] = File(default=[]),
):
    """Chat với Gemini. files là binary upload (không dùng base64)."""
    # Dùng temp file với extension đúng để MIME type được detect chính xác.
    # io.BytesIO không có filename → thư viện đặt tên random .txt → MIME sai → Gemini không nhận ra ảnh.
    temp_paths: list[str] = []

    try:
        for upload in files:
            try:
                ct = upload.content_type or "image/jpeg"
                ext = ".jpg"
                if "png" in ct:  ext = ".png"
                elif "gif" in ct: ext = ".gif"
                elif "webp" in ct: ext = ".webp"
                elif "pdf" in ct:  ext = ".pdf"
                raw = await upload.read()
                tf = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
                tf.write(raw)
                tf.close()
                temp_paths.append(tf.name)
                logger.debug("Saved upload to temp %s (%d bytes, %s)", tf.name, len(raw), ct)
            except Exception as e:
                logger.warning("Không lưu được ảnh upload: %s", e)

        kwargs: dict[str, Any] = {"temporary": True}
        if temp_paths:
            kwargs["files"] = temp_paths

        response = None
        last_exc: Exception | None = None
        for attempt in range(3):
            # Lấy client mỗi lần — nếu evict trước đó sẽ tạo fresh client
            client = await _get_client()
            try:
                response = await client.generate_content(prompt, **kwargs)
                break
            except Exception as e:
                last_exc = e
                msg = str(e)
                if any(kw in msg.lower() for kw in ("auth", "cookie", "token", "unauthorized", "sign in")):
                    logger.error("Gemini auth failure: %s", e)
                    raise HTTPException(status_code=401, detail=f"Gemini auth failed: {e}")
                # Error 1100 / Unknown API error / I/O closed = curl_cffi session broke → evict + retry
                if attempt < 2 and ("1100" in msg or "unknown api error" in msg.lower() or "stream" in msg.lower() or "i/o operation" in msg.lower() or "closed file" in msg.lower()):
                    wait = 3 * (attempt + 1)
                    logger.warning("Gemini transient error (attempt %d/3), evicting client and retry in %ds: %s", attempt + 1, wait, e)
                    await _evict_client()
                    await asyncio.sleep(wait)
                    continue
                logger.error("Gemini generate_content error: %s", e)
                raise HTTPException(status_code=500, detail=str(e))

        if response is None:
            logger.error("Gemini failed after 3 attempts: %s", last_exc)
            raise HTTPException(status_code=500, detail=str(last_exc))

        text = response.text or ""

        # Guard: HTML trả về khi session hết hạn hoặc bị rate limit
        if text.strip().startswith("<"):
            raise _html_to_http_exception(text)

        return ChatResponse(text=text)

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Unexpected error in /chat: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        for p in temp_paths:
            try:
                os.unlink(p)
            except OSError:
                pass

