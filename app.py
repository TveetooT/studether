import os
import logging
import asyncio
import time
import html
import random
from datetime import datetime, timedelta
from collections import Counter
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.types import (
    ErrorEvent,
    BotCommand,
    CallbackQuery,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from supabase import create_client
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

# ---------- Импорт регионов ----------
from regions import Regions

# ---------- Логирование ----------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------- Переменные окружения ----------
TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_TOKEN не задан")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL и SUPABASE_KEY должны быть заданы")

WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
if not WEBHOOK_URL:
    raise ValueError("WEBHOOK_URL не задан")

ROOT_CODE = os.environ.get("ROOT_CODE")
if not ROOT_CODE:
    raise ValueError("ROOT_CODE не задан")

# ---------- Бот и диспетчер ----------
bot = Bot(token=TOKEN)
dp = Dispatcher()

# ---------- Подключение к БД ----------
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------- Константы ----------
BOT_NAME = "Livether"
DIAG_TEST_ID = -999999

# ---------- Списки ----------
Actions = ["name", "age", "univer", "about", "requirements", "confirm"]
ActionEdit = ["nameEdit", "ageEdit", "univerEdit", "aboutEdit", "requirementsEdit"]

# ---------- Словарь фраз ----------
Phrases = {
    "StartMessage": (
        "👋 Привет! Я бот <b>Livether</b> — твой помощник в поиске идеального соседа для совместной аренды! 🏠\n\n"
        "Мы подберём тебе друга, с которым будет комфортно делить квартиру и быт. 😊\n\n"
        "Чтобы начать, заполни анкету — это займёт всего пару минут! 📝\n"
        "Просто нажми /form или выбери пункт в меню."
#        "\n УБЕДИТЕЛЬНАЯ ПРОСЬБА ДЛЯ ТЕСТИРОВЩИКОВ \n НЕ ПИШИТЕ ПОЖАЛУЙСТА \n 🤖',' говно жопа пенис); DROP TABLE vibe_code; -- \n В КАКИЕ ЛИБО ПОЛЯ АНКЕТЫ \n ЭТА ХРЕНЬ ЛОЖИТ ВЕБХУК И Я НЕ МОГУ ЕЁ ПАРСИТЬ/ПЕРЕХВАТЫВАТЬ \n НОРМАЛЬНЫЕ ЛЮДИ ТАКОЙ ХУЙНЁЙ Не ЗАНИМАЮТСЯ"
    ),
    "nameMessage": (
        "📝 <b>Шаг 1 из 7:</b> Как тебя называть?\n\n"
        "✨ Меня зовут <b>Livether</b>. А ты? Под каким именем тебя будут видеть другие люди? "
        "Можешь указать имя, ник или даже прозвище — как тебе удобно! 😉"
    ),
    "ageMessage": (
        "📝 <b>Шаг 2 из 7:</b> Сколько тебе лет?\n\n"
        "🎂 А сколько тебе лет? Укажи цифру (например, 22)."
    ),
    "univerMessage": (
        "📝 <b>Шаг 3 из 7:</b> Где ты учишься? (учебное заведение)\n\n"
        "🎓 В каком вузе или колледже ты учишься? Напиши полное название или аббревиатуру."
    ),
    "aboutMessage": (
        "📝 <b>Шаг 4 из 7:</b> Расскажи о себе (что ищешь, чем увлекаешься)\n\n"
        "🧑‍💻 Расскажи о себе поподробнее! 👇\n"
        "- Чем ты увлекаешься?\n"
        "- Какой образ жизни ведёшь?\n"
        "- Есть ли особые привычки?\n"
        "- Что ты ищешь в квартире и соседе?\n\n"
        "Это поможет найти идеального соседа! 😊"
    ),
    "requirementsMessage": (
        "📝 <b>Шаг 5 из 7:</b> Каким ты хочешь видеть соседа? (пожелания)\n\n"
        "🧹 Теперь опиши, каким ты хотел(а) бы видеть своего соседа.\n\n"
        "Например:\n"
        "- Чистоплотность (важно / неважно)\n"
        "- Режим дня (тишина по ночам или можно шуметь)\n"
        "- Общительность (хочешь дружить или просто соседствовать)\n"
        "- Вредные привычки (курение, алкоголь)\n"
        "- Животные (можно/нельзя)\n\n"
        "Будь честен — это поможет найти лучшего друга по квартире! 🤝"
    ),
    "regionMessage": (
        "📝 <b>Шаг 6 из 7:</b> Выбери <b>регион</b>, где ищешь жильё 🗺️\n\n"
        "🌍 Чтобы мы могли найти соседей в твоём городе, нужно сначала выбрать <b>регион</b>.\n"
        "Нажми на кнопку ниже, чтобы выбрать область, край или республику. 👇"
    ),
    "cityMessage": (
        "📝 <b>Шаг 7 из 7:</b> Теперь выбери <b>город</b> в этом регионе 🌆\n\n"
        "🏙️ Отлично! Теперь выбери <b>город</b>, в котором ты хочешь снимать квартиру.\n"
        "Список городов появится ниже — просто нажми на нужный. 📍"
    ),
    "confirmMessage": (
        "✅ <b>Проверь свою анкету</b> — всё ли верно? Если есть ошибки, просто нажми «Заполнить заново».\n\n"
    ),
    "FormSaved": "🎉 <b>Анкета успешно сохранена!</b>\n\nТеперь ты можешь искать соседей через /find или в меню. Удачи в поиске! 🍀",
    "Menu": "🏠 <b>Главное меню</b>\n\nВыбери действие на клавиатуре ниже:",
    "RootCode": "🔐 Доступ к админ-панели открыт.",
    "FAQMessage": "❓ ЧаВо\n\nВ разработке...\n\nПо вопросам и предложениям: @tveetoo",
    "RulesMessage": (
        "📋 <b>Прежде чем начать</b>\n\n"
        "1️⃣ Запрещено указывать чужие персональные данные или выдавать себя за другого человека.\n"
        "2️⃣ Запрещено оскорблять, разжигать рознь по национальному, религиозному или иному признаку.\n"
        "3️⃣ Запрещено размещать рекламу, спам-ссылки или предлагать услуги, не связанные с поиском соседа.\n"
        "4️⃣ Запрещено использовать анкету для мошенничества (сбор денег, поддельные объявления о жилье и т.п.).\n"
        "5️⃣ Запрещено присылать оскорбительные или угрожающие сообщения другим пользователям после совпадения.\n"
        "6️⃣ Запрещено размещать материалы сексуального характера или содержащие насилие.\n"
        "7️⃣ Запрещено создавать несколько анкет от одного человека без цели поиска соседа.\n"
        "8️⃣ Не злоупотребляй кнопкой «⚠️ Пожаловаться» — репортить анкеты просто из вредности запрещено.\n\n"
        "9️⃣ Можно создавать анкету на несколько человек, если вы ищете ещё одного (или нескольких) соседей в уже снятую или планируемую квартиру.\n"
        "🔟 Можно редактировать анкету в любой момент через «👤 Моя анкета».\n"
        "1️⃣1️⃣ Пиши пожелания к соседу максимально конкретно — это увеличивает шанс на удачное совпадение.\n"
        "1️⃣2️⃣ Можно отказаться от совпадения и продолжить поиск в любой момент.\n"
        "1️⃣3️⃣ Анкету видят только пользователи из указанного тобой города.\n"
        "1️⃣4️⃣ После взаимного лайка обеим сторонам приходит уведомление с @username — дальше вы общаетесь напрямую в Telegram, без участия бота. <b>Важно:</b> соблюдай осторожность при общении с незнакомыми людьми, не передавай личную информацию и договаривайся о встречах в безопасных местах.\n"
        "1️⃣5️⃣ При накоплении жалоб анкета может быть скрыта, а пользователь забанен. Администратор также оставляет за собой право забанить без объяснения причин.\n"
        "1️⃣6️⃣ Бот не проверяет достоверность указанных данных — будьте внимательны при личной встрече.\n"
        "1️⃣7️⃣ Изменение города или анкеты может обновить список анкет, доступных для поиска.\n\n"
        "Нажми «Принимаю», чтобы продолжить заполнение анкеты."
    )
}

