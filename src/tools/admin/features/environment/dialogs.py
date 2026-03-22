from __future__ import annotations

import json
from typing import Any


def safe_int(value: str, default: int = 0) -> int:
    try:
        return int(str(value or "").strip())
    except (TypeError, ValueError):
        return int(default)



def safe_float(value: str, default: float = 0.0) -> float:
    try:
        return float(str(value or "").strip())
    except (TypeError, ValueError):
        return float(default)



def parse_text_lines(text: str) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    raw = str(text or "")
    for line in raw.replace(",", "\n").splitlines():
        value = str(line or "").strip()
        if not value:
            continue
        lowered = value.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        result.append(value)
    return result



def parse_tag_lines(text: str) -> list[str]:
    return [entry.lower() for entry in parse_text_lines(text)]



def format_text_lines(values: list[str] | None) -> str:
    return "\n".join(str(value or "") for value in (values or []))



def parse_json_dict(text: str) -> dict[str, Any]:
    raw = str(text or "").strip()
    if not raw:
        return {}
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("Expected a JSON object.")
    return payload



def format_json_dict(value: dict[str, Any] | None) -> str:
    if not value:
        return "{}"
    return json.dumps(dict(value), indent=2, ensure_ascii=False, sort_keys=True)



def parse_weighted_fragments(text: str) -> list[dict[str, Any]]:
    fragments: list[dict[str, Any]] = []
    for raw_line in str(text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = [part.strip() for part in line.split("||")]
        fragment_text = parts[0] if parts else ""
        if not fragment_text:
            continue
        weight = safe_float(parts[1], 1.0) if len(parts) >= 2 and parts[1] else 1.0
        required = parse_tag_lines(parts[2]) if len(parts) >= 3 else []
        excluded = parse_tag_lines(parts[3]) if len(parts) >= 4 else []
        fragments.append(
            {
                "text": fragment_text,
                "weight": weight,
                "requiredTags": required,
                "excludedTags": excluded,
            }
        )
    return fragments



def format_weighted_fragments(fragments: list[dict[str, Any]] | None) -> str:
    lines: list[str] = []
    for fragment in fragments or []:
        if hasattr(fragment, "to_dict"):
            payload = fragment.to_dict()
        else:
            payload = dict(fragment or {})
        text = str(payload.get("text", "") or "").strip()
        if not text:
            continue
        weight = payload.get("weight", 1.0)
        required = format_text_lines(payload.get("requiredTags", []))
        excluded = format_text_lines(payload.get("excludedTags", []))
        line = f"{text} || {weight}"
        if required or excluded:
            line += f" || {required.replace(chr(10), ', ')} || {excluded.replace(chr(10), ', ')}"
        lines.append(line)
    return "\n".join(lines)
