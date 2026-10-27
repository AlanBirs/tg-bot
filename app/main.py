import asyncio
import logging
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import settings
from app.database.database import create_tables
from app.handlers.main_handler import router
from app.services.scheduler_service import SchedulerService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    # Создаем таблицы асинхронно
    await create_tables()
    
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    
    scheduler = SchedulerService(bot)
    scheduler.start()
    
    try:
        logger.info("Бот успешно запущен")
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
