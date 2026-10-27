from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select
from datetime import datetime
from aiogram import Bot

from app.database.database import async_session
from app.database.models import Reminder

class SchedulerService:
    def __init__(self, bot: Bot):
        self.scheduler = AsyncIOScheduler()
        self.bot = bot
    
    async def check_reminders(self):
        # Открываем сессию. Контекстный менеджер сам закроет её в случае любых ошибок
        async with async_session() as session:
            # Открываем явный блок транзакции (аналог @Transactional / try-catch-commit)
            async with session.begin():
                stmt = select(Reminder).where(Reminder.reminder_time <= datetime.now(), Reminder.is_sent == False)
                res = await session.execute(stmt)
                # Используем selectin load или подгруженные данные, чтобы избежать LazyInitializationException
                reminders = res.scalars().all()
                
                for reminder in reminders:
                    try:
                        # Напрямую обращаемся к связанному объекту user благодаря lazy="selectin" в моделях
                        if reminder.user:
                            await self.bot.send_message(
                                chat_id=reminder.user.telegram_id,
                                text=f"⏰ Напоминание: {reminder.message}"
                            )
                            reminder.is_sent = True
                    except Exception as e:
                        # Если один пользователь заблокировал бота, логгируем ошибку, 
                        # но не ломаем цикл для остальных напоминаний
                        print(f"Ошибка отправки напоминания {reminder.id}: {e}")

    def start(self):
        self.scheduler.add_job(
            self.check_reminders,
            IntervalTrigger(seconds=10),  # Проверяем базу каждые 10 секунд
            id='reminder_checker'
        )
        self.scheduler.start()
    
    def shutdown(self):
        self.scheduler.shutdown()
