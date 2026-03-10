import asyncio
import logging
from datetime import datetime, date, timedelta
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

import config
import database as db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


# ─── FSM States ───────────────────────────────────────────────────────────────

class BookingState(StatesGroup):
    choose_service = State()
    choose_master = State()
    choose_date = State()
    choose_time = State()
    enter_phone = State()
    confirm = State()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✂️ Записаться"), KeyboardButton(text="📋 Мои записи")],
            [KeyboardButton(text="💈 Услуги и цены"), KeyboardButton(text="📍 Контакты")],
        ],
        resize_keyboard=True
    )


def get_service_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    for s in config.SERVICES:
        buttons.append([InlineKeyboardButton(
            text=f"{s['name']} — {s['price']}₽",
            callback_data=f"service:{s['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_master_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    for m in config.MASTERS:
        buttons.append([InlineKeyboardButton(text=f"💈 {m['name']}", callback_data=f"master:{m['id']}")])
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_dates_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    today = date.today()
    for i in range(1, 15):  # следующие 14 дней
        d = today + timedelta(days=i)
        if d.weekday() not in config.WORK_DAYS:
            continue
        label = d.strftime("%d.%m (%a)")
        ru_days = {"Mon": "Пн", "Tue": "Вт", "Wed": "Ср", "Thu": "Чт", "Fri": "Пт", "Sat": "Сб", "Sun": "Вс"}
        for en, ru in ru_days.items():
            label = label.replace(en, ru)
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"date:{d.isoformat()}")])
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_time_keyboard(master_id: int, appointment_date: str, duration: int) -> InlineKeyboardMarkup:
    booked = db.get_booked_slots(master_id, appointment_date)
    buttons = []
    row = []
    hour = config.WORK_START
    while hour < config.WORK_END:
        time_str = f"{hour:02d}:00"
        if time_str in booked:
            row.append(InlineKeyboardButton(text=f"🚫 {time_str}", callback_data="booked"))
        else:
            row.append(InlineKeyboardButton(text=f"✅ {time_str}", callback_data=f"time:{time_str}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
        hour += 1
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_yes"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"),
        ]
    ])


def format_appointment(apt: dict) -> str:
    return (
        f"🗓 <b>{apt['appointment_date']}</b> в <b>{apt['appointment_time']}</b>\n"
        f"✂️ {apt['service_name']} — {apt['service_price']}₽\n"
        f"💈 Мастер: {apt['master_name']}"
    )


# ─── Handlers ─────────────────────────────────────────────────────────────────

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        f"👋 Добро пожаловать в наш барбершоп!\n\n"
        f"Мы рады видеть вас. Выберите нужное действие:",
        reply_markup=main_menu_keyboard()
    )


@dp.message(F.text == "💈 Услуги и цены")
async def show_services(message: Message):
    text = "💈 <b>Наши услуги:</b>\n\n"
    for s in config.SERVICES:
        text += f"• <b>{s['name']}</b> — {s['price']}₽ (~{s['duration']} мин)\n"
    await message.answer(text, parse_mode="HTML")


@dp.message(F.text == "📍 Контакты")
async def show_contacts(message: Message):
    await message.answer(
        "📍 <b>Наш адрес:</b> ул. Примерная, д. 1\n"
        "📞 <b>Телефон:</b> +7 (999) 123-45-67\n"
        "🕐 <b>Режим работы:</b> Пн–Сб с 10:00 до 20:00\n"
        "📸 <b>Instagram:</b> @my_barbershop",
        parse_mode="HTML"
    )


# ─── Booking flow ──────────────────────────────────────────────────────────────

