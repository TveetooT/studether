import os
import logging
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    BotCommand,                          
    InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.webhook import aiohttp_server
from supabase import create_client

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


# ---------- Константы ----------
BOT_NAME = "Studether"

# ---------- Списки ----------
Actions = [
    "firstname", "age", "year", "city", "univer", "about", "requirements", "confirm"
]

# ---------- Словари ----------
Phrases = {
    "StartMessage": "👋 Привет! Я робот хD.\nДавай найдем для тебя \nдруга, с которым ты будешь вместе снимать жилье 🏠.\nНачни заполнять анкету в /form",

    "firstnameMessage1": "Имя, отображаемое в анкете",
    "ageMessage1": "Возраст, отображаемый в анкете",
    "yearMessage1": "Курс, отображаемый в анкете\nЕсли ты закончил бакалавриат и учишься в аспирантуре или т.п., укажи общее количество учебных лет.\nЕсли сейчас лето, укажи, на какой курс ты переходишь.",
    "cityMessage1": "Город, используемый для поиска",
    "univerMessage1": "Учебное заведение, отображаемое в профиле",
    "aboutMessage1": "Описание профиля",
    "requirementsMessage1": "Пожелания, отображаемые после описания профиля",

    "firstnameMessage2": f"Меня зовут Studether. А под каким именем ты хочешь быть видимым для других людей?",
    "ageMessage2": "Сколько тебе лет?",
    "yearMessage2": "Гораздо веселее будет жить со студентами того же курса! На каком курсе ты сейчас?",
    "cityMessage2": "В каком городе ты собираешься снимать квартиру?",
    "univerMessage2": "Выбери учебное заведение, в котором ты учишься",
    "aboutMessage2": "Добавь информацию к анкете. Можешь рассказать о себе или о том, какую квартиру ищешь. Что бы ты сам(а) хотел(а) знать о своём будущем соседе?",
    "requirementsMessage2": "Очень чистоплотен/чистоплотна, или наоборот наплевать, сколько носков валяется на полу? Жить вдвоём или целой казармой? Хочешь соседа, с которым интересно поговорить, или перекидываться взглядами раз в день? Расскажи, каким/какой бы ты хотел(а) видеть будущего соседа.",

    "confirmMessage1": "✅ Проверь свою анкету",
    "confirmMessage2": ".",

    "FormSaved": "Анкета сохранена! Теперь ты можешь искать соседей через /find.",
    "Menu": "Ты в меню. Выбери действие на клавиатуре",
}

Buttons = { #В названии переменной сначала идёт клавиатура к которой привязана кнопка, потом действие
    "MainProfile": "",
    "MainFind": "",
    "FormConfirm": "Всё хорошо",
    "FormRestart": "Заполнить заново",
}

NextAction = { 
    "firstname": "age",
    "age": "year",
    "year": "city",
    "city": "univer",
    "univer": "about",
    "about": "requirements",
    "requirements": "confirm",
}

CommandMenu = {
    "start": "Запустить бота",
    "profile": "Вывести анкету",
    "form": "Заполнить анкету",
    "menu": "Меню",
}
# ---------- Reply Клавиатуры ----------
# ---------- Главная клавиатура ----------
MainReplyKeyboardBuilder = ReplyKeyboardBuilder()
MainReplyKeyboardBuilder.button(text=Buttons["MainProfile"])
MainReplyKeyboardBuilder.button(text=Buttons["MainFind"])
MainReplyKeyboardBuilder.adjust(1, 2) #Столбцы, ряды
MainMenuKeyboard = MainReplyKeyboardBuilder.as_markup(resize_keyboard=True)
# ---------- Клавиатура в конце анкеты ----------
FormConfirmKeyboardBuilder = ReplyKeyboardBuilder()
FormConfirmKeyboardBuilder.button(text=Buttons["FormConfirm"])
FormConfirmKeyboardBuilder.button(text=Buttons["FormRestart"])
FormConfirmKeyboardBuilder.adjust(1, 2)
FormConfirmKeyboard = FormConfirmKeyboardBuilder.as_markup(resize_keyboard=True, one_time_keyboard=True)
# ---------- Подключение к БД ----------
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------- Функция для БД ----------
def new_user_sync(user_id: int):
    response = supabase.table("users").upsert(
        {"user_id": user_id}, on_conflict="user_id"
    ).execute()

async def set_string_field(user_id: int, field: str, value: str):
    response = supabase.table("users")\
        .update({field: value})\
        .eq("user_id", user_id)\
        .execute()

