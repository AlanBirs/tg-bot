import re
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select

from app.database.database import async_session
from app.database.models import User, Reminder

router = Router()

# ==================== FSM States ====================
class RegisterStates(StatesGroup):
    waiting_for_username = State()

class ReminderStates(StatesGroup):
    waiting_for_time = State()
    waiting_for_message = State()

# ==================== Keyboards ====================
def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⏰ Создать напоминание")],
            [KeyboardButton(text="📋 Мои напоминания")]
        ],
        resize_keyboard=True,
        persistent=True
    )

# ==================== Хэндлеры логики ====================

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    async with async_session() as session:
        res = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = res.scalar_one_or_none()
        
        if user:
            await message.answer(
                f"👋 Рад видеть тебя снова, {user.username}!\n"
                "Используй меню внизу экрана для работы с напоминаниями:",
                reply_markup=get_main_menu_keyboard()
            )
        else:
            await state.set_state(RegisterStates.waiting_for_username)
            await message.answer(
                "👋 Привет! Добро пожаловать в бот напоминаний.\n"
                "Ты еще не зарегистрирован. Введи свой уникальный никнейм:",
                reply_markup=ReplyKeyboardRemove()
            )

@router.message(RegisterStates.waiting_for_username)
async def process_username(message: Message, state: FSMContext):
    username = message.text.strip()
    if len(username) < 3 or len(username) > 30:
        await message.answer("❌ Никнейм должен быть от 3 до 30 символов. Попробуй еще раз:")
        return

    async with async_session() as session:
        res = await session.execute(select(User).where(User.username == username))
        if res.scalar_one_or_none():
            await message.answer("❌ Этот никнейм уже занят. Придумай другой:")
            return

        new_user = User(telegram_id=message.from_user.id, username=username)
        session.add(new_user)
        await session.commit()
        
    await state.clear()
    await message.answer(
        f"✅ Регистрация успешна! Твой никнейм: {username}",
        reply_markup=get_main_menu_keyboard()
    )

@router.message(F.text == "⏰ Создать напоминание")
async def start_reminder_creation(message: Message, state: FSMContext):
    await state.set_state(ReminderStates.waiting_for_time)
    await message.answer(
        "⏰ Когда прислать напоминание?\n\n"
        "Вы можете ввести время двумя способами:\n"
        "1. Через сколько минут/часов (например: 1ч 20мин, 2 часа, 30м)\n"
        "2. Точная дата и время в формате (например: 15:30, 28.10 14:00 или 2026-12-31 23:59):"
    )

@router.message(ReminderStates.waiting_for_time)
async def process_reminder_time(message: Message, state: FSMContext):
    time_input = message.text.strip().lower()
    reminder_time = None
    now = datetime.now()

    # Сценарий 1: Парсинг интервала буквами (например: "15м", "1ч 15мин", "2 часа") через регулярки
    hours_match = re.search(r'(\d+)\s*(?:час|ч)', time_input)
    minutes_match = re.search(r'(\d+)\s*(?:минут|мин|м)', time_input)
    
    total_minutes = 0
    if hours_match:
        total_minutes += int(hours_match.group(1)) * 60
    if minutes_match:
        total_minutes += int(minutes_match.group(1))
        
    if 0 < total_minutes <= 525600:
        reminder_time = now + timedelta(minutes=total_minutes)

    # Сценарий 2: Парсинг точной абсолютной даты (например: "15:30", "28.10 14:00")
    if not reminder_time:
        formats = [
            ("%Y-%m-%d %H:%M", False), # Полный формат даты
            ("%d.%m.%Y %H:%M", False), # Классический формат с точками
            ("%d.%m %H:%M", True),     # Только день и месяц (подставим текущий год)
            ("%H:%M", True)            # Только время (подставим сегодняшний день)
        ]
        
        for fmt, is_short in formats:
            try:
                dt = datetime.strptime(message.text.strip(), fmt)
                if is_short:
                    # Достраиваем недостающие год/месяц/день из текущего времени
                    dt = dt.replace(
                        year=now.year, 
                        month=dt.month if "%d.%m" in fmt else now.month, 
                        day=dt.day if "%d.%m" in fmt else now.day
                    )
                    
                    # Если ввели только время, и оно на сегодня уже прошло — переносим на завтра
                    if fmt == "%H:%M" and dt < now:
                        dt += timedelta(days=1)
                        
                    # Если ввели день и месяц, но эта дата в текущем году уже прошла — переносим на следующий год
                    elif "%d.%m" in fmt and dt < now:
                        dt = dt.replace(year=now.year + 1)
                        
                reminder_time = dt
                break
            except ValueError:
                continue

    # Валидация: если ни один парсер не сработал или время ушло в прошлое
    if not reminder_time or reminder_time < now:
        await message.answer(
            "❌ Неверный формат времени или указана дата в прошлом.\n\n"
            "Пожалуйста, введите время в одном из форматов:\n"
            "• Интервал: 15м, 1ч 20м, 2 часа, 30 мин\n"
            "• Точное время: 15:30, 28.10 12:00, 2026-12-31 23:59"
        )
        return

    # Сохраняем и переходим к тексту сообщения
    await state.update_data(reminder_time=reminder_time.isoformat())
    await state.set_state(ReminderStates.waiting_for_message)
    await message.answer(
        f"⏰ Время установлено: {reminder_time.strftime('%d.%m.%Y %H:%M')}\n\n"
        "💬 Теперь введите текст напоминания:"
    )

@router.message(ReminderStates.waiting_for_message)
async def process_reminder_message(message: Message, state: FSMContext):
    reminder_text = message.text.strip()
    if not reminder_text:
        await message.answer("❌ Текст напоминания не может быть пустым. Введите текст:")
        return

    data = await state.get_data()
    reminder_time = datetime.fromisoformat(data['reminder_time'])

    async with async_session() as session:
        res = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = res.scalar_one_or_none()

        new_reminder = Reminder(user_id=user.id, message=reminder_text, reminder_time=reminder_time)
        session.add(new_reminder)
        await session.commit()

    await state.clear()
    await message.answer(
        f"✅ Напоминание успешно создано!\n\n"
        f"📝 Текст: {reminder_text}\n"
        f"⏰ Время отправки: {reminder_time.strftime('%d.%m.%Y %H:%M')}",
        reply_markup=get_main_menu_keyboard()
    )

@router.message(F.text == "📋 Мои напоминания")
async def cmd_my_reminders(message: Message):
    async with async_session() as session:
        res = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = res.scalar_one_or_none()
        
        if not user:
            await message.answer("❌ Ты не зарегистрирован. Напиши /start для регистрации.")
            return

        res_reminders = await session.execute(
            select(Reminder).where(Reminder.user_id == user.id).order_by(Reminder.reminder_time)
        )
        reminders = res_reminders.scalars().all()

        if not reminders:
            await message.answer("📭 У тебя пока нет активных напоминаний.")
            return

        response = ["📋 Твои напоминания:\n"]
        for idx, r in enumerate(reminders, 1):
            status = "✅ Отправлено" if r.is_sent else "⏰ Ожидает"
            response.append(f"{idx}. {r.message}\n   🗓 {r.reminder_time.strftime('%d.%m.%Y %H:%M')} [{status}]\n")

        await message.answer('\n'.join(response))
