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
    "llm.provider":                    "deepseek",
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
                    """SELECT key, value FROM system_config
                       WHERE key IN ('llm.provider', 'llm.deepseek_api_key', 'llm.deepseek_model')
                         AND is_active = true"""
                )
            ).fetchall()
            for key, value in rows:
                self._data[key] = value
            # Ignore a legacy provider value left in an existing database.
            self._data["llm.provider"] = "deepseek"
            self._loaded = True
            logger.info("RuntimeConfig loaded %d LLM keys from DB", len(rows))
        except Exception as e:
            logger.warning("RuntimeConfig: could not load from DB (%s), using defaults", e)
            self._loaded = True  # vẫn hoạt động với defaults

    def _save_to_db(self, db: Session, key: str, value: str, user_id: int | None = None) -> None:
        """Upsert một key vào system_config."""
        self._save_many_to_db(db, {key: value}, user_id)

    def _save_many_to_db(
        self,
        db: Session,
        values: dict[str, str],
        user_id: int | None = None,
    ) -> None:
        """Atomically upsert multiple runtime settings."""
        try:
            for key, value in values.items():
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
            logger.error("RuntimeConfig: failed to save keys=%s: %s", list(values), e)
            db.rollback()
            raise

    # ── Getters ────────────────────────────────────────────────────────────────

    @property
    def llm_provider(self) -> str:
        return "deepseek"

    @property
    def deepseek_api_key(self) -> str:
        return self._data.get("llm.deepseek_api_key", "")

    @property
    def deepseek_model(self) -> str:
        return self._data.get("llm.deepseek_model", "deepseek-chat")

    # ── Setters (cập nhật memory + DB) ────────────────────────────────────────

    def set_provider(self, value: str, db: Session, user_id: int | None = None) -> None:
        if value != "deepseek":
            raise ValueError("This deployment supports DeepSeek only")
        self._save_to_db(db, "llm.provider", value, user_id)
        self._data["llm.provider"] = value

    def set_deepseek_config(
        self,
        api_key: str,
        model: str,
        db: Session,
        user_id: int | None = None,
    ) -> None:
        self._save_many_to_db(db, {
            "llm.deepseek_api_key": api_key,
            "llm.deepseek_model": model,
        }, user_id)
        self._data["llm.deepseek_api_key"] = api_key
        self._data["llm.deepseek_model"] = model


# ── Singleton ──────────────────────────────────────────────────────────────────
runtime_config = RuntimeConfig()
