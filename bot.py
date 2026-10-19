import asyncio
import os
print("=== DEBUG ENV ===")
print("BOT_TOKEN exists:", "BOT_TOKEN" in os.environ)
print("BOT_TOKEN value:", os.getenv("BOT_TOKEN"))
print("All env keys:", list(os.environ.keys()))
print("=================")

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("Задай переменную окружения BOT_TOKEN")
# ==============================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

KYIV = ZoneInfo("Europe/Kyiv")
WINNIPEG = ZoneInfo("America/Winnipeg")
UTC = timezone.utc

RIFT_HOURS = [0, 3, 6, 9, 12, 15, 18, 21]
KAIRA_HOURS = [1, 4, 7, 10, 13, 16, 19, 22]

# Artifact Siege + Executors: Пн / Чт / Сб в 21:00 UTC
# Guardian Lord Nahma: Пт / Вс в 21:00 UTC
ARTIFACT_DAYS = [0, 3, 5]  # Пн=0, Чт=3, Сб=5
NAHMA_DAYS = [4, 6]        # Пт=4, Вс=6

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


def get_next_weekday_time(weekdays: list[int], hour: int, now: datetime):
    """Ближайшее время по дням недели (0=Пн ... 6=Вс) в заданный час UTC."""
    candidates = []
    for day_offset in range(0, 8):
        day = now.date() + timedelta(days=day_offset)
        if day.weekday() in weekdays:
            t = datetime(day.year, day.month, day.day, hour, 0, tzinfo=UTC)
            if t > now:
                candidates.append(t)
    if not candidates:
        return None, None
    next_t = min(candidates)
    return next_t, next_t - now


def format_time_left(delta: timedelta) -> str:
    if delta is None:
        return "—"
    total = int(delta.total_seconds())
    h = total // 3600
    m = (total % 3600) // 60
    if h > 0:
        return f"{h}ч {m}м"
    return f"{m}м"


def format_both_times(dt: datetime) -> str:
    if dt is None:
        return "—"
    kyiv = dt.astimezone(KYIV)
    win = dt.astimezone(WINNIPEG)
    return (
        f"Киев: <b>{kyiv.strftime('%H:%M')}</b> ({kyiv.strftime('%d.%m')})\n"
        f"Виннипег: <b>{win.strftime('%H:%M')}</b> ({win.strftime('%d.%m')})"
    )


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
        "🔔 Уведомления — включить/выключить оповещения\n\n"
        "Времена показываются в <b>Киеве</b> и <b>Виннипеге</b>"
    )
    await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=main_keyboard())


@dp.message(Command("rift"))
@dp.message(F.text == "🌀 Портал")
async def cmd_rift(message: types.Message):
    now = datetime.now(UTC)
    next_rift, left = get_next_time(RIFT_HOURS, now)
    text = (
        f"🌀 <b>Следующий Spacetime Rift</b>\n\n"
        f"{format_both_times(next_rift)}\n"
        f"⏳ Осталось: <b>{format_time_left(left)}</b>\n\n"
        f"Портал открыт ~10 минут"
    )
    await message.answer(text, parse_mode=ParseMode.HTML)


@dp.message(Command("boss"))
@dp.message(F.text == "⚔️ Боссы")
async def cmd_boss(message: types.Message):
    now = datetime.now(UTC)

    next_kaira, left_kaira = get_next_time(KAIRA_HOURS, now)
    next_artifact, left_artifact = get_next_weekday_time(ARTIFACT_DAYS, 21, now)
    next_nahma, left_nahma = get_next_weekday_time(NAHMA_DAYS, 21, now)

    text = (
        f"⚔️ <b>Мировые боссы</b>\n\n"
        f"<b>Watcher Kaira</b>\n"
        f"{format_both_times(next_kaira)}\n"
        f"⏳ через {format_time_left(left_kaira)}\n\n"
        f"<b>Artifact Siege + Executors</b>\n"
        f"{format_both_times(next_artifact)}\n"
        f"⏳ через {format_time_left(left_artifact)}\n"
        f"(Пн / Чт / Сб)\n\n"
        f"<b>Guardian Lord Nahma</b>\n"
        f"{format_both_times(next_nahma)}\n"
        f"⏳ через {format_time_left(left_nahma)}\n"
        f"(Пт / Вс)"
    )
    await message.answer(text, parse_mode=ParseMode.HTML)


@dp.message(Command("next"))
@dp.message(F.text == "📅 Ближайшее")
async def cmd_next(message: types.Message):
    now = datetime.now(UTC)
    next_rift, left_rift = get_next_time(RIFT_HOURS, now)
    next_kaira, left_kaira = get_next_time(KAIRA_HOURS, now)

    text = (
        f"📅 <b>Ближайшие события</b>\n\n"
        f"🌀 <b>Spacetime Rift</b>\n"
        f"{format_both_times(next_rift)}\n"
        f"через {format_time_left(left_rift)}\n\n"
        f"⚔️ <b>Watcher Kaira</b>\n"
        f"{format_both_times(next_kaira)}\n"
        f"через {format_time_left(left_kaira)}"
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
                    f"🌀 <b>Скоро Spacetime Rift!</b>\n\n"
                    f"Через ~{int(minutes_left)} минут\n"
                    f"{format_both_times(next_rift)}"
                )
                for user_id in list(subscribers):
                    try:
                        await bot.send_message(user_id, text, parse_mode=ParseMode.HTML)
                    except Exception:
                        subscribers.discard(user_id)

            # Kaira
            next_kaira, left_kaira = get_next_time(KAIRA_HOURS, now)
            minutes_left_k = left_kaira.total_seconds() / 60
            key_kaira = f"kaira_{next_kaira.strftime('%Y%m%d_%H')}"
            if 10 <= minutes_left_k <= 15 and key_kaira not in notified:
                notified.add(key_kaira)
                text = (
                    f"👁️ <b>Скоро Watcher Kaira!</b>\n\n"
                    f"Через ~{int(minutes_left_k)} минут\n"
                    f"{format_both_times(next_kaira)}"
                )
                for user_id in list(subscribers):
                    try:
                        await bot.send_message(user_id, text, parse_mode=ParseMode.HTML)
                    except Exception:
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
