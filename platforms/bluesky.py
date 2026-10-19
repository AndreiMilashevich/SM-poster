import io
import re

from atproto import Client, client_utils
from PIL import Image, ImageOps

from config import env, get_images

LIMIT = 300  # Bluesky counts graphemes; len() counts code points, so this check is slightly stricter
SUPPORTS_MEDIA = True
MAX_IMAGES = 4         # Bluesky allows up to 4 images per post
MAX_BYTES = 1_000_000  # Bluesky size limit for one image

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

def shrink(path: str) -> bytes:
    """Re-encode an image as JPEG that fits the Bluesky size limit."""
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
    image.thumbnail((2000, 2000))  # cap the longest side, keep the aspect ratio
    quality = 90
    while True:
        buffer = io.BytesIO()
        image.save(buffer, "JPEG", quality=quality, optimize=True)
        if buffer.tell() <= MAX_BYTES:
            return buffer.getvalue()
        if quality > 50:
            quality -= 10
        else:  # quality alone is not enough, make the picture smaller
            image = image.resize((int(image.width * 0.85), int(image.height * 0.85)))

def publish(text: str, meta: dict) -> str:
    images = get_images(meta)
    if len(images) > MAX_IMAGES:
        print(f"Bluesky принимает до {MAX_IMAGES} фото, использую первые {MAX_IMAGES}")
        images = images[:MAX_IMAGES]

    client = Client()
    client.login(env("BLUESKY_HANDLE"), env("BLUESKY_APP_PASSWORD"))
    # post language: the lang field in the front matter, Russian by default
    langs = [meta.get("lang", "ru")]
    if images:
        response = client.send_images(
            build_text(text), images=[shrink(path) for path in images], langs=langs
        )
    else:
        response = client.send_post(build_text(text), langs=langs)
    return response.uri
