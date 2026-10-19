# crosspost

Пишете пост в `posts/*.md`, коммитите, GitHub Actions публикует в Bluesky, Telegram и Threads.
X не автоматизирован, постится вручную.

## Формат поста

```md
---
publish_at: 2026-10-20T10:00:00+02:00   # необязательно; всегда с часовым поясом
networks: [bluesky, telegram, threads]  # необязательно; по умолчанию все три
lang: ru                                # необязательно; язык поста в Bluesky, по умолчанию ru
image: images/photo.jpg                 # необязательно; картинка (пока только Telegram)
draft: true                             # необязательно; пропустить пост
---
Текст поста.
```

- Файлы, начинающиеся с `_`, игнорируются.
- Без `publish_at` пост уходит при ближайшем запуске. Без часового пояса время считается по UTC.
- Что уже опубликовано, хранится в `state/published.json` (бот коммитит его сам), так что дублей не будет.
- Если сеть вернула ошибку, на следующем запуске (каждые ~15 минут) повторится только она.
- Слишком длинный пост не публикуется в сеть, где он не влезает (лимиты: Bluesky 300, Threads 500, Telegram 4096), а запуск помечается как упавший.
- В Bluesky ссылки и #хэштеги размечаются автоматически.
- Картинки кладите в папку `images/` и коммитьте вместе с постом. Пока их публикует только Telegram (подпись до 1024 символов, файл до 10 МБ); в остальных сетях пост выйдет без картинки, а в логе появится предупреждение.

## Секреты (Settings → Secrets and variables → Actions)

| Секрет | Откуда |
|---|---|
| `BLUESKY_HANDLE` | например `name.bsky.social` |
| `BLUESKY_APP_PASSWORD` | Настройки Bluesky → App Passwords |
| `TELEGRAM_BOT_TOKEN` | @BotFather |
| `TELEGRAM_CHAT_ID` | `@channelname` или числовой ID; бот должен быть админом канала с правом публикации |
| `THREADS_USER_ID`, `THREADS_ACCESS_TOKEN` | Meta for Developers, приложение с Threads API |

Токен Threads живёт ~60 дней, его нужно обновлять вручную и менять в секретах.

Также включите Settings → Actions → General → Workflow permissions → Read and write.

## Запуск локально

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=...
python main.py
```

Репозиторий лучше сделать приватным: там лежат черновики.

## Структура

- `main.py` читает посты, проверяет дату и состояние, вызывает публикаторы
- `platforms/` по одному файлу на сеть (`LIMIT` и `publish()`), реестр в `__init__.py`
- `config.py` чтение переменных окружения
