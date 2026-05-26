"""
DeepSeek API Proxy — thin OpenAI-compatible proxy

Chạy trong container riêng biệt. Container `api` gọi HTTP đến đây.
Proxy lưu API key, forward tất cả /v1/* đến api.deepseek.com.

Endpoints:
  GET  /health      — health check
  POST /configure   — cập nhật api_key + model tại runtime
  POST /v1/*        — forward đến DeepSeek API (OpenAI-compatible)
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"

_config: dict[str, str] = {
    "api_key": os.getenv("DEEPSEEK_API_KEY", ""),
    "model": os.getenv("DEEPSEEK_MODEL", DEFAULT_MODEL),
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    if _config["api_key"]:
        logger.info("DeepSeek API key loaded from env (len=%d)", len(_config["api_key"]))
    else:
        logger.warning("No DEEPSEEK_API_KEY — set via POST /configure or env var")
    yield


app = FastAPI(title="DeepSeek Proxy", version="1.0.0", lifespan=lifespan)


class ConfigureRequest(BaseModel):
    api_key: str
    model: str = DEFAULT_MODEL


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "configured": bool(_config["api_key"]),
        "model": _config["model"],
    }


@app.post("/configure")
async def configure(req: ConfigureRequest):
    """Cập nhật API key và model tại runtime — không cần restart container."""
    _config["api_key"] = req.api_key
    _config["model"] = req.model
    logger.info("DeepSeek config updated — model=%s key_len=%d", req.model, len(req.api_key))
    return {"ok": True, "model": _config["model"]}


@app.api_route("/v1/{path:path}", methods=["GET", "POST", "DELETE", "PUT", "PATCH"])
async def proxy(path: str, request: Request):
    """Forward tất cả /v1/* đến DeepSeek API với API key đã lưu."""
    if not _config["api_key"]:
        raise HTTPException(
            status_code=503,
            detail="DeepSeek API key chưa được cấu hình. Gọi POST /configure trước.",
        )

    body = await request.body()
    headers = {
        "Authorization": f"Bearer {_config['api_key']}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(base_url=DEEPSEEK_BASE_URL, timeout=120.0) as client:
        try:
            resp = await client.request(
                method=request.method,
                url=f"/v1/{path}",
                content=body,
                headers=headers,
            )
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="DeepSeek API timeout")
        except httpx.ConnectError as exc:
            raise HTTPException(status_code=502, detail=f"Không kết nối được DeepSeek: {exc}")

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type=resp.headers.get("content-type", "application/json"),
    )
