from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

# Глобальный асинхронный движок
engine = create_async_engine(settings.db_url, echo=True)

# Фабрика асинхронных сессий
async_session = async_sessionmaker(engine, expire_on_commit=False)

# Современный базовый класс для моделей
class Base(DeclarativeBase):
    pass

# Асинхронная инициализация таблиц
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
