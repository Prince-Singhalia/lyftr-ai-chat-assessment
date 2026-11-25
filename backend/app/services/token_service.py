def estimate_tokens(text: str) -> int:
    """Conservative fallback when provider usage is unavailable; provider usage wins."""
    return max(1, len(text.split())) if text else 0


def usage_value(usage: object, *names: str) -> int | None:
    for name in names:
        value = usage.get(name) if isinstance(usage, dict) else getattr(usage, name, None)
        if value is not None:
            return int(value)
    return None