# ---------- Кнопки ----------
MainButtons = {
    "Profile": "👤 Моя анкета",
    "Find": "🔍 Найти сожителя",
    "Likes": "📬 Запросы на сожительство",
    "FAQ": "❓ ЧаВо",
}
FormButtons = {
    "Confirm": "Всё хорошо",
    "Restart": "Заполнить заново",
}
EditButtons = {
    "name": "Изменить имя",
    "age": "Изменить возраст",
    "univer": "Изменить учебное заведение",
    "about": "Изменить описание",
    "requirements": "Изменить пожелания",
    "city": "Изменить город",
}
ViewButtons = {
    "like": "👍",
    "dislike": "👎",
    "report": "⚠️ Пожаловаться"
}
ReturnButton = {
    "Return": "⬅️ Назад",
}

NextAction = {
    "name": "age",
    "age": "univer",
    "univer": "about",
    "about": "requirements",
    "requirements": "region",
    "region": "city",
    "city": "confirm",
}

CommandMenu = {
    "start": "Запустить бота",
    "profile": "Вывести анкету",
    "form": "Заполнить анкету",
    "menu": "Меню",
    "find": "Найти сожителя",
    "likes": "Запросы на сожительство",
    "faq": "ЧаВо"
}

# ---------- Регионы ----------
from regions import Regions
region_keys = list(Regions.keys())

# ---------- Reply Клавиатуры ----------
MainReplyKeyboardBuilder = ReplyKeyboardBuilder()
for text in MainButtons.values():
    MainReplyKeyboardBuilder.button(text=text)
MainReplyKeyboardBuilder.adjust(1, 2)
MainMenuKeyboard = MainReplyKeyboardBuilder.as_markup(resize_keyboard=True)

RulesButtons = {"Accept": "✅ Принимаю"}
RulesKeyboardBuilder = ReplyKeyboardBuilder()
RulesKeyboardBuilder.button(text=RulesButtons["Accept"])
RulesKeyboard = RulesKeyboardBuilder.as_markup(resize_keyboard=True, one_time_keyboard=True)

FormConfirmKeyboardBuilder = ReplyKeyboardBuilder()
for text in FormButtons.values():
    FormConfirmKeyboardBuilder.button(text=text)
FormConfirmKeyboardBuilder.adjust(1, 2)
FormConfirmKeyboard = FormConfirmKeyboardBuilder.as_markup(resize_keyboard=True, one_time_keyboard=True)

# ---------- Inline Клавиатуры ----------
RegionInlineKeyboardBuilder = InlineKeyboardBuilder()
for idx, region in enumerate(region_keys):
    RegionInlineKeyboardBuilder.button(text=region, callback_data=f"reg_{idx}")
RegionInlineKeyboardBuilder.adjust(1)
RegionInlineKeyboard = RegionInlineKeyboardBuilder.as_markup()

FormEditKeyboardBuilder = InlineKeyboardBuilder()
for key, label in EditButtons.items():
    FormEditKeyboardBuilder.button(text=label, callback_data=f"edit_{key}")
FormEditKeyboardBuilder.adjust(1, 2)
FormEditKeyboard = FormEditKeyboardBuilder.as_markup()

FormViewKeyboardBuilder = InlineKeyboardBuilder()
for key, label in ViewButtons.items():
    FormViewKeyboardBuilder.button(text=label, callback_data=f"view_{key}")
FormViewKeyboardBuilder.adjust(3)
FormViewKeyboard = FormViewKeyboardBuilder.as_markup()

Cities = {}
for region in region_keys:
    builder = InlineKeyboardBuilder()
    for city in Regions[region]:
        builder.button(text=city, callback_data=f"city_{city}")
    builder.adjust(1)
    Cities[region] = builder.as_markup()

