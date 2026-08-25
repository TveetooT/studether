import os
import logging
import asyncio
import time
import html
import random
from datetime import datetime, timezone
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.types import (
    ErrorEvent,
    BotCommand,
    CallbackQuery,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from supabase import create_client

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

# ---------- Бот и диспетчер ----------
bot = Bot(token=TOKEN)
dp = Dispatcher()

# ---------- Подключение к БД ----------
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------- Константы ----------
BOT_NAME = "Livether"
DIAG_TEST_ID = -999999

# ---------- Списки ----------
Actions = [
    "name", "age", "univer", "about", "requirements", "confirm"
]
ActionEdit = [
    "nameEdit", "ageEdit", "univerEdit", "aboutEdit", "requirementsEdit",
]

# ---------- Словари ----------
Phrases = {
    "StartMessage": (
        "👋 Привет! Я бот <b>Livether</b> — твой помощник в поиске идеального соседа для совместной аренды! 🏠\n\n"
        "Мы подберём тебе друга, с которым будет комфортно делить квартиру и быт. 😊\n\n"
        "Чтобы начать, заполни анкету — это займёт всего пару минут! 📝\n"
        "Просто нажми /form или выбери пункт в меню."
    ),
    "nameMessage1": "📝 <b>Шаг 1 из 7:</b> Как тебя называть?",
    "ageMessage1": "📝 <b>Шаг 2 из 7:</b> Сколько тебе лет?",
    "univerMessage1": "📝 <b>Шаг 3 из 7:</b> Где ты учишься? (учебное заведение)",
    "aboutMessage1": "📝 <b>Шаг 4 из 7:</b> Расскажи о себе (что ищешь, чем увлекаешься)",
    "requirementsMessage1": "📝 <b>Шаг 5 из 7:</b> Каким ты хочешь видеть соседа? (пожелания)",
    "regionMessage1": "📝 <b>Шаг 6 из 7:</b> Выбери <b>регион</b>, где ищешь жильё 🗺️",
    "cityMessage1": "📝 <b>Шаг 7 из 7:</b> Теперь выбери <b>город</b> в этом регионе 🌆",
    "nameMessage2": (
        "✨ Меня зовут <b>Livether</b>. А ты? Под каким именем тебя будут видеть другие люди? "
        "Можешь указать имя, ник или даже прозвище — как тебе удобно! 😉"
    ),
    "ageMessage2": "🎂 А сколько тебе лет? Укажи цифру (например, 22).",
    "univerMessage2": "🎓 В каком вузе или колледже ты учишься? Напиши полное название или аббревиатуру.",
    "aboutMessage2": (
        "🧑‍💻 Расскажи о себе поподробнее! 👇\n"
        "- Чем ты увлекаешься?\n"
        "- Какой образ жизни ведёшь?\n"
        "- Есть ли особые привычки?\n"
        "- Что ты ищешь в квартире и соседе?\n\n"
        "Это поможет найти идеального соседа! 😊"
    ),
    "requirementsMessage2": (
        "🧹 Теперь опиши, каким ты хотел(а) бы видеть своего соседа.\n\n"
        "Например:\n"
        "- Чистоплотность (важно / неважно)\n"
        "- Режим дня (тишина по ночам или можно шуметь)\n"
        "- Общительность (хочешь дружить или просто соседствовать)\n"
        "- Вредные привычки (курение, алкоголь)\n"
        "- Животные (можно/нельзя)\n\n"
        "Будь честен — это поможет найти лучшего друга по квартире! 🤝"
    ),
    "regionMessage2": (
        "🌍 Чтобы мы могли найти соседей в твоём городе, нужно сначала выбрать <b>регион</b>.\n"
        "Нажми на кнопку ниже, чтобы выбрать область, край или республику. 👇"
    ),
    "cityMessage2": (
        "🏙️ Отлично! Теперь выбери <b>город</b>, в котором ты хочешь снимать квартиру.\n"
        "Список городов появится ниже — просто нажми на нужный. 📍"
    ),
    "confirmMessage": "✅ <b>Проверь свою анкету</b> — всё ли верно? Если есть ошибки, просто нажми «Заполнить заново».\n\n",
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
    if await get_field(user_id, "form") != "true":
        await message.answer(Phrases[nextaction+"Message2"], parse_mode="HTML")
    await message.answer(Phrases[nextaction+"Message1"], reply_markup=reply, parse_mode="HTML")
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
        await message.answer(Phrases['nameMessage1'], parse_mode="HTML")
        await set_string_field(user_id, "action", "name")

async def set_commands(bot: Bot):
    commands = [BotCommand(command=cmd, description=desc) for cmd, desc in CommandMenu.items()]
    await bot.set_my_commands(commands)

# ---------- Команды ----------
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username
    await asyncio.to_thread(new_user_sync, user_id)
    await set_string_field(user_id, "username", username)
    await set_string_field(user_id, "action", "None")
    await add_view(user_id, user_id, state="seen")
    await message.answer(Phrases['StartMessage'], parse_mode="HTML")

async def cmd_form(message: types.Message, user_id=None):
    await set_string_field(message.from_user.id, "username", message.from_user.username)
    if user_id is None:
        user_id = message.from_user.id
    await set_string_field(user_id, "action", "None")
    profile_text = await print_profile(user_id=user_id)
    if profile_text:
        await message.answer(profile_text, reply_markup=FormEditKeyboard, parse_mode="HTML")
    else:
        await message.answer("Профиль не существует")

async def cmd_menu(message: types.Message):
    await set_string_field(message.from_user.id, "username", message.from_user.username)
    await print_menu(message)

async def cmd_find(message: types.Message, user_id=None):
    if user_id is None:
        user_id = message.from_user.id
    await set_string_field(user_id, "username", message.from_user.username)
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
            await message.answer(Phrases['nameMessage1'], parse_mode="HTML")
            await message.answer(Phrases['nameMessage2'], parse_mode="HTML")
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
        me = await bot.get_me()
        results.append(f"✅ Telegram API: бот @{me.username} на связи")
    except Exception as e:
        results.append(f"❌ Telegram API: {e}")

    try:
        await asyncio.to_thread(lambda: supabase.table("users").select("user_id").limit(1).execute())
        results.append("✅ Чтение из таблицы users")
    except Exception as e:
        results.append(f"❌ Чтение из таблицы users: {e}")

    try:
        await asyncio.to_thread(lambda: supabase.table("views").select("user_id").limit(1).execute())
        results.append("✅ Чтение из таблицы views")
    except Exception as e:
        results.append(f"❌ Чтение из таблицы views: {e}")

    try:
        await asyncio.to_thread(lambda: supabase.rpc(
            "get_unseen_users", {"p_user_id": DIAG_TEST_ID, "p_city": "__diag__"}
        ).execute())
        results.append("✅ Функция get_unseen_users отвечает")
    except Exception as e:
        results.append(f"❌ Функция get_unseen_users: {e}")

    try:
        await asyncio.to_thread(new_user_sync, DIAG_TEST_ID)
        await set_string_field(DIAG_TEST_ID, "action", "diag")
        value = await get_field(DIAG_TEST_ID, "action")
        if value == "diag":
            results.append("✅ Запись/чтение полей users (set_string_field/get_field)")
        else:
            results.append(f"❌ Запись/чтение полей users: ожидалось 'diag', получено {value!r}")
    except Exception as e:
        results.append(f"❌ Запись/чтение полей users: {e}")

    try:
        await add_view(DIAG_TEST_ID, DIAG_TEST_ID, state="unseen")
        state = await get_field(DIAG_TEST_ID, "state", table="views", additional_field="viewed_user_id", additional_value=DIAG_TEST_ID)
        if state == "unseen":
            results.append("✅ Запись/чтение таблицы views (add_view)")
        else:
            results.append(f"❌ Запись/чтение таблицы views: ожидалось 'unseen', получено {state!r}")
    except Exception as e:
        results.append(f"❌ Запись/чтение таблицы views: {e}")

    try:
        await asyncio.to_thread(lambda: supabase.table("views").delete().eq("user_id", DIAG_TEST_ID).execute())
        await asyncio.to_thread(delete_user_sync, DIAG_TEST_ID)
        results.append("✅ Очистка тестовых данных")
    except Exception as e:
        results.append(f"❌ Очистка тестовых данных: {e}")

    try:
        await set_string_field(DIAG_TEST_ID, "city", "Москва")
        await set_string_field(DIAG_TEST_ID, "form", "true")
        start = time.time()
        await asyncio.to_thread(lambda: supabase.table("users").select("*").limit(10).execute())
        elapsed = time.time() - start
        results.append(f"⏱️ SELECT * FROM users LIMIT 10: {elapsed:.3f} сек")
    except Exception as e:
        results.append(f"❌ SELECT * FROM users LIMIT 10: {e}")

    try:
        start = time.time()
        await asyncio.to_thread(lambda: supabase.rpc(
            "get_unseen_users", {"p_user_id": DIAG_TEST_ID, "p_city": "Москва"}
        ).execute())
        elapsed = time.time() - start
        results.append(f"⏱️ Вызов get_unseen_users (Москва): {elapsed:.3f} сек")
    except Exception as e:
        results.append(f"❌ get_unseen_users (Москва): {e}")

    try:
        start = time.time()
        await asyncio.to_thread(lambda: supabase.table("views").select("*").limit(10).execute())
        elapsed = time.time() - start
        results.append(f"⏱️ SELECT * FROM views LIMIT 10: {elapsed:.3f} сек")
    except Exception as e:
        results.append(f"❌ SELECT * FROM views LIMIT 10: {e}")

    try:
        await asyncio.to_thread(lambda: supabase.table("views").delete().eq("user_id", DIAG_TEST_ID).execute())
        await asyncio.to_thread(delete_user_sync, DIAG_TEST_ID)
        results.append("✅ Очистка тестовых данных")
    except Exception as e:
        results.append(f"❌ Очистка тестовых данных: {e}")

    try:
        def _many_queries():
            for _ in range(100):
                supabase.table("users").select("user_id").limit(1).execute()
        start = time.time()
        await asyncio.to_thread(_many_queries)
        elapsed = time.time() - start
        results.append(f"⏱️ 100 запросов SELECT user_id LIMIT 1: {elapsed:.3f} сек (в среднем {elapsed/100:.3f} сек/запрос)")
    except Exception as e:
        results.append(f"❌ 100 запросов SELECT: {e}")

    try:
        def _many_rpc():
            for _ in range(100):
                supabase.rpc("get_unseen_users", {"p_user_id": DIAG_TEST_ID, "p_city": "Москва"}).execute()
        start = time.time()
        await asyncio.to_thread(_many_rpc)
        elapsed = time.time() - start
        results.append(f"⏱️ 100 вызовов RPC get_unseen_users: {elapsed:.3f} сек (в среднем {elapsed/100:.3f} сек/вызов)")
    except Exception as e:
        results.append(f"❌ 100 вызовов RPC: {e}")

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
    await set_string_field(user_id, "username", callback.from_user.username)
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
        if form != "true":
            await callback.message.answer(Phrases["cityMessage2"], parse_mode="HTML")
        await callback.message.answer(Phrases["cityMessage1"], reply_markup=Cities[region_name], parse_mode="HTML")

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
        await callback.message.answer(Phrases[action+"Message1"], reply_markup=reply, parse_mode="HTML")
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

# ---------- Веб-сервер ----------
async def on_startup(app: web.Application):
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL, allowed_updates=dp.resolve_used_update_types())
    logger.info(f"Вебхук установлен на {WEBHOOK_URL}")
    await set_commands(bot)

def create_app():
    app = web.Application()
    app.router.add_get("/", lambda request: web.Response(text="OK"))
    app.router.add_get("/health", lambda request: web.Response(text="OK"))
    from aiogram.webhook import aiohttp_server
    webhook_requests = aiohttp_server.SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    webhook_requests.register(app, path="/webhook")
    app.on_startup.append(on_startup)
    return app

# ---------- Точка входа ----------
if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", 5000))
    web.run_app(app, host="0.0.0.0", port=port)