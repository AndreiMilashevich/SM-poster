import requests

from config import env

LIMIT = 4096


def publish(text: str, meta: dict) -> str:
    response = requests.post(
        f"https://api.telegram.org/bot{env('TELEGRAM_BOT_TOKEN')}/sendMessage",
        json={"chat_id": env("TELEGRAM_CHAT_ID"), "text": text},
        timeout=30,
    )
    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram: {data.get('description', response.status_code)}")
    return str(data["result"]["message_id"])
