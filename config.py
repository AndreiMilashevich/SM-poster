import os


def env(name: str) -> str:
    """Возвращает переменную окружения или падает с понятной ошибкой."""
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Не задана переменная окружения: {name}")
    return value
