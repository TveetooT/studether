import os
import logging
import asyncio
import time
import html
import random
from datetime import datetime, timezone
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

ROOT_CODE = os.environ.get("ROOT_CODE")
# ---------- Подключение к БД ----------
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------- Константы ----------
BOT_NAME = "Livether"
DIAG_TEST_ID = -999999  # служебный ID для self-test, Telegram user_id всегда положительные

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

    "FAQMessage": 
        "❓ ЧаВо\n\n"
        "В разработке...\n\n"
        "По вопросам и предложениям: @tveetoo",

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
        "1️⃣7️⃣ Изменение города или анкеты может обновить список анкет, доступных для поиска.\n"
        "1️⃣8️⃣ Ты можешь использовать HTML-разметку для оформления текста анкеты: "
        "<b>жирный</b>, <i>курсив</i>, <a href=\"https://example.com\">ссылки</a> и другие теги. "
        "Это поможет сделать твою анкету более выразительной!\n\n"
        "Нажми «Принимаю», чтобы продолжить заполнение анкеты."
    )
}

# ---------- Кнопки ----------
# ---------- главное меню ----------
MainButtons = {
    "Profile": "👤 Моя анкета",
    "Find": "🔍 Найти сожителя",
    "Likes": "📬 Запросы на сожительство",
    "FAQ": "❓ ЧаВо",
}

# ---------- Подтверждение анкеты ----------
FormButtons = {
    "Confirm": "Всё хорошо",
    "Restart": "Заполнить заново",
}

# ---------- Редактирование анкеты ----------
EditButtons = {
    "name": "Изменить имя",
    "age": "Изменить возраст",
    "univer": "Изменить учебное заведение",
    "about": "Изменить описание",
    "requirements": "Изменить пожелания",
    "city": "Изменить город",
}

# ---------- Просмотр анкеты ----------
ViewButtons = {
    "like": "👍",
    "dislike": "👎",
    "report": "⚠️ Пожаловаться"
}

# ---------- Кнопка назад ----------
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

# ---------- Reply Клавиатуры ----------
MainReplyKeyboardBuilder = ReplyKeyboardBuilder()
for text in MainButtons:
    MainReplyKeyboardBuilder.button(text=MainButtons[text])
MainReplyKeyboardBuilder.adjust(1, 2)
MainMenuKeyboard = MainReplyKeyboardBuilder.as_markup(resize_keyboard=True)

RulesButtons = {
    "Accept": "✅ Принимаю",
}
RulesKeyboardBuilder = ReplyKeyboardBuilder()
RulesKeyboardBuilder.button(text=RulesButtons["Accept"])
RulesKeyboard = RulesKeyboardBuilder.as_markup(resize_keyboard=True, one_time_keyboard=True)

FormConfirmKeyboardBuilder = ReplyKeyboardBuilder()
for text in FormButtons:
    FormConfirmKeyboardBuilder.button(text=FormButtons[text])
FormConfirmKeyboardBuilder.adjust(1, 2)
FormConfirmKeyboard = FormConfirmKeyboardBuilder.as_markup(resize_keyboard=True, one_time_keyboard=True)

# ---------- Inline Клавиатуры ----------
RegionInlineKeyboardBuilder = InlineKeyboardBuilder()
region_keys = list(Regions.keys())  
for idx, region in enumerate(region_keys):
    RegionInlineKeyboardBuilder.button(text=region, callback_data=f"reg_{idx}" )
RegionInlineKeyboardBuilder.adjust(1)
RegionInlineKeyboard = RegionInlineKeyboardBuilder.as_markup()

FormEditKeyboardBuilder = InlineKeyboardBuilder()
for text in EditButtons:
    FormEditKeyboardBuilder.button(text=EditButtons[text], callback_data=f"edit_{text}")
FormEditKeyboardBuilder.adjust(1, 2)
FormEditKeyboard = FormEditKeyboardBuilder.as_markup()

FormViewKeyboardBuilder = InlineKeyboardBuilder()
for text in ViewButtons:
    FormViewKeyboardBuilder.button(text=ViewButtons[text], callback_data=f"view_{text}")
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
            return False, f"Слишком длинно — не больше {max_len} символов.", None

        # Запрет переноса строки и табуляции для полей name и univer
        if action in ("name", "univer"):
            if '\n' in text or '\r' in text or '\t' in text:
                return False, "Использование переноса строки и табуляции запрещено. Введите текст в одну строку.", None

        return True, None, text

    return True, None, text

