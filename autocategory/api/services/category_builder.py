"""
Build category vector profiles từ JSON file.
Sinh: parent_name, path, level, is_leaf, category_document
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def load_categories(json_path: str) -> list[dict]:
    path = Path(json_path)
    if not path.exists():
        raise FileNotFoundError(f"Categories JSON not found: {json_path}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _build_parent_map(categories: list[dict]) -> tuple[dict[int, dict], set[int]]:
    category_by_id: dict[int, dict] = {c["id"]: c for c in categories}
    active_parent_ids: set[int] = {
        c["parent_id"]
        for c in categories
        if c.get("is_active") == 1 and c.get("parent_id") is not None
    }
    return category_by_id, active_parent_ids


def _build_path(category: dict, category_by_id: dict[int, dict]) -> str:
    names: list[str] = []
    current: dict | None = category
    visited: set[int] = set()
    while current:
        if current["id"] in visited:
            break
        visited.add(current["id"])
        names.append(current["name"])
        parent_id = current.get("parent_id")
        current = category_by_id.get(parent_id) if parent_id else None
    return " > ".join(reversed(names))


def _build_category_document(category: dict, path: str) -> str:
    description = category.get("description") or category.get("name", "")
    return (
        f"Đường dẫn danh mục: {path}. "
        f"Tên danh mục: {category['name']}. "
        f"Mô tả: {description}."
    )


def build_leaf_profiles(categories: list[dict]) -> list[dict[str, Any]]:
    """Return danh sách profile cho các leaf category đang active."""
    category_by_id, active_parent_ids = _build_parent_map(categories)
    profiles: list[dict] = []

    for category in categories:
        if category.get("is_active") != 1:
            continue
        if category["id"] in active_parent_ids:
            continue  # không phải leaf

        path = _build_path(category, category_by_id)
        level = max(len(path.split(" > ")) - 1, 0)
        parent = category_by_id.get(category.get("parent_id"))  # type: ignore[arg-type]
        parent_name = parent["name"] if parent else None
        category_document = _build_category_document(category, path)

        profiles.append(
            {
                "category_id": category["id"],
                "name": category["name"],
                "parent_id": category.get("parent_id"),
                "parent_name": parent_name,
                "path": path,
                "level": level,
                "is_leaf": True,
                "is_active": True,
                "description": category.get("description"),
                "category_document": category_document,
            }
        )

    return profiles


def build_all_profiles(categories: list[dict]) -> list[dict[str, Any]]:
    """Return tất cả active categories (kể cả parent) – dùng cho list API."""
    category_by_id, _ = _build_parent_map(categories)
    profiles: list[dict] = []

    for category in categories:
        if category.get("is_active") != 1:
            continue
        path = _build_path(category, category_by_id)
        profiles.append(
            {
                "category_id": category["id"],
                "name": category["name"],
                "parent_id": category.get("parent_id"),
                "path": path,
                "description": category.get("description"),
                "image": category.get("image"),
            }
        )

    return profiles


class CategoryBuilder:
    """Wrapper class for category building functions"""
    
    def __init__(self, categories_path: str | None = None):
        if categories_path is None:
            categories_path = os.getenv("CATEGORIES_JSON_PATH", "/app/data/categories.json")
        self.categories_path = categories_path
        self._categories = None
    
    @property
    def categories(self) -> list[dict]:
        """Load categories lazily"""
        if self._categories is None:
            self._categories = load_categories(self.categories_path)
        return self._categories
    
    def build_leaf_profiles(self) -> list[dict[str, Any]]:
        """Build profiles for leaf categories"""
        return build_leaf_profiles(self.categories)
    
    def build_all_profiles(self) -> list[dict[str, Any]]:
        """Build profiles for all active categories"""
        return build_all_profiles(self.categories)
    
    def reload(self):
        """Reload categories from file"""
        self._categories = None
