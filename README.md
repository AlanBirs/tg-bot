# Telegram Reminder Bot

## Стек
* Python 3.13
* aiogram 3.x
* SQLAlchemy 2.0 + aiosqlite
* APScheduler
* pydantic-settings

## Инструкция по запуску

1. Установите зависимости проекта в ваше виртуальное окружение:
   pip install -r requirements.txt

2. Создайте файл .env в корневой папке проекта и укажите ваши ключи:
   BOT_TOKEN=your_telegram_bot_token_here
   DB_URL=sqlite+aiosqlite:///./tg_bot.db

3. Запустите бота модульно из корня проекта:
   python -m app.main или .venv\Scripts\python.exe -m app.main

## Примечания
На win могут быть проблемы с greenlet. Решаются через pip install --force-reinstall "sqlalchemy[asyncio]" greenlet
