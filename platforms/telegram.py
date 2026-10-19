import json
from contextlib import ExitStack
from pathlib import Path

import requests

from config import env, get_media

LIMIT = 4096          # message text limit
CAPTION_LIMIT = 1024  # caption limit when the post has photos or videos
SUPPORTS_MEDIA = True

PHOTO_EXT = {".jpg", ".jpeg", ".png", ".webp", ".jfif"}
VIDEO_EXT = {".mp4", ".mov", ".m4v"}
MAX_PHOTO = 10 * 1024 * 1024  # Telegram photo size limit
MAX_FILE = 50 * 1024 * 1024   # file upload limit via the Bot API
MAX_ALBUM = 10                # maximum files in one album


def _kind(path: str) -> str:
    """Detect the file type and check its size. Fail with a clear error."""
    extension = Path(path).suffix.lower()
    if extension in PHOTO_EXT:
        kind, limit = "photo", MAX_PHOTO
    elif extension in VIDEO_EXT:
        kind, limit = "video", MAX_FILE
    else:
        raise RuntimeError(f"Telegram: неподдерживаемый формат файла {path}")
    size = Path(path).stat().st_size  # a missing file raises FileNotFoundError
    if size > limit:
        raise RuntimeError(
            f"Telegram: файл {path} слишком большой ({size / 1048576:.1f} МБ, "
            f"максимум {limit // 1048576} МБ)"
        )
    return kind


def _call(base: str, method: str, **kwargs):
    response = requests.post(f"{base}/{method}", timeout=300, **kwargs)
    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram: {data.get('description', response.status_code)}")
    return data["result"]


def publish(text: str, meta: dict) -> str:
    base = f"https://api.telegram.org/bot{env('TELEGRAM_BOT_TOKEN')}"
    chat_id = env("TELEGRAM_CHAT_ID")
    files = get_media(meta)

    if not files:
        result = _call(base, "sendMessage", json={"chat_id": chat_id, "text": text})
        return str(result["message_id"])

    if len(files) > MAX_ALBUM:
        raise RuntimeError(f"Telegram: в альбоме максимум {MAX_ALBUM} файлов")
    if len(text) > CAPTION_LIMIT:
        raise RuntimeError(
            f"Telegram: подпись слишком длинная ({len(text)}/{CAPTION_LIMIT})"
        )
    kinds = [_kind(path) for path in files]

    with ExitStack() as stack:
        handles = {
            f"file{i}": stack.enter_context(open(path, "rb"))
            for i, path in enumerate(files)
        }
        if len(files) == 1:
            kind = kinds[0]
            fields = {"chat_id": chat_id, "caption": text}
            if kind == "video":
                fields["supports_streaming"] = "true"
            result = _call(
                base,
                "sendPhoto" if kind == "photo" else "sendVideo",
                data=fields,
                files={kind: handles["file0"]},
            )
        else:
            # Album: the caption goes on the first item, files are attached via attach://
            media = []
            for i, kind in enumerate(kinds):
                item = {"type": kind, "media": f"attach://file{i}"}
                if i == 0:
                    item["caption"] = text
                if kind == "video":
                    item["supports_streaming"] = True
                media.append(item)
            result = _call(
                base,
                "sendMediaGroup",
                data={"chat_id": chat_id, "media": json.dumps(media)},
                files=handles,
            )

    message = result[0] if isinstance(result, list) else result
    return str(message["message_id"])