# ---------- Валидация ----------
FieldLimits = {
    "name": (1, 50),
    "univer": (1, 100),
    "about": (1, 1000),
    "requirements": (1, 1000),
}
AGE_MIN, AGE_MAX = 16, 100

def validate_field(action: str, raw_text):
    if raw_text is None:
        return False, "Пожалуйста, отправь текстовое сообщение (не фото, не стикер и т.п.).", None
    text = raw_text.strip()
    if action == "age":
        try:
            age = int(text)
        except ValueError:
            return False, "Возраст должен быть числом, например: 22", None
        if age < AGE_MIN or age > AGE_MAX:
            return False, f"Укажи реальный возраст (от {AGE_MIN} до {AGE_MAX} лет).", None
        return True, None, age
    if action in FieldLimits:
        min_len, max_len = FieldLimits[action]
        if len(text) < min_len:
            return False, "Поле не может быть пустым.", None
        if len(text) > max_len:
            return False, f"Слишком длинно — не больше {max_len} символов (сейчас {len(text)}).", None
        if action in ("name", "univer"):
            if '\n' in text or '\r' in text or '\t' in text:
                return False, "Использование переноса строки и табуляции запрещено. Введите текст в одну строку.", None
        return True, None, text
    return True, None, text

# ---------- Функции БД ----------
def new_user_sync(user_id: int):
    supabase.table("users").upsert({"user_id": user_id}, on_conflict="user_id").execute()

async def set_string_field(user_id: int, field: str, value: str, table: str = "users", additional_field: str=None, additional_value=None):
    def _update():
        q = supabase.table(table).update({field: value}).eq("user_id", user_id)
        if additional_field and additional_value is not None:
            q = q.eq(additional_field, additional_value)
        return q.execute()
    await asyncio.to_thread(_update)

async def set_int_field(user_id: int, field: str, value: int, table: str = "users", additional_field: str=None, additional_value=None):
    def _update():
        q = supabase.table(table).update({field: value}).eq("user_id", user_id)
        if additional_field and additional_value is not None:
            q = q.eq(additional_field, additional_value)
        return q.execute()
    await asyncio.to_thread(_update)

async def get_field(user_id: int, field: str, table: str = "users", additional_field: str = None, additional_value=None):
    def _select():
        q = supabase.table(table).select(field).eq("user_id", user_id)
        if additional_field and additional_value is not None:
            q = q.eq(additional_field, additional_value)
        return q.execute()
    try:
        response = await asyncio.to_thread(_select)
        if response.data:
            return response.data[0][field]
        return None
    except Exception as e:
        logger.error("get_field(%s, %s) failed: %s", user_id, field, e)
        return None

async def get_user_sync(user_id: int):
    def _update():
        response = supabase.table("users").select("*").eq("user_id", user_id).execute()
        if response.data:
            return response.data[0]
        return None
    return await asyncio.to_thread(_update)

def delete_user_sync(user_id: int):
    # Удаляем все записи, где user_id = удаляемый (он смотрел других)
    supabase.table("views").delete().eq("user_id", user_id).execute()
    # Удаляем все записи, где viewed_user_id = удаляемый (его смотрели другие)
    supabase.table("views").delete().eq("viewed_user_id", user_id).execute()
    # Удаляем самого пользователя
    supabase.table("users").delete().eq("user_id", user_id).execute()

async def add_view(user_id: int, viewed_user_id: int, state: str = "unseen"):
    def _update():
        return supabase.table("views").upsert(
            {"user_id": user_id, "viewed_user_id": viewed_user_id, "state": state},
            on_conflict="user_id,viewed_user_id",
            ignore_duplicates=True,
        ).execute()
    await asyncio.to_thread(_update)

async def increment_views_count(user_id: int):
    def _sync():
        resp = supabase.table("users").select("views_count").eq("user_id", user_id).execute()
        if resp.data:
            current = resp.data[0].get("views_count") or 0
            new_count = current + 1
            supabase.table("users").update({"views_count": new_count}).eq("user_id", user_id).execute()
    await asyncio.to_thread(_sync)

async def get_unseen_form(user_id: int, city: str):
    def _sync():
        response = supabase.rpc("get_unseen_users", {"p_user_id": user_id, "p_city": city}).execute()
        return response.data
    candidates = await asyncio.to_thread(_sync)
    if not candidates:
        return None

    now = time.time()
    weights = []
    for u in candidates:
        last_active = u.get("last_active")
        if last_active:
            try:
                if isinstance(last_active, str):
                    dt = datetime.fromisoformat(last_active.replace('Z', '+00:00'))
                    last_ts = dt.timestamp()
                else:
                    last_ts = last_active.timestamp()
            except Exception:
                last_ts = 0
        else:
            last_ts = 0
        views = u.get("views_count") or 0
        days_since_active = (now - last_ts) / 86400
        weight = (days_since_active + 1) / (views + 1)
        weights.append(weight)

    selected = random.choices(candidates, weights=weights, k=1)[0]
    await add_view(user_id, selected["user_id"])
    await increment_views_count(selected["user_id"])
    await set_string_field(user_id, "last_active", datetime.now(timezone.utc).isoformat())
    return selected

# ---------- Основные функции бота ----------
async def form_question(message: types.Message):
    text = message.text
    user_id = message.from_user.id
    action = await get_field(user_id, "action")
    nextaction = NextAction.get(action)

    if nextaction is None:
        await message.answer("Что-то пошло не так. Отправь /form, чтобы начать заново.")
        return

    ok, error, value = validate_field(action, text)
    if not ok:
        await message.answer(f"⚠️ {error}")
        return

    if action == "age":
        await set_int_field(user_id, action, value)
    else:
        await set_string_field(user_id, action, value)

    reply = None
    if nextaction == "region":
        reply = RegionInlineKeyboard
    elif nextaction == "city":
        reply = Cities.get(await get_field(user_id, "region"))

    msg = Phrases.get(nextaction + "Message")
    if not msg:
        msg = f"Шаг {nextaction} (в разработке)"
    await message.answer(msg, reply_markup=reply, parse_mode="HTML")

    await set_string_field(user_id, "action", nextaction)

    if nextaction == "confirm":
        profile_text = await print_profile(user_id=user_id)
        if profile_text:
            await message.answer(profile_text, reply_markup=FormConfirmKeyboard, parse_mode="HTML")

