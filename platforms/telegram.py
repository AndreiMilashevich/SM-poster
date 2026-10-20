import json
from contextlib import ExitStack
from pathlib import Path

import requests

from config import IMAGE_EXT, VIDEO_EXT, env

LIMIT = 4096          # message text limit
CAPTION_LIMIT = 1024  # caption limit when the post has photos or videos
SUPPORTS_MEDIA = True

# PHOTO_EXT = {".jpg", ".jpeg", ".png", ".webp", ".jfif"}
# VIDEO_EXT = {".mp4", ".mov", ".m4v"}
MAX_PHOTO = 10 * 1024 * 1024  # Telegram photo size limit
MAX_FILE = 50 * 1024 * 1024   # file upload limit via the Bot API
MAX_ALBUM = 10                # maximum files in one album
MEDIA_LIMIT = MAX_ALBUM       # how many files fit in one post

def _kind(path: str) -> str:
    """Detect the file type and check its size. Fail with a clear error."""
    extension = Path(path).suffix.lower()
    if extension in IMAGE_EXT:
        kind, limit = "photo", MAX_PHOTO
    elif extension in VIDEO_EXT:
        kind, limit = "video", MAX_FILE
    else:
        raise RuntimeError(f"Telegram: unsupported file format {path}")
    size = Path(path).stat().st_size  # a missing file raises FileNotFoundError
    if size > limit:
        raise RuntimeError(
            f"Telegram: file {path} is too large ({size / 1048576:.1f} MB, "
            f"max {limit // 1048576} MB)"
        )
    return kind


def _call(base: str, method: str, **kwargs):
    response = requests.post(f"{base}/{method}", timeout=300, **kwargs)
    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram: {data.get('description', response.status_code)}")
    return data["result"]


def publish_part(text: str, media: list[str], parent, root, meta: dict) -> int:
    """Send one message or album. A reply points at the previous message of the thread."""
    base = f"https://api.telegram.org/bot{env('TELEGRAM_BOT_TOKEN')}"
    chat_id = env("TELEGRAM_CHAT_ID")

    if not media:
        payload = {"chat_id": chat_id, "text": text}
        if parent:
            payload["reply_parameters"] = {"message_id": parent}
        return _call(base, "sendMessage", json=payload)["message_id"]

    kinds = [_kind(path) for path in media]
    fields = {"chat_id": chat_id}
    if parent:
        fields["reply_parameters"] = json.dumps({"message_id": parent})

    with ExitStack() as stack:
        handles = {
            f"file{i}": stack.enter_context(open(path, "rb"))
            for i, path in enumerate(media)
        }
        if len(media) == 1:
            kind = kinds[0]
            if text:
                fields["caption"] = text
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
            items = []
            for i, kind in enumerate(kinds):
                item = {"type": kind, "media": f"attach://file{i}"}
                if i == 0 and text:
                    item["caption"] = text
                if kind == "video":
                    item["supports_streaming"] = True
                items.append(item)
            result = _call(
                base,
                "sendMediaGroup",
                data={**fields, "media": json.dumps(items)},
                files=handles,
            )

    message = result[0] if isinstance(result, list) else result
    return message["message_id"]
