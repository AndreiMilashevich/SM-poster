import re

from atproto import Client, client_utils

from config import env

LIMIT = 300  # Bluesky считает графемы; len() считает кодпоинты, то есть с небольшим запасом

# Ссылки или хэштеги. Ссылки ищем первыми, чтобы #якорь внутри URL не считался тегом.
TOKEN = re.compile(r"(https?://\S+)|(?<!\w)#(\w+)")
TRAILING = ".,!?:;)»”\"'"


def build_text(text: str) -> client_utils.TextBuilder:
    """Bluesky сам не делает ссылки и хэштеги кликабельными, их нужно разметить явно."""
    builder = client_utils.TextBuilder()
    pos = 0
    for match in TOKEN.finditer(text):
        url, tag = match.group(1), match.group(2)
        start, end = match.span()
        if url:
            # знаки препинания в конце не входят в ссылку
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
    # язык поста: поле lang в заголовке файла, по умолчанию русский
    langs = [meta.get("lang", "ru")]
    response = client.send_post(build_text(text), langs=langs)
    return response.uri
