"""Split a post into a thread: a root post plus replies."""
import re
from dataclasses import dataclass, field
from pathlib import Path

from config import VIDEO_EXT


@dataclass
class Part:
    text: str
    media: list[str] = field(default_factory=list)


def _cut_position(window: str, limit: int) -> int:
    """Best place to cut a window of text: a paragraph, a sentence, then a word boundary."""
    minimum = limit // 3  # never cut so early that a chunk becomes tiny
    paragraph = window.rfind("\n\n")
    if paragraph >= minimum:
        return paragraph
    sentences = [m.end() for m in re.finditer(r"[.!?…]\s", window) if m.end() >= minimum]
    if sentences:
        return sentences[-1]
    space = max(window.rfind(" "), window.rfind("\n"))
    if space > 0:  # any word boundary is better than cutting a word or a link in half
        return space
    return limit  # no whitespace at all, hard cut


def split_text(text: str, limit: int) -> list[str]:
    """Split text into chunks of at most `limit` characters."""
    text = text.strip()
    chunks = []
    while len(text) > limit:
        cut = _cut_position(text[: limit + 1], limit)
        chunk = text[:cut].rstrip()
        if not chunk:  # safety net, should not happen
            chunk, cut = text[:limit], limit
        chunks.append(chunk)
        text = text[cut:].lstrip()
    if text:
        chunks.append(text)
    return chunks


def batch_media(media: list[str], limit: int, video_alone: bool = False) -> list[list[str]]:
    """Group media into posts of at most `limit` files, keeping the order."""
    batches: list[list[str]] = []
    current: list[str] = []
    for item in media:
        if video_alone and Path(item).suffix.lower() in VIDEO_EXT:
            if current:  # a video never shares a post with other files
                batches.append(current)
                current = []
            batches.append([item])
            continue
        current.append(item)
        if len(current) == limit:
            batches.append(current)
            current = []
    if current:
        batches.append(current)
    return batches


def plan(
    text: str, media: list[str], text_limit: int, media_limit: int, video_alone: bool = False
) -> list[Part]:
    """Spread text chunks and media batches over posts: the first is the root, the rest are replies."""
    chunks = split_text(text, text_limit) if text.strip() else []
    batches = batch_media(media, media_limit, video_alone)
    count = max(len(chunks), len(batches), 1)
    return [
        Part(chunks[i] if i < len(chunks) else "", batches[i] if i < len(batches) else [])
        for i in range(count)
    ]
