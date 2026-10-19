import requests

from config import env

LIMIT = 4096          # лимит текста сообщения
CAPTION_LIMIT = 1024  # лимит подписи, если у поста есть картинка
SUPPORTS_IMAGES = True


def publish(text: str, meta: dict) -> str:
    base = f"https://api.telegram.org/bot{env('TELEGRAM_BOT_TOKEN')}"
    chat_id = env("TELEGRAM_CHAT_ID")
    image = meta.get("image")  # путь к файлу относительно корня репозитория

    if image:
        if len(text) > CAPTION_LIMIT:
            raise RuntimeError(
                f"Telegram: подпись к фото слишком длинная ({len(text)}/{CAPTION_LIMIT})"
            )
        with open(image, "rb") as photo:
            response = requests.post(
                f"{base}/sendPhoto",
                data={"chat_id": chat_id, "caption": text},
                files={"photo": photo},
                timeout=60,
            )
    else:
        response = requests.post(
            f"{base}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=30,
        )

    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram: {data.get('description', response.status_code)}")
    return str(data["result"]["message_id"])
