import os
import re
from pathlib import Path
from urllib.parse import quote

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXT = {".mp4", ".mov", ".m4v"}

def env(name: str) -> str:
    """Return an environment variable or fail with a clear error."""
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Не задана переменная окружения: {name}")
    return value


def _natural_key(path: Path) -> list:
    """Sort key that puts 2.jpg before 10.jpg."""
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", path.name.lower())]


def get_media(meta: dict) -> list[str]:
    """Post files: the media field (a file, a folder or a list of both) or the legacy image field."""
    value = meta.get("media") or meta.get("image") or []
    entries = [value] if isinstance(value, str) else list(value)
    files: list[str] = []
    for entry in entries:
        path = Path(entry)
        if path.is_dir():
            # a folder: take every supported file in natural name order
            found = [
                str(item)
                for item in sorted(path.iterdir(), key=_natural_key)
                if item.is_file()
                and not item.name.startswith(".")  # skip hidden files like ._photo.jpg
                and item.suffix.lower() in IMAGE_EXT | VIDEO_EXT
            ]
            if not found:
                raise RuntimeError(f"В папке {entry} нет фото и видео")
            files += found
        else:
            files.append(entry)
    return files

def get_images(meta: dict) -> list[str]:
    """Image files only, for networks that do not take videos yet."""
    files = get_media(meta)
    images = [item for item in files if Path(item).suffix.lower() in IMAGE_EXT]
    if len(images) < len(files):
        print(f"Пропущено файлов, которые не являются фото: {len(files) - len(images)}")
    return images


def public_url(path: str) -> str:
    """Public URL of a repo file, for networks that fetch media by URL (Threads)."""
    base = os.environ.get("MEDIA_BASE_URL")
    if not base:
        repo, sha = os.environ.get("GITHUB_REPOSITORY"), os.environ.get("GITHUB_SHA")
        if not (repo and sha):
            raise RuntimeError("Не задан MEDIA_BASE_URL (публичный адрес корня репозитория с медиа)")
        base = f"https://raw.githubusercontent.com/{repo}/{sha}"
    return f"{base.rstrip('/')}/{quote(Path(path).as_posix())}"
