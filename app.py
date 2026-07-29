import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.webhook import aiohttp_server
from supabase import create_client
from aiohttp import web

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

# ---------- Бот и диспетчер ----------
bot = Bot(token=TOKEN)
dp = Dispatcher()

# ---------- Обработчики ----------
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("У ромы маленький член!")
    await asyncio.to_thread(new_user_sync, message.from_user.id)

@dp.message(Command("echo"))
async def cmd_echo_message(message: types.Message):
    await message.send_copy(chat_id=message.chat.id)

# ---------- Установка вебхука ----------
async def on_startup():
    webhook_url = "https://studether.onrender.com/webhook"
    await bot.set_webhook(webhook_url)
    logger.info(f"Вебхук установлен на {webhook_url}")

# ---------- Запуск через aiohttp ----------
def main():
    # Создаём приложение aiohttp
    app = web.Application()
    
    # Эндпоинт для пинга (чтобы Render не думал, что сервер умер)
    async def health(request):
        return web.Response(text="OK", status=200)
    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    
    # Эндпоинт для вебхука
    webhook_requests = aiohttp_server.SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    webhook_requests.register(app, path="/webhook")

    # Запускаем сервер
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Сервер запущен на порту {port}")
    
    # Важно: перед запуском сервера нужно установить вебхук
    asyncio.run(on_startup())
    
    web.run_app(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()