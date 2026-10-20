import time
from pathlib import Path

import requests

from config import env, public_url

LIMIT = 500
SUPPORTS_MEDIA = True
MAX_CAROUSEL = 20  # a carousel holds 2 to 20 items
MEDIA_LIMIT = MAX_CAROUSEL
IMAGES_ONLY = True             # no video support yet
MAX_IMAGE_BYTES = 8 * 1024 * 1024
API = "https://graph.threads.net/v1.0"


def _request(method: str, url: str, params: dict) -> dict:
    response = requests.request(method, url, params=params, timeout=30)
    data = response.json()
    if not response.ok or "error" in data:
        message = data.get("error", {}).get("message", response.status_code)
        step = url.rsplit("/", 1)[-1]  # threads, threads_publish or a container id
        raise RuntimeError(f"Threads ({step}): {message}")
    return data


def _post(url: str, params: dict) -> dict:
    return _request("POST", url, params)


def _check_image(path: str) -> None:
    """Threads takes only JPEG and PNG up to 8 MB."""
    if Path(path).suffix.lower() not in {".jpg", ".jpeg", ".png"}:
        raise RuntimeError(f"Threads: поддерживаются только JPEG и PNG ({path})")
    if Path(path).stat().st_size > MAX_IMAGE_BYTES:
        raise RuntimeError(f"Threads: файл {path} больше 8 МБ")


def _wait_until_ready(container_id: str, token: str) -> None:
    """Media is processed asynchronously, so poll the container until it is ready."""
    for _ in range(30):
        data = _request(
            "GET",
            f"{API}/{container_id}",
            {"fields": "status,error_message", "access_token": token},
        )
        status = data.get("status")
        if status == "FINISHED":
            return
        if status in ("ERROR", "EXPIRED"):
            raise RuntimeError(
                f"Threads: контейнер {status}: {data.get('error_message', 'нет подробностей')}"
            )
        time.sleep(2)
    raise RuntimeError("Threads: контейнер не стал готов за 60 секунд")


def publish_part(text: str, media: list[str], parent, root, meta: dict) -> str:
    """Publish one post. A reply points at the previous post of the thread via reply_to_id."""
    user_id = "me"
    token = env("THREADS_ACCESS_TOKEN")

    for path in media:
        _check_image(path)

    def params(**fields) -> dict:
        result = {**fields, "access_token": token}
        if text and "is_carousel_item" not in fields:
            result["text"] = text
        if parent and "is_carousel_item" not in fields:
            result["reply_to_id"] = parent
        return result

    endpoint = f"{API}/{user_id}/threads"
    if not media:
        container = _post(endpoint, params(media_type="TEXT"))
    elif len(media) == 1:
        container = _post(endpoint, params(media_type="IMAGE", image_url=public_url(media[0])))
    else:
        # Carousel: one container per image, then one container that holds them all
        children = []
        for path in media:
            item = _post(
                endpoint,
                params(media_type="IMAGE", image_url=public_url(path), is_carousel_item="true"),
            )
            children.append(item["id"])
        for child in children:
            _wait_until_ready(child, token)
        container = _post(endpoint, params(media_type="CAROUSEL", children=",".join(children)))

    if media:
        _wait_until_ready(container["id"], token)
    else:
        time.sleep(10)  # give Threads a moment to register a text container
    published = _post(
        f"{API}/{user_id}/threads_publish",
        {"creation_id": container["id"], "access_token": token},
    )
    return str(published["id"])