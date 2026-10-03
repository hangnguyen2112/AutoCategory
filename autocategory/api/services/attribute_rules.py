"""Shared evidence matching and dependency checks for both attribute modes."""
from __future__ import annotations

import re
import unicodedata
from typing import Any

_NEGATED = re.compile(r"\b(?:khong|ko|chua|can mua|tim mua|kem|tang)(?:\s+\w+){0,3}$")
_NEGATED_SPEC = re.compile(r"\b(?:khong|ko|chua|kem|tang)(?:\s+\w+){0,3}$")


def normalize_text(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).casefold()
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.replace("đ", "d").replace("+", " plus ")
    return " ".join(re.findall(r"[a-z0-9]+", text))


def option_names(option: dict) -> list[str]:
    if "_normalized_names" in option:
        return option["_normalized_names"]
    return list(dict.fromkeys(
        name for raw in (option.get("value"), option.get("label"))
        if (name := normalize_text(raw))
    ))


def prepare_mentions(text: str) -> list[str]:
    return [normalize_text(clause) for clause in
            re.split(r"[.!?;,\n]|\bnhưng\b|\bnhung\b", text, flags=re.I)]


def positive_option_mention(text: str, name: str, *, prepared: list[str] | None = None) -> bool:
    """Ignore negated, wanted, or accompanying items, retaining clause boundaries.

    Normalized clauses can be reused across the entire option catalog. Literal
    token matching avoids compiling thousands of per-option regexes per request.
    """
    for normalized in prepared if prepared is not None else prepare_mentions(text):
        padded = f" {normalized} "
        needle = f" {name} "
        position = padded.find(needle)
        while position >= 0:
            prefix = padded[:position].strip()
            if not _NEGATED.search(prefix):
                return True
            position = padded.find(needle, position + 1)
        # Compact specifications such as 256GB versus the option '256 GB'.
        compact = name.replace(" ", "")
        if len(compact) >= 4 and any(c.isdigit() for c in compact):
            needle = f" {compact} "
            position = padded.find(needle)
            while position >= 0:
                if not _NEGATED_SPEC.search(padded[:position].strip()):
                    return True
                position = padded.find(needle, position + 1)
    return False


def canonical_value(field: dict, raw: Any) -> str | None:
    name = normalize_text(raw)
    if not name:
        return None
    matches = {
        str(o["value"]) for o in field.get("field_options") or []
        if o.get("value") is not None and name in option_names(o)
    }
    return next(iter(matches)) if len(matches) == 1 else None


def explicit_value(field: dict, title: str, description: str,
                   *, prepared: list[str] | None = None) -> str | None:
    matches = []
    text = f"{title}\n{description}"
    if prepared is None:
        prepared = prepare_mentions(text)
    for option in field.get("field_options") or []:
        if option.get("value") is None:
            continue
        names = [n for n in option_names(option) if positive_option_mention(text, n, prepared=prepared)]
        if names:
            name = max(names, key=lambda n: (len(n.split()), len(n)))
            matches.append((len(name.split()), len(name), str(option["value"])))
    if not matches:
        return None
    best = max(m[:2] for m in matches)
    values = {m[2] for m in matches if m[:2] == best}
    return next(iter(values)) if len(values) == 1 else None


def parent_map(fields: list[dict]) -> dict[str, dict]:
    omni = {f["omni_field_id"]: f for f in fields if f.get("omni_field_id") is not None}
    local = {f["id"]: f for f in fields if f.get("id") is not None}
    # Once Omni IDs are present, never confuse them with local primary keys.
    ids = omni if omni else local
    return {f["field_key"]: ids[f["parent_field_id"]] for f in fields
            if f.get("parent_field_id") is not None and f["parent_field_id"] in ids}


def field_is_active(field: dict, values: dict, parents: dict[str, dict]) -> bool:
    seen = set()
    current = field
    while current.get("parent_field_id") is not None:
        key = current["field_key"]
        if key in seen:
            return False
        seen.add(key)
        parent = parents.get(key)
        if parent is None:
            return False
        required = canonical_value(parent, current.get("parent_field_value"))
        if required is None or values.get(parent["field_key"]) != required:
            return False
        current = parent
    return True


def resolve_explicit_values(fields: list[dict], title: str, description: str) -> dict:
    """Infer parents only from unambiguous positive evidence in their descendants."""
    parents = parent_map(fields)
    values = {f["field_key"]: value for f in fields
              if (value := explicit_value(f, title, description)) is not None}
    for _ in range(len(fields)):
        proposals: dict[str, set[str]] = {}
        for f in fields:
            if f["field_key"] not in values:
                continue
            parent = parents.get(f["field_key"])
            if parent is None:
                continue
            required = canonical_value(parent, f.get("parent_field_value"))
            if required is not None:
                proposals.setdefault(parent["field_key"], set()).add(required)
        additions = {key: next(iter(opts)) for key, opts in proposals.items()
                     if key not in values and len(opts) == 1}
        if not additions:
            break
        values.update(additions)
    return {f["field_key"]: values[f["field_key"]] for f in fields
            if f["field_key"] in values and field_is_active(f, values, parents)}


def validate_values(fields: list[dict], values: dict, explicit: dict | None = None) -> dict:
    clean = {}
    for f in fields:
        key = f["field_key"]
        value = values.get(key)
        if value is None or not str(value).strip():
            continue
        if f.get("field_options"):
            value = canonical_value(f, value)
        if value is not None:
            clean[key] = value
    clean.update(explicit or {})
    parents = parent_map(fields)
    return {f["field_key"]: clean[f["field_key"]] for f in fields
            if f["field_key"] in clean and field_is_active(f, clean, parents)}


async def select_with_dependencies(fields: list[dict], title: str, description: str, processor) -> dict:
    explicit = resolve_explicit_values(fields, title, description)
    result = dict(explicit)
    parents = parent_map(fields)
    processed = set(explicit)
    for _ in range(len(fields) + 1):
        pending = [f for f in fields if f["field_key"] not in processed
                   and field_is_active(f, result, parents)]
        if not pending:
            break
        # A parent selected in the preceding stage can disambiguate shared child
        # options (e.g. a stand available for both phone and computer accessories).
        stage_explicit = {f["field_key"]: value for f in pending
                          if (value := explicit_value(f, title, description)) is not None}
        explicit.update(stage_explicit)
        result.update(stage_explicit)
        processed.update(stage_explicit)
        pending = [f for f in pending if f["field_key"] not in processed]
        if not pending:
            continue
        result.update(await processor(pending, title, description))
        result = validate_values(fields, result, explicit)
        processed.update(f["field_key"] for f in pending)
    return validate_values(fields, result, explicit)
