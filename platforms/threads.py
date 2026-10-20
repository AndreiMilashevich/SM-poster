import time
from pathlib import Path

import requests

from config import VIDEO_EXT, env, public_url

LIMIT = 500
SUPPORTS_MEDIA = True
MAX_CAROUSEL = 20  # a carousel holds 2 to 20 items
MEDIA_LIMIT = MAX_CAROUSEL
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


def _is_video(path: str) -> bool:
    return Path(path).suffix.lower() in VIDEO_EXT


def _moov_at_front(path: str) -> bool:
    """True if the moov atom comes before the media data, which Threads requires."""
    with open(path, "rb") as file:
        while True:
            header = file.read(8)
            if len(header) < 8:
                return False
            size, kind = int.from_bytes(header[:4], "big"), header[4:8]
            if kind == b"moov":
                return True
            if kind == b"mdat":
                return False
            header_size = 8
            if size == 1:  # 64-bit size follows the header
                size = int.from_bytes(file.read(8), "big")
                header_size = 16
            if size < header_size:  # size 0 (to the end of the file) or a broken file
                return False
            file.seek(size - header_size, 1)


def _check_media(path: str) -> None:
    """Fail early with a clear message instead of a vague error from Threads."""
    extension = Path(path).suffix.lower()
    if _is_video(path):
        if extension not in {".mp4", ".mov"}:
            raise RuntimeError(f"Threads: для видео поддерживаются только MP4 и MOV ({path})")
        if not _moov_at_front(path):
            raise RuntimeError(
                f"Threads: в видео {path} служебные данные (moov) стоят в конце файла. "
                "Исправьте без перекодирования: "
                "ffmpeg -i in.mp4 -c copy -movflags +faststart out.mp4"
            )
    else:
        if extension not in {".jpg", ".jpeg", ".png"}:
            raise RuntimeError(f"Threads: для фото поддерживаются только JPEG и PNG ({path})")
        if Path(path).stat().st_size > MAX_IMAGE_BYTES:
            raise RuntimeError(f"Threads: файл {path} больше 8 МБ")


def _wait_until_ready(container_id: str, token: str, seconds: int = 60, interval: int = 2) -> None:
    """Media is processed asynchronously, so poll the container until it is ready."""
    for _ in range(seconds // interval):
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
        time.sleep(interval)
    raise RuntimeError(f"Threads: контейнер не стал готов за {seconds} секунд")


def publish_part(text: str, media: list[str], parent, root, meta: dict) -> str:
    """Publish one post. A reply points at the previous post of the thread via reply_to_id."""
    user_id = "me"
    token = env("THREADS_ACCESS_TOKEN")

    for path in media:
        _check_media(path)

    def params(**fields) -> dict:
        result = {**fields, "access_token": token}
        if text and "is_carousel_item" not in fields:
            result["text"] = text
        if parent and "is_carousel_item" not in fields:
            result["reply_to_id"] = parent
        return result

    def media_fields(path: str) -> dict:
        if _is_video(path):
            return {"media_type": "VIDEO", "video_url": public_url(path)}
        return {"media_type": "IMAGE", "image_url": public_url(path)}

    def wait(container_id: str, paths: list[str]) -> None:
        # video processing takes much longer than images
        if any(_is_video(path) for path in paths):
            _wait_until_ready(container_id, token, seconds=600, interval=10)
        else:
            _wait_until_ready(container_id, token)

    endpoint = f"{API}/{user_id}/threads"
    if not media:
        container = _post(endpoint, params(media_type="TEXT"))
    elif len(media) == 1:
        container = _post(endpoint, params(**media_fields(media[0])))
    else:
        # Carousel (images and videos can be mixed): one container per file, then one that holds them all
        children = []
        for path in media:
            item = _post(endpoint, params(**media_fields(path), is_carousel_item="true"))
            children.append(item["id"])
            wait(item["id"], [path])
        container = _post(endpoint, params(media_type="CAROUSEL", children=",".join(children)))

    if media:
        wait(container["id"], media)
    else:
        time.sleep(10)  # give Threads a moment to register a text container
    published = _post(
        f"{API}/{user_id}/threads_publish",
        {"creation_id": container["id"], "access_token": token},
    )
    return str(published["id"])