async def set_int_field(user_id: int, field: str, value: int):
    response = supabase.table("users")\
        .update({field: value})\
        .eq("user_id", user_id)\
        .execute()

async def get_field(user_id: int, field: str):
    response = supabase.table("users")\
        .select(field)\
        .eq("user_id", user_id)\
        .execute()
    return response.data[0][field]

def get_user_sync(user_id: int) -> dict | None:
    response = supabase.table("users").select("*").eq("user_id", user_id).execute()
    if response.data:
        return response.data[0]  # первая (и единственная) строка
    return None

# ---------- Выводим и получаем вопрос в анкете ----------
async def form_question(message: types.Message):
    text = message.text
    user_id = message.from_user.id
    action = await get_field(user_id, "action")
    await set_string_field(user_id, action, text)
    if await get_field(user_id, "form") != "true":
        await message.answer([NextAction[action]+"Message2"])
    await message.answer(Phrases[NextAction[action]+"Message1"])
    await set_string_field(user_id, "action", NextAction[action])
    if NextAction[action] == "confirm":
        await message.answer(await get_profile(user_id), reply_markup=FormConfirmKeyboard)
    
# ----------- Выводим профиль -----------
async def get_profile(user_id: int):
    data = await asyncio.to_thread(get_user_sync, user_id)
    if data:
        text = await format_profile(data)
    else:
        text = None
    return text

# ----------- Возращаемся в меню -----------
async def print_menu(message: types.Message):
    await message.answer(Phrases["Menu"], reply_markup=MainMenuKeyboard)

# ----------- Старт анкеты -----------
async def start_form(message: types.Message, user_id: int):
    await message.answer(Phrases['firstnameMessage1'])
    if await get_field(user_id, "form") != "true":
        await message.answer(Phrases['firstnameMessage2'])
    await set_string_field(user_id, "action", "firstname")

# ----------- Меню команд -----------
async def set_commands(bot: Bot):
    commands = []
    for command in CommandMenu:
        commands.append(BotCommand(command=command, description=CommandMenu[command]))
    await bot.set_my_commands(commands)

# ----------- Работа с данными -------------
async def format_profile(data: dict) -> str:

    c_user_id = data.get("id")

    c_user_photo = data.get("photo")
    c_user_name = data.get("firstname")
    c_user_age = data.get("age")
    c_user_course = data.get("year")
    c_user_city = data.get("city")
    c_user_university = data.get("univer")
    c_user_bio = data.get("about")

    return (
        f"👤 Профиль\n"
        f"Фото: ебать ты \n"          # пока так, потом можно менять
        f"Имя: {c_user_name}\n"
        f"Возраст: {c_user_age}\n"
        f"Курс: {c_user_course}\n"
        f"Город: {c_user_city}\n"
        f"Университет: {c_user_university}\n"
        f"О себе: {c_user_bio}"
    )

# ---------- Бот и диспетчер ----------
bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    await asyncio.to_thread(new_user_sync, user_id)
    await message.answer(Phrases['StartMessage'])

@dp.message(Command("profile"))
async def cmd_profile(message: types.Message):
    user_id = message.from_user.id
    text = await get_profile(user_id)
    if text != None:
        await message.answer(text)
    else:
        await message.answer("Профиль не существует")

@dp.message(Command("form"))
async def cmd_form(message: types.Message):
    user_id = message.from_user.id
    await start_form(message, user_id)

@dp.message(F.text & ~F.text.startswith('/'))
async def cmd_text(message: types.Message):
    text = message.text
    user_id = message.from_user.id
    action = await get_field(user_id, "action")     
    if action in Actions:    
        if action == "confirm":
            await set_string_field(user_id, "form", "true")
            await set_string_field(user_id , "action", "None")
            if text == Buttons["FormRestart"]:
                await cmd_form(message)
            if text == Buttons["FormConfirm"]:
                await message.answer(Phrases["FormSaved"])
                await print_menu(message)
            return
        await form_question(message)

@dp.message(Command("menu"))
async def cmd_menu(message: types.Message):
    print_menu(message)

# ---------- Функция установки вебхука (будет вызвана при старте) ----------
async def on_startup(app: web.Application):
    webhook_url = WEBHOOK_URL
    await bot.delete_webhook()
    await bot.set_webhook(webhook_url)
    await set_commands(bot) 


# ---------- Создание aiohttp-приложения ----------
def create_app():
    app = web.Application()
    async def health(request):
        return web.Response(text="OK", status=200)
    app.router.add_get("/", health)
    app.router.add_get("/health", health)
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