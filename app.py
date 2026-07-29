import os
import logging
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.webhook import aiohttp_server
from aiogram import F
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

# ---------- Бот и диспетчер ----------
bot = Bot(token=TOKEN)
dp = Dispatcher()

# ---------- Обработчики команд ----------
Phrases = {
    "FirstNameMessage": "Привет! Это бот" #После команды /start Запрашиваем имя
}

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    userid = message.from_user.id
    await asyncio.to_thread(new_user_sync, userid)
    await message.answer("Phrases['FirstNameMessage']")
    await set_string_field(userid, "action", "name")

@dp.message(Command("profile"))
async def cmd_profile(message: types.Message):
    user_id = message.from_user.id
    data = await asyncio.to_thread(get_user_sync, user_id)
    if data:
        text = format_profile(data)
    else:
        text = "Профиль не найден"
    await message.answer(text)


@dp.message(Command("echo"))
async def cmd_echo_message(message: types.Message):
    await message.send_copy(chat_id=message.chat.id)

@dp.message(Command("test"))
async def cmd_test(message: types.Message):
    userid = message.from_user.id
    await message.answer("Тест")

@dp.message(F.text & ~F.text.startswith('/'))
async def handle_text(message: types.Message):
    text = message.text
    ""


# ---------- Функция установки вебхука (будет вызвана при старте) ----------
async def on_startup(app: web.Application):
    webhook_url = "https://studether.onrender.com/webhook"
    # Удаляем старый вебхук на всякий случай
    await bot.delete_webhook()
    await bot.set_webhook(webhook_url)
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







#-----------работа с данными-------------

def get_user_sync(user_id: int) -> dict | None:
    """Возвращает словарь со всеми полями пользователя."""
    response = supabase.table("users").select("*").eq("user_id", user_id).execute()
    if response.data:
        return response.data[0]  # первая (и единственная) строка
    return None


def format_profile(data: dict) -> str:
    
    c_user_id = data.get("id")

    c_user_photo = data.get("photo")
    c_user_name = data.get("username")
    c_user_age = data.get("age")
    c_user_course = data.get("course")
    c_user_city = data.get("city")
    c_user_university = data.get("university")
    c_user_bio = data.get("bio")

    return (
        f"👤 Профиль\n"
        f"Фото: ебать ты урод\n"          # пока так, потом можно менять
        f"Имя: {c_user_name}\n"
        f"Возраст: {c_user_age}\n"
        f"Курс: {c_user_course}\n"
        f"Город: {c_user_city}\n"
        f"Университет: {c_user_university}\n"
        f"О себе: {c_user_bio}"
    )










    