# ---------- Функции работы с БД ----------
def new_user_sync(user_id: int):
    supabase.table("users").upsert(
        {"user_id": user_id}, on_conflict="user_id"
    ).execute()

async def set_string_field(user_id: int, field: str, value: str, table: str = "users", additional_field: str=None, additional_value: str=None):
    def _update():
        if additional_field is not None and additional_value is not None:
            return supabase.table(table).update({field: value}).eq("user_id", user_id).eq(additional_field, additional_value).execute()
        return supabase.table(table).update({field: value}).eq("user_id", user_id).execute()
    await asyncio.to_thread(_update)

async def set_int_field(user_id: int, field: str, value: int, table: str = "users", additional_field: str=None, additional_value: int=None):
    def _update():
        if additional_field is not None and additional_value is not None:
            return supabase.table(table).update({field: value}).eq("user_id", user_id).eq(additional_field, additional_value).execute()
        return supabase.table(table).update({field: value}).eq("user_id", user_id).execute()
    await asyncio.to_thread(_update)

async def get_field(user_id: int, field: str, table: str = "users", additional_field: str = None, additional_value=None):
    def _select():
        query = supabase.table(table).select(field).eq("user_id", user_id)
        if additional_field is not None and additional_value is not None:
            query = query.eq(additional_field, additional_value)
        return query.execute()
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
        # Получаем текущее значение
        response = supabase.table("users").select("views_count").eq("user_id", user_id).execute()
        if response.data:
            current = response.data[0].get("views_count") or 0
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
        days_since_active = (now - last_ts) / 86400  # дни
        weight = (days_since_active + 1) / (views + 1)
        weights.append(weight)

    selected = random.choices(candidates, weights=weights, k=1)[0]

    # Записываем просмотр
    await add_view(user_id, selected["user_id"])
    # Увеличиваем счётчик просмотров выбранной анкеты
    await increment_views_count(selected["user_id"])
    # Обновляем время последней активности текущего пользователя
    await set_string_field(user_id, "last_active", datetime.now(timezone.utc).isoformat())

    return selected

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
    reply = None
    if action == "age":
        await set_int_field(user_id, action, value)
    else:
        await set_string_field(user_id, action, value)
    if nextaction == "region":
        reply = RegionInlineKeyboard
    if nextaction == "city":
        reply = Cities[await get_field(user_id, "region")]
    if await get_field(user_id, "form") != "true":
        await message.answer(Phrases[nextaction+"Message2"], parse_mode="HTML")
    await message.answer(Phrases[nextaction+"Message1"], reply_markup=reply, parse_mode="HTML")
    await set_string_field(user_id, "action", nextaction)
    if nextaction == "confirm":
        await message.answer(await print_profile(user_id=user_id), reply_markup=FormConfirmKeyboard, parse_mode="HTML")

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
    await message.answer(await print_profile(user_id=user_id), reply_markup=FormEditKeyboard, parse_mode="HTML")

async def print_profile(user_id=None, data=None):
    if data is None:
        if user_id is None:
            return None
        data = await get_user_sync(user_id)
    if data:
        name = html.escape(str(data.get("name") or ""))
        univer = html.escape(str(data.get("univer") or ""))
        about = html.escape(str(data.get("about") or ""))
        requirements = html.escape(str(data.get("requirements") or ""))

        raw_age = data.get("age")
        try:
            age = int(raw_age) if raw_age is not None else None
        except (TypeError, ValueError):
            age = None

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
            elif age % 10 in [2, 3, 4] and age % 100 not in [12, 13, 14]:
                yearword = "года"
            else:
                yearword = "лет"
        return (
            f"<b>{name}</b>, {age_display} {yearword} | {univer}\n\n"
            f"<b>О себе: </b>\n"
            f"<i>{about}</i>\n\n"
            f"<b>Пожелания к соседу: </b>\n"
            f"<i>{requirements}</i>\n\n"
        )
    return None

async def print_menu(message: types.Message):
    await message.answer(Phrases["Menu"], reply_markup=MainMenuKeyboard, parse_mode="HTML")

async def start_form(message: types.Message, user_id: int):
    if await get_field(user_id, "form") != "true":
        await message.answer(Phrases["RulesMessage"], reply_markup=RulesKeyboard, parse_mode="HTML")
        await set_string_field(user_id, "action", "rules")
    else:
        await message.answer(Phrases['nameMessage1'], parse_mode="HTML")
        await set_string_field(user_id, "action", "name")

