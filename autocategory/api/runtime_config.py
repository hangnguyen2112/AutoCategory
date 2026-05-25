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
    "llm.provider":            "lm_studio",
    "llm.lm_studio_base_url":  "http://host.docker.internal:11434",
    "llm.lm_studio_model":     "google/gemma-4-e4b",
    "llm.llama_base_url":      "http://llama-server:8080",
    "llm.llama_model":         "gemma4-e4b",
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


# ── Singleton ──────────────────────────────────────────────────────────────────
runtime_config = RuntimeConfig()