async def form_edit(message: types.Message, action: str):
    user_id = message.from_user.id
    text = message.text
    ok, error, value = validate_field(action, text)
    if not ok:
        await message.answer(f"⚠️ {error}")
        return
    if action == "age":
        await set_int_field(user_id, action, value)
    else:
        await set_string_field(user_id, action, value)
    profile_text = await print_profile(user_id=user_id)
    if profile_text:
        await message.answer(profile_text, reply_markup=FormEditKeyboard, parse_mode="HTML")
    await set_string_field(user_id, "action", "None")

async def print_profile(user_id=None, data=None):
    if data is None:
        if user_id is None:
            return None
        data = await get_user_sync(user_id)
    if data:
        name = html.escape(str(data.get("name") or ""))
        age = data.get("age")
        univer = html.escape(str(data.get("univer") or ""))
        about = html.escape(str(data.get("about") or ""))
        requirements = html.escape(str(data.get("requirements") or ""))
        yearword = ""
        if age is None:
            age_display = ""
        else:
            age_display = age
            if age < 5:
                yearword = "года"
            elif age < 21:
                yearword = "лет"
            elif age % 10 == 1 and age % 100 != 11:
                yearword = "год"
            elif age % 10 in [2,3,4] and age % 100 not in [12,13,14]:
                yearword = "года"
            else:
                yearword = "лет"
        return (
            f"<b>{name}</b>, {age_display} {yearword} | {univer}\n\n"
            f"<b>О себе: </b>\n<i>{about}</i>\n\n"
            f"<b>Пожелания к соседу: </b>\n<i>{requirements}</i>\n\n"
        )
    return None

async def print_menu(message: types.Message):
    await set_string_field(message.from_user.id, "action", "None")
    await message.answer(Phrases["Menu"], reply_markup=MainMenuKeyboard, parse_mode="HTML")

async def start_form(message: types.Message, user_id: int):
    if await get_field(user_id, "form") != "true":
        await message.answer(Phrases["RulesMessage"], reply_markup=RulesKeyboard, parse_mode="HTML")
        await set_string_field(user_id, "action", "rules")
    else:
        await message.answer(Phrases['nameMessage'], parse_mode="HTML")
        await set_string_field(user_id, "action", "name")

async def set_commands(bot: Bot):
    commands = [BotCommand(command=cmd, description=desc) for cmd, desc in CommandMenu.items()]
    await bot.set_my_commands(commands)

# ---------- Команды ----------
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username
    await asyncio.to_thread(new_user_sync, user_id)
    # Сохраняем username только здесь
    if username:
        await set_string_field(user_id, "username", username)
    await set_string_field(user_id, "action", "None")
    await add_view(user_id, user_id, state="seen")
    await message.answer(Phrases['StartMessage'], parse_mode="HTML")

async def cmd_form(message: types.Message, user_id=None):
    if user_id is None:
        user_id = message.from_user.id
    await set_string_field(user_id, "action", "None")
    profile_text = await print_profile(user_id=user_id)
    if profile_text:
        await message.answer(profile_text, reply_markup=FormEditKeyboard, parse_mode="HTML")
    else:
        await message.answer("Профиль не существует")

async def cmd_menu(message: types.Message):
    await print_menu(message)

async def cmd_find(message: types.Message, user_id=None):
    if user_id is None:
        user_id = message.from_user.id
    city = await get_field(user_id, "city")
    if city is None:
        await message.answer("Вы не указали город поиска. Пожалуйста, заполните анкету.")
        return
    form = await get_unseen_form(user_id, city)
    if form is None:
        await message.answer("Нет доступных анкет для просмотра в вашем городе.")
        return
    profile_text = await print_profile(data=form)
    if profile_text:
        await message.answer(profile_text, parse_mode="HTML", reply_markup=FormViewKeyboard)
    else:
        await message.answer("Ошибка при получении профиля.")
    await set_string_field(user_id, "action", f"viewing_{form.get('user_id')}")

async def cmd_faq(message: types.Message):
    await message.answer(Phrases["FAQMessage"], parse_mode="HTML")

async def cmd_likes(message: types.Message, user_id=None):
    if user_id is None:
        user_id = message.from_user.id
    def _sync():
        return supabase.table("views").select("*").eq("viewed_user_id", user_id).eq("state", "like_unseen").execute().data
    likes = await asyncio.to_thread(_sync)
    if not likes:
        await message.answer("У вас нет новых лайков.")
        return
    liked_user_id = likes[0]["user_id"]
    form = await get_user_sync(liked_user_id)
    if form is None:
        await message.answer("Анкета этого пользователя больше недоступна.")
        return
    profile_text = await print_profile(data=form)
    if profile_text:
        await message.answer(profile_text, parse_mode="HTML", reply_markup=FormViewKeyboard)
    else:
        await message.answer("Ошибка при получении профиля.")
    await set_string_field(user_id, "action", f"likes_{liked_user_id}")