async def set_commands(bot: Bot):
    commands = []
    for command in CommandMenu:
        commands.append(BotCommand(command=command, description=CommandMenu[command]))
    await bot.set_my_commands(commands)

# ---------- Бот и диспетчер ----------
bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.error()
async def error_handler(event: ErrorEvent):
    logger.error("Unhandled exception in handler: %s", event.exception, exc_info=event.exception)

# ---------- Команды ----------
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username
    await asyncio.to_thread(new_user_sync, user_id)
    await set_string_field(user_id, "username", username)
    await add_view(user_id, user_id, state="seen") 
    await message.answer(Phrases['StartMessage'], parse_mode="HTML")

async def cmd_form(message: types.Message, user_id=None):
    await set_string_field(message.from_user.id, "username", message.from_user.username)
    if user_id is not None:
        user_id = int(user_id)
        await message.answer(f"Город поиска: {await get_field(user_id, 'city')}({await get_field(user_id, 'region')})")
    else:
        user_id = message.from_user.id
    text = await print_profile(user_id=user_id)
    if text is not None:
        await message.answer(text, parse_mode="HTML", reply_markup=FormEditKeyboard)
    else:
        await message.answer("Профиль не существует")

async def cmd_menu(message: types.Message):
    await set_string_field(message.from_user.id, "username", message.from_user.username)
    await print_menu(message)

async def cmd_test(message: types.Message):
    TestIKB = InlineKeyboardBuilder()
    TestIKB.button(text="testText", callback_data="testCD")
    TestIKB.adjust(1)
    TestIK = TestIKB.as_markup()
    await message.answer("TestAnswer", reply_markup=TestIK)

async def cmd_find(message: types.Message, user_id=None):
    await set_string_field(message.from_user.id, "username", message.from_user.username)
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
    if profile_text is not None:
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
        response = supabase.table("views").select("*").eq("viewed_user_id", user_id).eq("state", "like_unseen").execute()
        return response.data
    likes = await asyncio.to_thread(_sync)
    if not likes:
        await message.answer("У вас нет новых лайков.")
        return
    liked_user_id = likes[0].get("user_id")
    form = await get_user_sync(liked_user_id)
    if form is None:
        await message.answer("Анкета этого пользователя больше недоступна.")
        return
    profile_text = await print_profile(data=form)
    if profile_text is not None:
        await message.answer(profile_text, parse_mode="HTML", reply_markup=FormViewKeyboard)
    else:
        await message.answer("Ошибка при получении профиля.")
    await set_string_field(user_id, "action", f"likes_{liked_user_id}")

def clear_all_data_sync():
    supabase.table("views").delete().neq("user_id", -1).execute()
    supabase.table("users").delete().neq("user_id", -1).execute()

def recreate_database_sync():
    return supabase.rpc("recreate_database").execute()

async def run_diagnostics() -> str:
    results = []
    # ... (диагностика без изменений, опущена для краткости)
    return f"🔧 Диагностика {BOT_NAME}\n\n" + "\n".join(results)

# ----------- Обработка команд -------------
async def command(message: types.Message):
    text = message.text
    if text == "/start":
        await cmd_start(message)
    elif text == "/form":
        await start_form(message, message.from_user.id)
    elif text == "/profile":
        await cmd_form(message)
    elif text == "/menu":
        await cmd_menu(message)
    elif text == "/test":
        await cmd_test(message)
    elif text == "/find":
        await cmd_find(message)
    elif text == "/faq":
        await cmd_faq(message)
    elif text == "/likes":
        await cmd_likes(message)

# ---------- Обработка сообщений ----------
async def text(message: types.Message):
    text = message.text
    user_id = message.from_user.id
    action = await get_field(user_id, "action")
    if text == ROOT_CODE and await get_field(user_id, "root") != "true":
        await set_string_field(user_id, "root", "true")
        await message.answer(Phrases["RootCode"], parse_mode="HTML")
        return
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
    if text == ReturnButton["Return"]:
        await set_string_field(user_id, "action", "None")
        await print_menu(message)
    if text == MainButtons["Profile"]:
        await cmd_form(message, user_id=user_id)
    if text == MainButtons["Find"]:
        await cmd_find(message)
    if text == MainButtons["Likes"]:
        await cmd_likes(message)
    if text == MainButtons["FAQ"]:
        await cmd_faq(message)

