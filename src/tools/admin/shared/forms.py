from src.domain.character_util import Attribute


def _parse_label_id(label: str) -> str:
    text = str(label or "").strip()
    if text.endswith("]") and "[" in text:
        return text[text.rfind("[") + 1 : -1].strip()
    return text


def _safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


BONUS_ATTRIBUTE_OPTIONS = ["NONE"] + [attribute.name for attribute in Attribute]
