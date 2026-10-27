from sqlalchemy import BigInteger, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from app.database.database import Base

class User(Base):
    __tablename__ = 'users'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    
    reminders: Mapped[list["Reminder"]] = relationship(back_populates="user", lazy="selectin")


class Reminder(Base):
    __tablename__ = 'reminders'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    reminder_time: Mapped[datetime] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    is_sent: Mapped[bool] = mapped_column(default=False)
    
    user: Mapped["User"] = relationship(back_populates="reminders", lazy="selectin")