# ---------- Консольные команды ----------
async def cmd(message: types.Message):
    text = message.text
    user_id = message.from_user.id
    if await get_field(user_id, "root") != "true":
        return
    if text.startswith("cmd_deleteform"):
        # ... (обработка)
        pass
    elif text == "cmd_cleardata":
        # ... (обработка)
        pass
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
            await message.answer(f"❌ Ошибка: {e}")
    elif text == "cmd_selftest":
        await message.answer("⏳ Запускаю диагностику...")
        report = await run_diagnostics()
        await message.answer(report)

# ---------- Принимаем сообщения ----------
@dp.message()
async def message(message: types.Message):
    mtext = message.text
    username = message.from_user.username
    if not(username):
        await message.answer("Чтобы пользоваться ботом установите имя пользователя в настройках Telegram")
        return
    if mtext and mtext[0] == "/":
        await command(message)
    elif mtext and mtext[:4] == "cmd_":
        await cmd(message)
    else:
        await text(message)

# ---------- Callback ----------
@dp.callback_query()
async def callback_query(callback: CallbackQuery):
    data = callback.data
    user_id = callback.from_user.id
    await set_string_field(user_id, "username", callback.from_user.username)
    form = await get_field(user_id, "form")
    if data.startswith("reg_"):
        try:
            region_idx = int(data.split("_")[1])
        except ValueError:
            await callback.answer("Некорректный выбор региона.")
            return
        if not (0 <= region_idx < len(region_keys)):
            await callback.answer("Некорректный выбор региона.")
            return
        region_name = region_keys[region_idx]
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
                await callback.answer("Действие устарело, начните заново.")
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
                await callback.answer("Действие устарело, начните заново.")
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

# ---------- Сайт (статистика) ----------
async def stats(request):
    def _get_stats():
        users_count = supabase.table("users").select("user_id", count="exact").execute().count
        filled_count = supabase.table("users").select("user_id", count="exact").eq("form", "true").execute().count
        views_count = supabase.table("views").select("user_id", count="exact").execute().count
        likes_count = supabase.table("views").select("user_id", count="exact").eq("state", "like_unseen").execute().count
        cities = supabase.table("users").select("city").eq("form", "true").execute()
        city_counter = Counter(row["city"] for row in cities.data if row.get("city"))
        top_cities = city_counter.most_common(5)
        return {
            "users_total": users_count,
            "filled_forms": filled_count,
            "views_total": views_count,
            "likes_total": likes_count,
            "top_cities": top_cities,
        }

    stats_data = await asyncio.to_thread(_get_stats)
    html_content = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>📊 Статистика Livether</title>
        <style>
            body {{ font-family: sans-serif; max-width: 800px; margin: auto; padding: 20px; background: #f9f9f9; }}
            .stat {{ background: white; padding: 15px; margin: 10px 0; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .stat h2 {{ margin: 0 0 5px 0; font-size: 1.2em; }}
            .stat p {{ font-size: 1.8em; font-weight: bold; margin: 0; color: #2c3e50; }}
            ul {{ padding-left: 20px; }}
            li {{ margin: 5px 0; }}
        </style>
    </head>
    <body>
        <h1>📊 Статистика бота Livether</h1>
        <div class="stat"><h2>👥 Всего пользователей</h2><p>{stats_data['users_total']}</p></div>
        <div class="stat"><h2>✅ Заполненных анкет</h2><p>{stats_data['filled_forms']}</p></div>
        <div class="stat"><h2>👁️ Просмотров анкет</h2><p>{stats_data['views_total']}</p></div>
        <div class="stat"><h2>❤️ Лайков</h2><p>{stats_data['likes_total']}</p></div>
        <div class="stat"><h2>🏙️ Топ-5 городов</h2>
            <ul>
                {"".join(f"<li>{city}: {count}</li>" for city, count in stats_data['top_cities'])}
            </ul>
        </div>
        <p><i>🔄 Обновлено: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i></p>
        <footer><a href="/">На главную</a></footer>
    </body>
    </html>
    """
    return web.Response(text=html_content, content_type='text/html')

def create_app():
    app = web.Application()
    app.router.add_get("/", lambda request: web.Response(text="<h1>Livether Bot is running</h1>", content_type='text/html'))
    app.router.add_get("/health", lambda request: web.Response(text="OK"))
    app.router.add_get("/stats", stats)
    return app

# ---------- Точка входа ----------
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await set_commands(bot)

    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 5000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info("Health-check server запущен на порту %s, запускаю polling...", port)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())