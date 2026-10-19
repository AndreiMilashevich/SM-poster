import os


def env(name: str) -> str:
    """Return an environment variable or fail with a clear error."""
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Не задана переменная окружения: {name}")
    return value


def get_media(meta: dict) -> list[str]:
    """Post files: the media field (a list or a single string) or the legacy image field."""
    value = meta.get("media") or meta.get("image") or []
    return [value] if isinstance(value, str) else list(value)
