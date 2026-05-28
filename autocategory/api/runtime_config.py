"""
RuntimeConfig — singleton lưu cấu hình LLM trong memory.

Lifecycle:
  1. startup: load_from_db() đọc từ bảng system_config
  2. admin switch: set_*() cập nhật memory + ghi vào DB ngay
  3. mọi LLM call: đọc từ các property của RuntimeConfig

Ưu điểm so với pydantic Settings (env var):
  - Tồn tại qua restart (lưu DB)
  - Thay đổi runtime không cần rebuild hay restart
  - Không phụ thuộc env var
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# ── Default values (dùng khi DB chưa có row) ──────────────────────────────────
_DEFAULTS: dict[str, Any] = {
    "llm.provider":                    "lm_studio",
    "llm.lm_studio_base_url":          "http://host.docker.internal:11434",
    "llm.lm_studio_model":             "google/gemma-4-e4b",
    "llm.llama_base_url":              "http://llama-server:8080",
    "llm.llama_model":                 "gemma4-e4b",
    "llm.gemini_web_secure_1psid":     "",
    "llm.gemini_web_secure_1psidts":   "",
    "llm.gemini_web_model":            "unspecified",
    "llm.deepseek_api_key":            "",
    "llm.deepseek_model":              "deepseek-chat",
}


class RuntimeConfig:
    """In-memory config store, backed by system_config table."""

    def __init__(self) -> None:
        self._data: dict[str, str] = dict(_DEFAULTS)
        self._loaded = False

    # ── Load / Save ────────────────────────────────────────────────────────────

    def load_from_db(self, db: Session) -> None:
        """Đọc tất cả key LLM từ DB vào memory. Gọi 1 lần lúc startup."""
        try:
            rows = db.execute(
                __import__("sqlalchemy").text(
                    "SELECT key, value FROM system_config WHERE key LIKE 'llm.%' AND is_active = true"
                )
            ).fetchall()
            for key, value in rows:
                self._data[key] = value
            self._loaded = True
            logger.info("RuntimeConfig loaded %d LLM keys from DB", len(rows))
        except Exception as e:
            logger.warning("RuntimeConfig: could not load from DB (%s), using defaults", e)
            self._loaded = True  # vẫn hoạt động với defaults

    def _save_to_db(self, db: Session, key: str, value: str, user_id: int | None = None) -> None:
        """Upsert một key vào system_config."""
        try:
            db.execute(
                __import__("sqlalchemy").text("""
                    INSERT INTO system_config (key, value, value_type, category, is_active, updated_by)
                    VALUES (:key, :value, 'string', 'llm', true, :uid)
                    ON CONFLICT (key) DO UPDATE
                      SET value = EXCLUDED.value,
                          updated_by = EXCLUDED.updated_by,
                          updated_at = CURRENT_TIMESTAMP
                """),
                {"key": key, "value": value, "uid": user_id},
            )
            db.commit()
        except Exception as e:
            logger.error("RuntimeConfig: failed to save key=%s: %s", key, e)
            db.rollback()

    # ── Getters ────────────────────────────────────────────────────────────────

    @property
    def llm_provider(self) -> str:
        return self._data.get("llm.provider", "lm_studio")

    @property
    def lm_studio_base_url(self) -> str:
        return self._data.get("llm.lm_studio_base_url", "http://host.docker.internal:11434")

    @property
    def lm_studio_model(self) -> str:
        return self._data.get("llm.lm_studio_model", "google/gemma-4-e4b")

    @property
    def llama_base_url(self) -> str:
        return self._data.get("llm.llama_base_url", "http://llama-server:8080")

    @property
    def llama_model(self) -> str:
        return self._data.get("llm.llama_model", "gemma4-e4b")

    @property
    def gemini_web_secure_1psid(self) -> str:
        return self._data.get("llm.gemini_web_secure_1psid", "")

    @property
    def gemini_web_secure_1psidts(self) -> str:
        return self._data.get("llm.gemini_web_secure_1psidts", "")

    @property
    def gemini_web_model(self) -> str:
        val = self._data.get("llm.gemini_web_model", "unspecified")
        # Migrate old gemini-1.x / gemini-2.x names → unspecified (không còn hợp lệ)
        if val and (val.startswith("gemini-1.") or val.startswith("gemini-2.")):
            val = "unspecified"
        return val

    @property
    def deepseek_api_key(self) -> str:
        return self._data.get("llm.deepseek_api_key", "")

    @property
    def deepseek_model(self) -> str:
        return self._data.get("llm.deepseek_model", "deepseek-chat")

    # ── Setters (cập nhật memory + DB) ────────────────────────────────────────

    def set_provider(self, value: str, db: Session, user_id: int | None = None) -> None:
        self._data["llm.provider"] = value
        self._save_to_db(db, "llm.provider", value, user_id)

    def set_lm_studio_base_url(self, value: str, db: Session, user_id: int | None = None) -> None:
        self._data["llm.lm_studio_base_url"] = value
        self._save_to_db(db, "llm.lm_studio_base_url", value, user_id)

    def set_lm_studio_model(self, value: str, db: Session, user_id: int | None = None) -> None:
        self._data["llm.lm_studio_model"] = value
        self._save_to_db(db, "llm.lm_studio_model", value, user_id)

    def set_gemini_web_cookies(
        self,
        secure_1psid: str,
        secure_1psidts: str,
        db: Session,
        user_id: int | None = None,
    ) -> None:
        self._data["llm.gemini_web_secure_1psid"] = secure_1psid
        self._data["llm.gemini_web_secure_1psidts"] = secure_1psidts
        self._save_to_db(db, "llm.gemini_web_secure_1psid", secure_1psid, user_id)
        self._save_to_db(db, "llm.gemini_web_secure_1psidts", secure_1psidts, user_id)

    def set_gemini_web_model(self, model: str, db: Session, user_id: int | None = None) -> None:
        self._data["llm.gemini_web_model"] = model
        self._save_to_db(db, "llm.gemini_web_model", model, user_id)

    def set_deepseek_config(
        self,
        api_key: str,
        model: str,
        db: Session,
        user_id: int | None = None,
    ) -> None:
        self._data["llm.deepseek_api_key"] = api_key
        self._data["llm.deepseek_model"] = model
        self._save_to_db(db, "llm.deepseek_api_key", api_key, user_id)
        self._save_to_db(db, "llm.deepseek_model", model, user_id)


# ── Singleton ──────────────────────────────────────────────────────────────────
runtime_config = RuntimeConfig()