# ---------- Обработка сообщений ----------
async def text(message: types.Message):
    text = message.text
    user_id = message.from_user.id
    action = await get_field(user_id, "action")

    # 1. Обработка root-кода (админ)
    if text == ROOT_CODE and await get_field(user_id, "root") != "true":
        await set_string_field(user_id, "root", "true")
        await message.answer(Phrases["RootCode"], parse_mode="HTML")
        return

    # 2. Обработка кнопок главного меню и возврата (даже если action не None)
    if text == MainButtons["Profile"]:
        await set_string_field(user_id, "action", "None")
        await cmd_form(message, user_id=user_id)
        return
    if text == MainButtons["Find"]:
        await set_string_field(user_id, "action", "None")
        await cmd_find(message)
        return
    if text == MainButtons["Likes"]:
        await set_string_field(user_id, "action", "None")
        await cmd_likes(message)
        return
    if text == MainButtons["FAQ"]:
        await cmd_faq(message)
        return
    if text == ReturnButton["Return"]:
        await print_menu(message)
        return

    # 3. Обработка состояний (action)
    if action == "rules":
        if text == RulesButtons["Accept"]:
            await message.answer(Phrases['nameMessage'], parse_mode="HTML")
            await set_string_field(user_id, "action", "name")
        else:
            await message.answer("Пожалуйста, подтверди согласие с правилами, чтобы продолжить.", reply_markup=RulesKeyboard)
        return

    if action in Actions:
        if action == "confirm":
            if text == FormButtons["Restart"]:
                await set_string_field(user_id, "action", "None")
                await start_form(message, user_id)
            elif text == FormButtons["Confirm"]:
                await set_string_field(user_id, "form", "true")
                await set_string_field(user_id, "action", "None")
                await message.answer(Phrases["FormSaved"], parse_mode="HTML")
                await print_menu(message)
            else:
                await message.answer("Пожалуйста, используй кнопки ниже.", reply_markup=FormConfirmKeyboard)
            return
        await form_question(message)
        return

    if action in ActionEdit:
        await form_edit(message, action[:-4])
        return

    # Если ничего не подошло
    await message.answer("Я не понимаю эту команду. Используй кнопки меню или /help.")

# ---------- Админ-команды ----------
async def cmd(message: types.Message):
    text = message.text
    user_id = message.from_user.id
    if await get_field(user_id, "root") != "true":
        return

    if text.startswith("cmd_deleteform"):
        parts = text.split()
        if len(parts) == 2:
            try:
                target_id = int(parts[1])
            except ValueError:
                await message.answer("Неверный ID пользователя")
                return
        else:
            await message.answer("Формат: cmd_deleteform <user_id>")
            return
        await asyncio.to_thread(delete_user_sync, target_id)
        await message.answer(f"Анкета пользователя {target_id} удалена.")

    elif text == "cmd_cleardata":
        await set_string_field(user_id, "action", "confirm_cleardata")
        await message.answer(
            "⚠️ Это удалит ВСЕ данные из таблиц users и views без возможности восстановления.\n"
            "Для подтверждения отправьте: cmd_cleardata_confirm"
        )

    elif text == "cmd_cleardata_confirm":
        if await get_field(user_id, "action") != "confirm_cleardata":
            await message.answer("Сначала отправьте cmd_cleardata")
            return
        await asyncio.to_thread(clear_all_data_sync)
        await message.answer("✅ Все данные удалены. Отправьте /start и код root заново, чтобы продолжить как администратор.")

    elif text == "cmd_recreatedb":
        await set_string_field(user_id, "action", "confirm_recreatedb")
        await message.answer(
            "⚠️ Это ПОЛНОСТЬЮ удалит и заново создаст таблицы users, views и функцию get_unseen_users.\n"
            "Требуется, чтобы в Supabase уже была создана функция recreate_database.\n"
            "Для подтверждения отправьте: cmd_recreatedb_confirm"
        )

    elif text == "cmd_recreatedb_confirm":
        if await get_field(user_id, "action") != "confirm_recreatedb":
            await message.answer("Сначала отправьте cmd_recreatedb")
            return
        try:
            await asyncio.to_thread(recreate_database_sync)
            await message.answer("✅ База данных пересоздана.")
        except Exception as e:
            await message.answer(f"❌ Ошибка при пересоздании БД: {e}")

    elif text == "cmd_selftest":
        await message.answer("⏳ Запускаю диагностику...")
        report = await run_diagnostics()
        await message.answer(report)

    else:
        await message.answer("Неизвестная админ-команда.")

# ---------- Диагностика ----------
async def run_diagnostics() -> str:
    results = []
    try:
        resp = await asyncio.to_thread(lambda: supabase.table("users").select("count", count="exact").limit(1).execute())
        results.append("✅ БД доступна")
    except Exception as e:
        results.append(f"❌ Ошибка БД: {e}")

    try:
        me = await bot.get_me()
        results.append(f"✅ Бот @{me.username} активен")
    except Exception as e:
        results.append(f"❌ Ошибка бота: {e}")

    return f"🔧 Диагностика {BOT_NAME}\n\n" + "\n".join(results)

def clear_all_data_sync():
    supabase.table("views").delete().neq("user_id", -1).execute()
    supabase.table("users").delete().neq("user_id", -1).execute()

def recreate_database_sync():
    return supabase.rpc("recreate_database").execute()

# ---------- Обработчики диспетчера ----------
@dp.message()
async def message(message: types.Message):
    mtext = message.text
    username = message.from_user.username
    if not username:
        await message.answer("Чтобы пользоваться ботом установите имя пользователя в настройках Telegram")
        return
    if mtext and mtext[0] == "/":
        if mtext == "/start": await cmd_start(message)
        elif mtext == "/form": await start_form(message, message.from_user.id)
        elif mtext == "/profile": await cmd_form(message)
        elif mtext == "/menu": await cmd_menu(message)
        elif mtext == "/find": await cmd_find(message)
        elif mtext == "/faq": await cmd_faq(message)
        elif mtext == "/likes": await cmd_likes(message)
        else:
            await message.answer("Неизвестная команда. Используй /help.")
        return
    if mtext and mtext[:4] == "cmd_":
        await cmd(message)
        return
    await text(message)

