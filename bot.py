import asyncio
import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# ================== НАСТРОЙКИ ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")   # Токен берётся из переменной окружения
# ==============================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

KYIV = ZoneInfo("Europe/Kyiv")
UTC = timezone.utc

RIFT_HOURS = [0, 3, 6, 9, 12, 15, 18, 21]
KAIRA_HOURS = [1, 4, 7, 10, 13, 16, 19, 22]

subscribers = set()
notified = set()


def get_next_time(hours: list[int], now: datetime):
    candidates = []
    for day_offset in range(0, 2):
        day = now.date() + timedelta(days=day_offset)
        for h in hours:
            candidates.append(datetime(day.year, day.month, day.day, h, 0, tzinfo=UTC))
    future = [t for t in candidates if t > now]
    next_t = min(future)
    return next_t, next_t - now


def format_time_left(delta: timedelta) -> str:
    total = int(delta.total_seconds())
    h = total // 3600
    m = (total % 3600) // 60
    if h > 0:
        return f"{h}ч {m}м"
    return f"{m}м"


def main_keyboard():
    kb = [
        [KeyboardButton(text="🌀 Портал"), KeyboardButton(text="⚔️ Боссы")],
        [KeyboardButton(text="📅 Ближайшее"), KeyboardButton(text="🔔 Уведомления")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


@dp.message(Command("start", "help"))
async def cmd_start(message: types.Message):
    text = (
        "Привет! Я бот таймеров <b>Aion 2</b> (Европа)\n\n"
        "Используй кнопки ниже:\n"
        "🌀 Портал — следующий Spacetime Rift\n"
        "⚔️ Боссы — мировые боссы\n"
        "📅 Ближайшее — всё сразу\n"
        "🔔 Уведомления — включить/выключить оповещения"
    )
    await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=main_keyboard())


@dp.message(Command("rift"))
@dp.message(F.text == "🌀 Портал")
async def cmd_rift(message: types.Message):
    now = datetime.now(UTC)
    next_rift, left = get_next_time(RIFT_HOURS, now)
    kyiv = next_rift.astimezone(KYIV)

    text = (
        f"🌀 <b>Следующий Spacetime Rift</b>\n\n"
        f"⏰ В Киеве: <b>{kyiv.strftime('%H:%M')}</b> ({kyiv.strftime('%d.%m')})\n"
        f"⏳ Осталось: <b>{format_time_left(left)}</b>\n\n"
        f"Портал открыт ~10 минут"
    )
    await message.answer(text, parse_mode=ParseMode.HTML)


@dp.message(Command("boss"))
@dp.message(F.text == "⚔️ Боссы")
async def cmd_boss(message: types.Message):
    now = datetime.now(UTC)
    next_kaira, left = get_next_time(KAIRA_HOURS, now)
    kyiv = next_kaira.astimezone(KYIV)

    text = (
        f"⚔️ <b>Мировые боссы</b>\n\n"
        f"<b>Watcher Kaira</b>\n"
        f"⏰ {kyiv.strftime('%H:%M')} ({kyiv.strftime('%d.%m')})\n"
        f"⏳ через {format_time_left(left)}\n\n"
        f"<b>Artifact Siege + Executors</b>\n"
        f"Пн / Чт / Сб ≈ 21:00–21:30\n\n"
        f"<b>Guardian Lord Nahma</b>\n"
        f"Пт / Вс ≈ 21:00"
    )
    await message.answer(text, parse_mode=ParseMode.HTML)


@dp.message(Command("next"))
@dp.message(F.text == "📅 Ближайшее")
async def cmd_next(message: types.Message):
    now = datetime.now(UTC)
    next_rift, left_rift = get_next_time(RIFT_HOURS, now)
    next_kaira, left_kaira = get_next_time(KAIRA_HOURS, now)

    text = (
        f"📅 <b>Ближайшие события (Киев)</b>\n\n"
        f"🌀 <b>Spacetime Rift</b>\n"
        f"{next_rift.astimezone(KYIV).strftime('%H:%M')} — через {format_time_left(left_rift)}\n\n"
        f"⚔️ <b>Watcher Kaira</b>\n"
        f"{next_kaira.astimezone(KYIV).strftime('%H:%M')} — через {format_time_left(left_kaira)}"
    )
    await message.answer(text, parse_mode=ParseMode.HTML)


@dp.message(Command("notify"))
@dp.message(F.text == "🔔 Уведомления")
async def cmd_notify(message: types.Message):
    user_id = message.from_user.id
    if user_id in subscribers:
        subscribers.remove(user_id)
        await message.answer("🔕 Уведомления <b>выключены</b>", parse_mode=ParseMode.HTML)
    else:
        subscribers.add(user_id)
        await message.answer(
            "🔔 Уведомления <b>включены</b>\nЯ буду писать за 10–15 минут до портала и Кайры",
            parse_mode=ParseMode.HTML
        )


async def notification_loop():
    while True:
        try:
            now = datetime.now(UTC)

            # Rift
            next_rift, left_rift = get_next_time(RIFT_HOURS, now)
            minutes_left = left_rift.total_seconds() / 60
            key_rift = f"rift_{next_rift.strftime('%Y%m%d_%H')}"

            if 10 <= minutes_left <= 15 and key_rift not in notified:
                notified.add(key_rift)
                text = (
                    f"⚠️ <b>Скоро Spacetime Rift!</b>\n\n"
                    f"Через ~{int(minutes_left)} минут\n"
                    f"В Киеве: {next_rift.astimezone(KYIV).strftime('%H:%M')}"
                )
                for user_id in list(subscribers):
                    try:
                        await bot.send_message(user_id, text, parse_mode=ParseMode.HTML)
                    except:
                        subscribers.discard(user_id)

            # Kaira
            next_kaira, left_kaira = get_next_time(KAIRA_HOURS, now)
            minutes_left_k = left_kaira.total_seconds() / 60
            key_kaira = f"kaira_{next_kaira.strftime('%Y%m%d_%H')}"

            if 10 <= minutes_left_k <= 15 and key_kaira not in notified:
                notified.add(key_kaira)
                text = (
                    f"⚠️ <b>Скоро Watcher Kaira!</b>\n\n"
                    f"Через ~{int(minutes_left_k)} минут\n"
                    f"В Киеве: {next_kaira.astimezone(KYIV).strftime('%H:%M')}"
                )
                for user_id in list(subscribers):
                    try:
                        await bot.send_message(user_id, text, parse_mode=ParseMode.HTML)
                    except:
                        subscribers.discard(user_id)

            if len(notified) > 40:
                notified.clear()

        except Exception as e:
            print("Ошибка уведомлений:", e)

        await asyncio.sleep(30)


async def main():
    print("Бот запущен...")
    asyncio.create_task(notification_loop())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
