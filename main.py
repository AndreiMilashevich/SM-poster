"""Публикует готовые посты из posts/*.md в соцсети.

Запуск: python main.py
"""
import json
import sys
from datetime import date, datetime, time, timezone
from pathlib import Path

import frontmatter

from platforms import PUBLISHERS

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
    """Приводит publish_at к datetime с часовым поясом. Нет значения = публиковать сразу."""
    if value is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    elif isinstance(value, date) and not isinstance(value, datetime):
        value = datetime.combine(value, time.min)
    if value.tzinfo is None:  # без пояса считаем время UTC
        value = value.replace(tzinfo=timezone.utc)
    return value


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
            continue  # ещё не время

        text = post.content.strip()
        if not text:
            continue

        done = state.setdefault(path.name, {})
        for network in post.get("networks", DEFAULT_NETWORKS):
            if network in done:
                continue  # уже опубликовано, второй раз не постим

            publisher = PUBLISHERS.get(network)
            if publisher is None:
                print(f"{path.name}: неизвестная сеть «{network}»", file=sys.stderr)
                failed = True
                continue
            if len(text) > publisher.LIMIT:
                print(
                    f"{path.name}: слишком длинный пост для {network} "
                    f"({len(text)}/{publisher.LIMIT})",
                    file=sys.stderr,
                )
                failed = True
                continue

            if post.get("image") and not getattr(publisher, "SUPPORTS_IMAGES", False):
                print(f"{path.name}: {network} пока не поддерживает картинки, публикую без неё")

            try:
                done[network] = publisher.publish(text, post.metadata)
                print(f"{path.name}: опубликовано в {network}")
            except Exception as error:
                print(f"{path.name}: ошибка в {network}: {error}", file=sys.stderr)
                failed = True
            save_state(state)  # сохраняем прогресс после каждой сети

    save_state(state)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