@dp.callback_query()
async def callback_query(callback: CallbackQuery):
    data = callback.data
    user_id = callback.from_user.id

    form = await get_field(user_id, "form")

    if data.startswith("reg_"):
        try:
            region_idx = int(data.split("_")[1])
            region_name = region_keys[region_idx]
        except (IndexError, ValueError):
            await callback.answer("Некорректный выбор региона.")
            return
        await set_string_field(user_id, "region", region_name)
        if await get_field(user_id, "action") != "regionEdit":
            await set_string_field(user_id, "action", "city")
        else:
            await set_string_field(user_id, "action", "cityEdit")
        await callback.answer()
        await callback.message.answer(Phrases["cityMessage"], reply_markup=Cities[region_name], parse_mode="HTML")

    elif data.startswith("city_"):
        city_name = data[5:]
        await set_string_field(user_id, "city", city_name)
        if await get_field(user_id, "action") == "cityEdit":
            await callback.answer()
            await cmd_form(callback.message, user_id=user_id)
            return
        await set_string_field(user_id, "action", "confirm")
        await callback.answer()
        profile_text = await print_profile(user_id=user_id)
        if profile_text:
            await callback.message.answer(Phrases["confirmMessage"] + "\n" + profile_text, reply_markup=FormConfirmKeyboard, parse_mode="HTML")

    elif data.startswith("edit_"):
        action = data[5:]
        if action not in EditButtons:
            await callback.answer("Неизвестное действие.")
            return
        reply = None
        if action == "city":
            reply = RegionInlineKeyboard
            action = "region"
        await set_string_field(user_id, "action", action+"Edit")
        await callback.message.answer(Phrases[action+"Message"], reply_markup=reply, parse_mode="HTML")
        await callback.answer()

    elif data.startswith("view_"):
        reaction = data[5:]
        action_value = await get_field(user_id, "action")
        if not action_value:
            await callback.answer("Действие устарело, начните заново.")
            return

        if action_value.startswith("likes"):
            try:
                liked_user_id = int(action_value.split("_")[1])
            except (IndexError, ValueError):
                await callback.answer("Действие устарело.")
                await set_string_field(user_id, "action", "None")
                return
            if reaction == "like":
                liker_username = await get_field(user_id, "username")
                liked_username = await get_field(liked_user_id, "username")
                liker_name = f"@{liker_username}" if liker_username else "пользователь без username"
                liked_name = f"@{liked_username}" if liked_username else "пользователь без username"
                await bot.send_message(liked_user_id, f"Совпадение с {liker_name}! Свяжитесь чтобы обсудить сожительство!")
                await bot.send_message(user_id, f"Совпадение с {liked_name}! Свяжитесь чтобы обсудить сожительство!")
            elif reaction == "report":
                current_reports = await get_field(liked_user_id, "reports") or 0
                await set_int_field(liked_user_id, "reports", current_reports + 1)
            await set_string_field(liked_user_id, "state", "seen", table="views", additional_field="viewed_user_id", additional_value=user_id)
            await set_string_field(user_id, "state", "seen", table="views", additional_field="viewed_user_id", additional_value=liked_user_id)
            await callback.answer()
            if reaction == "dislike":
                await cmd_likes(callback.message, user_id=user_id)
            return

        elif action_value.startswith("viewing"):
            try:
                viewed_id = int(action_value.split("_")[1])
            except (IndexError, ValueError):
                await callback.answer("Действие устарело.")
                await set_string_field(user_id, "action", "None")
                return
            if reaction == "like":
                mutual_state = await get_field(viewed_id, "state", table="views", additional_field="viewed_user_id", additional_value=user_id)
                if mutual_state == "like_unseen":
                    liker_username = await get_field(user_id, "username")
                    liked_username = await get_field(viewed_id, "username")
                    liker_name = f"@{liker_username}" if liker_username else "пользователь без username"
                    liked_name = f"@{liked_username}" if liked_username else "пользователь без username"
                    await bot.send_message(viewed_id, f"Совпадение с {liker_name}! Свяжитесь чтобы обсудить сожительство!")
                    await bot.send_message(user_id, f"Совпадение с {liked_name}! Свяжитесь чтобы обсудить сожительство!")
                    await set_string_field(viewed_id, "state", "seen", table="views", additional_field="viewed_user_id", additional_value=user_id)
                    await set_string_field(user_id, "state", "seen", table="views", additional_field="viewed_user_id", additional_value=viewed_id)
                else:
                    await set_string_field(user_id, "state", "like_unseen", table="views", additional_field="viewed_user_id", additional_value=viewed_id)
            elif reaction == "dislike":
                await set_string_field(user_id, "state", "seen", table="views", additional_field="viewed_user_id", additional_value=viewed_id)
            elif reaction == "report":
                current_reports = await get_field(viewed_id, "reports") or 0
                await set_int_field(viewed_id, "reports", current_reports + 1)
                await set_string_field(user_id, "state", "seen", table="views", additional_field="viewed_user_id", additional_value=viewed_id)
            await callback.answer()
            await set_string_field(user_id, "action", "None")
            await cmd_find(callback.message, user_id=user_id)
        else:
            await callback.answer("Действие устарело, начните заново.")
            await set_string_field(user_id, "action", "None")
    else:
        await callback.answer()
        await bot.send_message(user_id, data)

