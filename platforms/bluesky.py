import re

from atproto import Client, client_utils

from config import env

LIMIT = 300  # Bluesky counts graphemes; len() counts code points, so this check is slightly stricter

# Links or hashtags. Links are matched first so a #fragment inside a URL is not treated as a tag.
TOKEN = re.compile(r"(https?://\S+)|(?<!\w)#(\w+)")
TRAILING = ".,!?:;)»”\"'"


def build_text(text: str) -> client_utils.TextBuilder:
    """Bluesky does not auto-link URLs or hashtags, so they must be marked up explicitly."""
    builder = client_utils.TextBuilder()
    pos = 0
    for match in TOKEN.finditer(text):
        url, tag = match.group(1), match.group(2)
        start, end = match.span()
        if url:
            # trailing punctuation is not part of the link
            stripped = url.rstrip(TRAILING)
            end = start + len(stripped)
            url = stripped
        builder.text(text[pos:start])
        if url:
            builder.link(url, url)
        else:
            builder.tag(f"#{tag}", tag)
        pos = end
    builder.text(text[pos:])
    return builder


def publish(text: str, meta: dict) -> str:
    client = Client()
    client.login(env("BLUESKY_HANDLE"), env("BLUESKY_APP_PASSWORD"))
    # post language: the lang field in the front matter, Russian by default
    langs = [meta.get("lang", "ru")]
    response = client.send_post(build_text(text), langs=langs)
    return response.uri
