import os
import logging
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.webhook import aiohttp_server
from aiogram import F
from supabase import create_client
from aiogram.types import BotCommand
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

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

# ---------- Подключение к БД ----------
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------- Функция для БД ----------
def new_user_sync(user_id: int):
    try:
        response = supabase.table("users").upsert(
            {"user_id": user_id}, on_conflict="user_id"
        ).execute()
        if response.data:
            logger.info(f"Пользователь {user_id} сохранён")
    except Exception as e:
        logger.error(f"Ошибка при сохранении {user_id}: {e}")

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
    """Возвращает словарь со всеми полями пользователя."""
    response = supabase.table("users").select("*").eq("user_id", user_id).execute()
    if response.data:
        return response.data[0]  # первая (и единственная) строка
    return None

# ----------- Выводим профиль -----------
async def get_profile(user_id: int):
    data = await asyncio.to_thread(get_user_sync, user_id)
    if data:
        text = await format_profile(data)
    else:
        text = None
    return text

# ----------- Старт анкеты -----------
async def start_form(message: types.Message, user_id: int):
    await message.answer(Phrases['FirstNameMessage1'])
    if await get_field(user_id, "form") == "false":
        await message.answer(Phrases['FirstNameMessage2'])
    await set_string_field(user_id, "action", "firstname")

# ----------- Меню команд -----------
async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="help", description="Получить помощь"),
        BotCommand(command="profile", description="Мой профиль"),
        BotCommand(command="find", description="Найти сожителя"),
    ]
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

# ---------- Обработчики команд ----------
Phrases = {
    "StartMessage": "👋 Привет! Я робот хD.\nДавай найдем для тебя \nдруга, с которым ты будешь вместе снимать жилье 🏠.\nНачни заполнять анкету в /form",
    "FirstNameMessage1": "Как тебя зовут?",
    "AgeMessage1": "Сколько тебе лет?",
    "YearMessage1": "Как долго ты уже учишься в Вузе(в годах)?", #Если магистратура/аспирантура то год обучения от первого курса
    "CityMessage1": "В каком городе ты хочешь найти сожителя", 
    "UniverMessage1": "Как называется твой ВУЗ?",
    "AboutMessage1": "Расскажи о себе, что тебе нравится, в чем у тебя все успешно получается.",
    "RequirementsMessage1": "Что требуешь от соседа?",
    "FormConfirm": "Проверь свою анкету", #Выводу анкету после этого
    "FirstNameMessage2": "Как тебя зовут?",
    "AgeMessage2": "Возраст",
    "YearMessage2": "Год обучения",
    "CityMessage2": "Город", 
    "UniverMessage2": "Вуз",
    "AboutMessage2": "О себе",
    "RequirementsMessage2": "Требования к соседу",
}

@dp.message(Command("test"))
async def cmd_test(message: types.Message):
    user_id = message.from_user.id
    await message.answer("Тест")

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
        message.answer("Профиль не существует")

@dp.message(Command("form"))
async def cmd_form(message: types.Message):
    user_id = message.from_user.id
    await start_form(message, user_id)

@dp.message(F.text & ~F.text.startswith('/'))
async def handle_text(message: types.Message):
    text = message.text
    user_id = message.from_user.id
    action = await get_field(user_id, "action")     
    if action == "firstname":
        await set_string_field(user_id, "firstname", text)
        await message.answer(Phrases['AgeMessage1'])
        if await get_field(user_id, "form") == "false":
            await message.answer(Phrases['AgeMessage2'])
        await set_int_field(user_id, "action", "age")
    if action == "age":
        await set_string_field(user_id, "age", text)
        await message.answer(Phrases['YearMessage1'])
        if await get_field(user_id, "form") == "false":
            await message.answer(Phrases['YearMessage2'])
        await set_int_field(user_id, "action", "year")
    if action == "year":
        await set_string_field(user_id, "year", text)
        await message.answer(Phrases['CityMessage1'])
        if await get_field(user_id, "form") == "false":
            await message.answer(Phrases['CityMessage2'])
        await set_string_field(user_id, "action", "city")
    if action == "city":
        await set_string_field(user_id, "city", text)
        await message.answer(Phrases['UniverMessage1'])
        if await get_field(user_id, "form") == "false":
            await message.answer(Phrases['UniverMessage2'])
        await set_string_field(user_id, "action", "univer")
    if action == "univer":
        await set_string_field(user_id, "univer", text)
        await message.answer(Phrases['AboutMessage1'])
        if await get_field(user_id, "form") == "false":
            await message.answer(Phrases['AboutMessage2'])
        await set_string_field(user_id, "action", "about")
    if action == "about":
        await set_string_field(user_id, "about", text)
        await message.answer(Phrases['RequirementsMessage1'])
        if await get_field(user_id, "form") == "false":
            await message.answer(Phrases['RequirementsMessage2'])
        await set_string_field(user_id, "action", "requirements")
    if action == "requirements":
        await set_string_field(user_id, "requirements", text)
        await message.answer(Phrases['FormConfirm'])
        await message.answer(await get_profile(user_id))
        await set_string_field(user_id, "action", "confirm")
    if action == "confirm":
        await set_string_field(user_id, "form", "true")
        if text == "false":
            await cmd_form()
          


# ---------- Функция установки вебхука (будет вызвана при старте) ----------
async def on_startup(app: web.Application):
    webhook_url = "https://studether.onrender.com/webhook"
    
    # Удаляем старый вебхук на всякий случай
    await bot.delete_webhook()
    await bot.set_webhook(webhook_url)
    await set_commands(bot) перенесено

    logger.info(f"Вебхук установлен на {webhook_url}")


# ---------- Создание aiohttp-приложения ----------
def create_app():
    app = web.Application()

    # Эндпоинты для пинга (проверки здоровья)
    async def health(request):
        return web.Response(text="OK", status=200)
    app.router.add_get("/", health)
    app.router.add_get("/health", health)

    # Регистрируем вебхук-обработчик от aiogram
    webhook_requests = aiohttp_server.SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    webhook_requests.register(app, path="/webhook")

    # Регистрируем функцию, которая выполнится при старте сервера
    app.on_startup.append(on_startup)

    return app

# ---------- Точка входа ----------
if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Сервер запущен на порту {port}") 
    # Запускаем aiohttp-сервер (он сам создаст и управляет циклом событий)
    web.run_app(app, host="0.0.0.0", port=port)









    






