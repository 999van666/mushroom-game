# 🍄 Грибалка MVP

Рабочий MVP Telegram-игры: Bot + Mini App + FastAPI + SQLAlchemy + SQLite.

## Запуск
1. Python 3.11+
2. `python -m venv .venv`
3. Windows: `.venv\\Scripts\\activate`; Linux/macOS: `source .venv/bin/activate`
4. `pip install -r requirements.txt`
5. Скопировать `.env.example` в `.env` и заполнить `BOT_TOKEN` и `WEBAPP_URL`.
6. `python run_seed.py`
7. API: `uvicorn api.main:app --host 0.0.0.0 --port 8000`
8. В другом окне: `python -m bot.bot`

Для Telegram Mini App нужен HTTPS URL. Для локального теста можно использовать tunnel (например, Cloudflare Tunnel/ngrok). В `WEBAPP_URL` указывается публичный URL папки/статического хостинга Mini App. Для быстрого теста можно разместить `webapp` на любом HTTPS static host.

## Важно
- Токен бота не хранится в коде.
- MVP использует SQLite, чтобы запускался без отдельного сервера БД.
- Перед production рекомендуется PostgreSQL, HTTPS и строгая проверка Telegram `initData` на backend.