@dp.message(F.text == "✂️ Записаться")
async def start_booking(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(BookingState.choose_service)
    await message.answer(
        "Выберите услугу:",
        reply_markup=get_service_keyboard()
    )


@dp.callback_query(F.data.startswith("service:"), BookingState.choose_service)
async def choose_service(callback: CallbackQuery, state: FSMContext):
    service_id = int(callback.data.split(":")[1])
    service = next((s for s in config.SERVICES if s["id"] == service_id), None)
    if not service:
        await callback.answer("Услуга не найдена")
        return
    await state.update_data(service=service)
    await state.set_state(BookingState.choose_master)
    await callback.message.edit_text(
        f"Вы выбрали: <b>{service['name']}</b> — {service['price']}₽\n\nВыберите мастера:",
        reply_markup=get_master_keyboard(),
        parse_mode="HTML"
    )


@dp.callback_query(F.data.startswith("master:"), BookingState.choose_master)
async def choose_master(callback: CallbackQuery, state: FSMContext):
    master_id = int(callback.data.split(":")[1])
    master = next((m for m in config.MASTERS if m["id"] == master_id), None)
    if not master:
        await callback.answer("Мастер не найден")
        return
    await state.update_data(master=master)
    await state.set_state(BookingState.choose_date)
    await callback.message.edit_text(
        f"Мастер: <b>{master['name']}</b>\n\nВыберите дату:",
        reply_markup=get_dates_keyboard(),
        parse_mode="HTML"
    )


@dp.callback_query(F.data.startswith("date:"), BookingState.choose_date)
async def choose_date(callback: CallbackQuery, state: FSMContext):
    appointment_date = callback.data.split(":")[1]
    data = await state.get_data()
    master = data["master"]
    service = data["service"]
    await state.update_data(appointment_date=appointment_date)
    await state.set_state(BookingState.choose_time)
    await callback.message.edit_text(
        f"Дата: <b>{appointment_date}</b>\n\nВыберите время:\n✅ — свободно  🚫 — занято",
        reply_markup=get_time_keyboard(master["id"], appointment_date, service["duration"]),
        parse_mode="HTML"
    )


@dp.callback_query(F.data == "booked")
async def booked_slot(callback: CallbackQuery):
    await callback.answer("Это время уже занято, выберите другое", show_alert=True)


@dp.callback_query(F.data.startswith("time:"), BookingState.choose_time)
async def choose_time(callback: CallbackQuery, state: FSMContext):
    appointment_time = callback.data.split(":")[1]
    await state.update_data(appointment_time=appointment_time)
    await state.set_state(BookingState.enter_phone)
    await callback.message.edit_text(
        f"Время: <b>{appointment_time}</b>\n\n📱 Введите ваш номер телефона для подтверждения:",
        parse_mode="HTML"
    )


@dp.message(BookingState.enter_phone)
async def enter_phone(message: Message, state: FSMContext):
    phone = message.text.strip()
    if not any(c.isdigit() for c in phone):
        await message.answer("Пожалуйста, введите корректный номер телефона.")
        return
    await state.update_data(phone=phone)
    data = await state.get_data()
    summary = (
        f"📋 <b>Подтвердите запись:</b>\n\n"
        f"✂️ Услуга: <b>{data['service']['name']}</b> — {data['service']['price']}₽\n"
        f"💈 Мастер: <b>{data['master']['name']}</b>\n"
        f"🗓 Дата: <b>{data['appointment_date']}</b>\n"
        f"🕐 Время: <b>{data['appointment_time']}</b>\n"
        f"📱 Телефон: <b>{phone}</b>"
    )
    await state.set_state(BookingState.confirm)
    await message.answer(summary, reply_markup=get_confirm_keyboard(), parse_mode="HTML")


@dp.callback_query(F.data == "confirm_yes", BookingState.confirm)
async def confirm_booking(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user = callback.from_user
    apt_id = db.create_appointment(
        user_id=user.id,
        username=user.username or "",
        full_name=user.full_name,
        phone=data["phone"],
        master_id=data["master"]["id"],
        master_name=data["master"]["name"],
        service_id=data["service"]["id"],
        service_name=data["service"]["name"],
        service_price=data["service"]["price"],
        appointment_date=data["appointment_date"],
        appointment_time=data["appointment_time"],
    )
    await state.clear()
    await callback.message.edit_text(
        f"✅ <b>Запись подтверждена!</b>\n\n"
        f"Номер записи: <b>#{apt_id}</b>\n"
        f"✂️ {data['service']['name']}\n"
        f"💈 Мастер: {data['master']['name']}\n"
        f"🗓 {data['appointment_date']} в {data['appointment_time']}\n\n"
        f"Ждём вас! Если понадобится отменить — нажмите «📋 Мои записи».",
        parse_mode="HTML"
    )
    # Уведомление администратору
    if config.ADMIN_ID:
        try:
            await bot.send_message(
                config.ADMIN_ID,
                f"🔔 <b>Новая запись #{apt_id}</b>\n\n"
                f"👤 {user.full_name} (@{user.username})\n"
                f"📱 {data['phone']}\n"
                f"✂️ {data['service']['name']} — {data['service']['price']}₽\n"
                f"💈 Мастер: {data['master']['name']}\n"
                f"🗓 {data['appointment_date']} в {data['appointment_time']}",
                parse_mode="HTML"
            )
        except Exception:
            pass


# ─── My appointments ──────────────────────────────────────────────────────────

@dp.message(F.text == "📋 Мои записи")
async def my_appointments(message: Message):
    appointments = db.get_user_appointments(message.from_user.id)
    if not appointments:
        await message.answer("У вас нет активных записей.\n\nНажмите «✂️ Записаться» чтобы записаться.")
        return
    text = "📋 <b>Ваши записи:</b>\n\n"
    buttons = []
    for apt in appointments:
        text += f"#{apt['id']} — " + format_appointment(apt) + "\n\n"
        buttons.append([InlineKeyboardButton(
            text=f"❌ Отменить #{apt['id']}",
            callback_data=f"cancel_apt:{apt['id']}"
        )])
    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")


@dp.callback_query(F.data.startswith("cancel_apt:"))
async def cancel_appointment_handler(callback: CallbackQuery):
    apt_id = int(callback.data.split(":")[1])
    success = db.cancel_appointment(apt_id, callback.from_user.id)
    if success:
        apt = db.get_appointment_by_id(apt_id)
        await callback.message.edit_text(f"✅ Запись #{apt_id} отменена.")
        if config.ADMIN_ID and apt:
            try:
                await bot.send_message(
                    config.ADMIN_ID,
                    f"❌ <b>Запись #{apt_id} отменена клиентом</b>\n\n"
                    f"👤 {callback.from_user.full_name}\n"
                    f"✂️ {apt['service_name']}\n"
                    f"💈 {apt['master_name']}\n"
                    f"🗓 {apt['appointment_date']} в {apt['appointment_time']}",
                    parse_mode="HTML"
                )
            except Exception:
                pass
    else:
        await callback.answer("Не удалось отменить запись", show_alert=True)


# ─── Cancel from FSM ──────────────────────────────────────────────────────────

@dp.callback_query(F.data == "cancel")
async def cancel_booking(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Запись отменена.")
    await callback.message.answer("Выберите действие:", reply_markup=main_menu_keyboard())


# ─── Admin: today's schedule ──────────────────────────────────────────────────

@dp.message(Command("schedule"))
async def admin_schedule(message: Message):
    if message.from_user.id != config.ADMIN_ID:
        return
    today = date.today().isoformat()
    appointments = db.get_all_appointments_for_date(today)
    if not appointments:
        await message.answer(f"На сегодня ({today}) записей нет.")
        return
    text = f"📅 <b>Расписание на {today}:</b>\n\n"
    for apt in appointments:
        text += (
            f"🕐 {apt['appointment_time']} — 💈 {apt['master_name']}\n"
            f"   👤 {apt['full_name']} ({apt['phone']})\n"
            f"   ✂️ {apt['service_name']} — {apt['service_price']}₽\n\n"
        )
    await message.answer(text, parse_mode="HTML")


# ─── Main ─────────────────────────────────────────────────────────────────────

async def main():
    db.init_db()
    logger.info("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
