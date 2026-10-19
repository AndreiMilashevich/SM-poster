import requests

from config import env

LIMIT = 500
API = "https://graph.threads.net/v1.0"


def _post(url: str, params: dict) -> dict:
    response = requests.post(url, params=params, timeout=30)
    data = response.json()
    if not response.ok or "error" in data:
        message = data.get("error", {}).get("message", response.status_code)
        raise RuntimeError(f"Threads: {message}")
    return data


def publish(text: str, meta: dict) -> str:
    user_id = env("THREADS_USER_ID")
    token = env("THREADS_ACCESS_TOKEN")

    # Шаг 1: создаём контейнер с текстом
    container = _post(
        f"{API}/{user_id}/threads",
        {"media_type": "TEXT", "text": text, "access_token": token},
    )
    # Шаг 2: публикуем контейнер
    published = _post(
        f"{API}/{user_id}/threads_publish",
        {"creation_id": container["id"], "access_token": token},
    )
    return str(published["id"])
