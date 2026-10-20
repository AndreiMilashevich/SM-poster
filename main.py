"""Publish ready posts from posts/*.md to social networks.

Run: python main.py
"""
import json
import sys
from datetime import date, datetime, time, timezone
from pathlib import Path

import frontmatter

from config import get_images, get_media
from platforms import PUBLISHERS
from splitter import plan

POSTS_DIR = Path("posts")
STATE_FILE = Path("state/published.json")
DEFAULT_NETWORKS = ["bluesky", "telegram", "threads"]


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def parse_time(value) -> datetime:
    """Convert publish_at to a timezone-aware datetime. No value means publish immediately."""
    if value is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    elif isinstance(value, date) and not isinstance(value, datetime):
        value = datetime.combine(value, time.min)
    if value.tzinfo is None:  # treat a naive time as UTC
        value = value.replace(tzinfo=timezone.utc)
    return value

def publish_thread(publisher, text: str, meta: dict, entry: dict, save) -> None:
    """Publish a post as a root post plus replies, saving progress after every part."""
    media = get_images(meta) if getattr(publisher, "IMAGES_ONLY", False) else get_media(meta)
    limit = publisher.CAPTION_LIMIT if media and hasattr(publisher, "CAPTION_LIMIT") else publisher.LIMIT
    parts = plan(text, media, limit, publisher.MEDIA_LIMIT)
    entry["total"] = len(parts)
    refs = entry["refs"]
    for part in parts[len(refs):]:  # parts that are already published are skipped
        parent = refs[-1] if refs else None
        root = refs[0] if refs else None
        refs.append(publisher.publish_part(part.text, part.media, parent, root, meta))
        save()

def main() -> int:
    state = load_state()
    failed = False

    for path in sorted(POSTS_DIR.glob("*.md")):
        if path.name.startswith("_"):
            continue

        post = frontmatter.load(path)
        if post.get("draft"):
            continue
        if parse_time(post.get("publish_at")) > datetime.now(timezone.utc):
            continue  # not due yet

        text = post.content.strip()
        if not text:
            continue

        done = state.setdefault(path.name, {})
        for network in post.get("networks", DEFAULT_NETWORKS):
            entry = done.get(network)
            if isinstance(entry, str):
                continue  # old-style record: fully published
            if entry and entry["total"] and len(entry["refs"]) >= entry["total"]:
                continue  # all parts are already published, never post twice

            publisher = PUBLISHERS.get(network)
            if publisher is None:
                print(f"{path.name}: неизвестная сеть «{network}»", file=sys.stderr)
                failed = True
                continue

            entry = done.setdefault(network, {"refs": [], "total": 0})
            try:
                publish_thread(publisher, text, post.metadata, entry, lambda: save_state(state))
                print(f"{path.name}: опубликовано в {network} (постов: {len(entry['refs'])})")
            except Exception as error:
                print(f"{path.name}: ошибка в {network}: {error}", file=sys.stderr)
                failed = True
            save_state(state)  # keep progress even if a later part failed

    save_state(state)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
