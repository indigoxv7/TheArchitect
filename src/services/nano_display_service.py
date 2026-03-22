from __future__ import annotations


def format_nano(value) -> str:
    amount = float(value or 0.0)
    abs_amount = abs(amount)
    suffix = ""
    divisor = 1.0

    if abs_amount >= 1_000_000_000:
        suffix = " G"
        divisor = 1_000_000_000.0
    elif abs_amount >= 1_000_000:
        suffix = " M"
        divisor = 1_000_000.0
    elif abs_amount >= 1_000:
        suffix = " K"
        divisor = 1_000.0

    if divisor == 1.0:
        rounded = int(round(amount))
        return str(rounded)
    return f"{amount / divisor:.3f}{suffix}"