# ---------- ВЕБ-СЕРВЕР С СТАТИСТИКОЙ И ПАНЕЛЬЮ УПРАВЛЕНИЯ ----------
async def stats(request):
    """Эндпоинт для публичной статистики с фильтром по периоду."""
    period = request.query.get('period', 'all')
    now = datetime.now()
    since = None
    if period == 'day':
        since = now - timedelta(days=1)
    elif period == 'week':
        since = now - timedelta(days=7)
    elif period == 'month':
        since = now - timedelta(days=30)

    def _get_stats():
        users_query = supabase.table("users").select("user_id", count="exact")
        forms_query = supabase.table("users").select("user_id", count="exact").eq("form", "true")
        views_query = supabase.table("views").select("user_id", count="exact")
        likes_query = supabase.table("views").select("user_id", count="exact").eq("state", "like_unseen")
        cities_query = supabase.table("users").select("city").eq("form", "true")

        if since:
            users_query = users_query.gte("created_at", since.isoformat())
            forms_query = forms_query.gte("created_at", since.isoformat())
            views_query = views_query.gte("created_at", since.isoformat())
            likes_query = likes_query.gte("created_at", since.isoformat())
            cities_query = cities_query.gte("created_at", since.isoformat())

        total_users = users_query.execute().count
        filled_forms = forms_query.execute().count
        total_views = views_query.execute().count
        total_likes = likes_query.execute().count
        city_data = cities_query.execute().data
        city_counter = Counter(row["city"] for row in city_data if row.get("city"))
        top_cities = city_counter.most_common(5)

        return {
            "total_users": total_users,
            "filled_forms": filled_forms,
            "total_views": total_views,
            "total_likes": total_likes,
            "top_cities": top_cities,
        }

    try:
        stats_data = await asyncio.to_thread(_get_stats)
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        return web.Response(text="Ошибка получения данных", status=500)

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>📊 Статистика Livether</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 700px; margin: 30px auto; padding: 20px; background: #f0f2f5; color: #1a1a2e; }}
            h1 {{ text-align: center; font-size: 28px; color: #16213e; }}
            .period-buttons {{ display: flex; gap: 10px; justify-content: center; margin-bottom: 20px; }}
            .period-buttons a {{ background: #e0e0e0; padding: 8px 16px; border-radius: 20px; text-decoration: none; color: #333; font-weight: 500; }}
            .period-buttons a.active {{ background: #0f3460; color: white; }}
            .card {{ background: white; padding: 15px 25px; margin: 15px 0; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); display: flex; justify-content: space-between; align-items: center; }}
            .card .label {{ font-weight: 500; color: #555; }}
            .card .value {{ font-size: 26px; font-weight: bold; color: #0f3460; }}
            .city-list {{ list-style: none; padding: 0; margin: 5px 0; }}
            .city-list li {{ display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #eee; }}
            .badge {{ background: #e94560; color: white; padding: 4px 10px; border-radius: 20px; font-size: 14px; }}
            .footer {{ text-align: center; color: #888; font-size: 14px; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <h1>📊 Статистика Livether</h1>
        <div class="period-buttons">
            <a href="?period=all" class="{'active' if period=='all' else ''}">Всё время</a>
            <a href="?period=day" class="{'active' if period=='day' else ''}">День</a>
            <a href="?period=week" class="{'active' if period=='week' else ''}">Неделя</a>
            <a href="?period=month" class="{'active' if period=='month' else ''}">Месяц</a>
        </div>
        <div class="card"><span class="label">👥 Всего пользователей</span><span class="value">{stats_data['total_users']}</span></div>
        <div class="card"><span class="label">✅ Заполненных анкет</span><span class="value">{stats_data['filled_forms']}</span></div>
        <div class="card"><span class="label">👁️ Всего просмотров</span><span class="value">{stats_data['total_views']}</span></div>
        <div class="card"><span class="label">❤️ Лайков</span><span class="value">{stats_data['total_likes']}</span></div>
        <div class="card" style="flex-direction:column; align-items:stretch;">
            <span class="label" style="margin-bottom:10px;">🏙️ Топ-5 городов</span>
            <ul class="city-list">
                {"".join(f"<li><span>{city}</span><span class='badge'>{count}</span></li>" for city, count in stats_data['top_cities'])}
            </ul>
        </div>
        <div class="footer"><p>🔄 Обновлено: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p></div>
    </body>
    </html>
    """
    return web.Response(text=html_content, content_type='text/html')

# ---------- Панель управления администратора ----------
COOKIE_NAME = "admin_session"
COOKIE_MAX_AGE = 86400 * 7  # 7 дней

def set_admin_cookie(response, value):
    response.set_cookie(COOKIE_NAME, value, max_age=COOKIE_MAX_AGE, httponly=True, secure=True, path='/')

def is_admin(request):
    cookie_val = request.cookies.get(COOKIE_NAME)
    if cookie_val:
        expected = hashlib.sha256((ROOT_CODE + "_salt").encode()).hexdigest()
        return cookie_val == expected
    return False

async def admin_login(request):
    if request.method == "POST":
        data = await request.post()
        code = data.get("code")
        if code == ROOT_CODE:
            resp = web.HTTPFound("/admin/users")
            set_admin_cookie(resp, hashlib.sha256((ROOT_CODE + "_salt").encode()).hexdigest())
            return resp
        else:
            return web.Response(text="Неверный код", status=403)

    html_content = """
    <!DOCTYPE html>
    <html><head><meta charset="utf-8"><title>Вход в админку</title>
    <style>body{font-family:sans-serif;max-width:400px;margin:40px auto;padding:20px;background:#f0f2f5;}
    input,button{display:block;width:100%;padding:12px;margin:10px 0;border-radius:8px;border:1px solid #ccc;font-size:16px;}
    button{background:#0f3460;color:white;border:none;cursor:pointer;}</style>
    </head><body>
    <h2>Вход в панель управления</h2>
    <form method="POST">
        <input type="password" name="code" placeholder="Введите ROOT_CODE" required>
        <button type="submit">Войти</button>
    </form>
    </body></html>
    """
    return web.Response(text=html_content, content_type='text/html')

async def admin_users(request):
    if not is_admin(request):
        return web.HTTPFound("/admin")
    page = int(request.query.get('page', 1))
    per_page = 20
    offset = (page - 1) * per_page
    def _list():
        resp = supabase.table("users").select("*").order("user_id").range(offset, offset + per_page - 1).execute()
        return resp.data
    users = await asyncio.to_thread(_list)

    rows = ""
    for u in users:
        rows += f"""
        <tr>
            <td>{u['user_id']}</td>
            <td>@{u.get('username', '-')}</td>
            <td>{html.escape(u.get('name') or '')}</td>
            <td>{u.get('age', '')}</td>
            <td>{html.escape(u.get('city') or '')}</td>
            <td>{u.get('form') == 'true' and '✅' or '❌'}</td>
            <td>{u.get('reports', 0)}</td>
            <td>{u.get('views_count', 0)}</td>
            <td>{u.get('banned') and '🚫' or ''}</td>
            <td>
                <form style="display:inline" method="POST" action="/admin/delete/{u['user_id']}" onsubmit="return confirm('Удалить анкету?')">
                    <button type="submit">🗑️</button>
                </form>
                <form style="display:inline" method="POST" action="/admin/ban/{u['user_id']}">
                    <button type="submit">{"🚫" if not u.get('banned') else "✅"}</button>
                </form>
            </td>
        </tr>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html><head><meta charset="utf-8"><title>Пользователи</title>
    <style>
        body{{font-family:sans-serif;max-width:1200px;margin:20px auto;padding:20px;background:#f0f2f5;}}
        table{{width:100%;border-collapse:collapse;background:white;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.1);}}
        th,td{{padding:10px;text-align:left;border-bottom:1px solid #eee;}}
        th{{background:#0f3460;color:white;}}
        .nav{{display:flex;gap:10px;margin-top:20px;}}
        .nav a{{background:#0f3460;color:white;padding:8px 16px;border-radius:8px;text-decoration:none;}}
        .logout{{float:right;}}
    </style>
    </head><body>
        <h1>👥 Пользователи <span class="logout"><a href="/admin/logout">Выйти</a></span></h1>
        <table>
            <tr><th>ID</th><th>Username</th><th>Имя</th><th>Возраст</th><th>Город</th><th>Анкета</th><th>Жалобы</th><th>Просмотры</th><th>Бан</th><th>Действия</th></tr>
            {rows}
        </table>
        <div class="nav">
            <a href="?page={page-1 if page>1 else 1}">◀ Назад</a>
            <a href="?page={page+1}">Вперёд ▶</a>
        </div>
        <p><a href="/admin/stats">📊 Расширенная статистика</a></p>
    </body></html>
    """
    return web.Response(text=html_content, content_type='text/html')

async def admin_delete(request):
    if not is_admin(request):
        return web.HTTPFound("/admin")
    user_id = int(request.match_info['user_id'])
    await asyncio.to_thread(delete_user_sync, user_id)
    return web.HTTPFound("/admin/users")

async def admin_ban(request):
    if not is_admin(request):
        return web.HTTPFound("/admin")
    user_id = int(request.match_info['user_id'])
    def _get():
        resp = supabase.table("users").select("banned").eq("user_id", user_id).execute()
        return resp.data[0]["banned"] if resp.data else None
    current = await asyncio.to_thread(_get)
    new_val = not current if current is not None else True
    await set_string_field(user_id, "banned", str(new_val).lower() if new_val else "false")
    return web.HTTPFound("/admin/users")

async def admin_stats(request):
    if not is_admin(request):
        return web.HTTPFound("/admin")
    def _stats():
        total_users = supabase.table("users").select("user_id", count="exact").execute().count
        banned_users = supabase.table("users").select("user_id", count="exact").eq("banned", "true").execute().count
        reports_gt5 = supabase.table("users").select("user_id", count="exact").gt("reports", 5).execute().count
        views_total = supabase.table("views").select("user_id", count="exact").execute().count
        likes_total = supabase.table("views").select("user_id", count="exact").eq("state", "like_unseen").execute().count
        return {
            "total": total_users,
            "banned": banned_users,
            "reports_gt5": reports_gt5,
            "views": views_total,
            "likes": likes_total,
        }
    data = await asyncio.to_thread(_stats)

    html_content = f"""
    <!DOCTYPE html>
    <html><head><meta charset="utf-8"><title>Админ-статистика</title>
    <style>body{{font-family:sans-serif;max-width:600px;margin:40px auto;padding:20px;background:#f0f2f5;}}
    .card{{background:white;padding:15px;margin:10px 0;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,0.1);display:flex;justify-content:space-between;}}
    .value{{font-size:24px;font-weight:bold;color:#0f3460;}}
    </style>
    </head><body>
        <h1>📊 Расширенная статистика</h1>
        <div class="card"><span>👥 Всего пользователей</span><span class="value">{data['total']}</span></div>
        <div class="card"><span>🚫 Забаненных</span><span class="value">{data['banned']}</span></div>
        <div class="card"><span>⚠️ Жалоб >5</span><span class="value">{data['reports_gt5']}</span></div>
        <div class="card"><span>👁️ Всего просмотров</span><span class="value">{data['views']}</span></div>
        <div class="card"><span>❤️ Лайков</span><span class="value">{data['likes']}</span></div>
        <p><a href="/admin/users">← Назад к пользователям</a></p>
    </body></html>
    """
    return web.Response(text=html_content, content_type='text/html')

async def admin_logout(request):
    resp = web.HTTPFound("/admin")
    resp.del_cookie(COOKIE_NAME)
    return resp

async def webhook_refresher():
    """Фоновый процесс, переустанавливающий вебхук каждые 10 минут."""
    while True:
        await asyncio.sleep(600)  # 10 минут
        try:
            await bot.set_webhook(WEBHOOK_URL, allowed_updates=dp.resolve_used_update_types())
            logger.info("✅ Вебхук переустановлен")
        except Exception as e:
            logger.error(f"❌ Ошибка при переустановке вебхука: {e}")

# ---------- Веб-сервер ----------
async def on_startup(app: web.Application):
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL, allowed_updates=dp.resolve_used_update_types())
    logger.info(f"Вебхук установлен на {WEBHOOK_URL}")
    await set_commands(bot)
    asyncio.create_task(webhook_refresher())

def create_app():
    app = web.Application()
    app.router.add_get("/", lambda request: web.Response(text="OK"))
    app.router.add_get("/health", lambda request: web.Response(text="OK"))
    app.router.add_get("/stats", stats)
    app.router.add_get("/admin", admin_login)
    app.router.add_post("/admin", admin_login)
    app.router.add_get("/admin/users", admin_users)
    app.router.add_post("/admin/delete/{user_id}", admin_delete)
    app.router.add_post("/admin/ban/{user_id}", admin_ban)
    app.router.add_get("/admin/stats", admin_stats)
    app.router.add_get("/admin/logout", admin_logout)
    # webhook
    from aiogram.webhook import aiohttp_server
    webhook_requests = aiohttp_server.SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_requests.register(app, path="/webhook")
    app.on_startup.append(on_startup)
    return app

# ---------- Точка входа ----------
if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", 5000))
    web.run_app(app, host="0.0.0.0", port=port)