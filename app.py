import os
import threading
import logging
import asyncio
from flask import Flask
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
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

# ---------- Синхронная функция для работы с БД ----------
def new_user_sync(user_id: int):
    """Создаёт запись пользователя, если её нет (синхронная версия)."""
    try:
        response = supabase.table("users").upsert(
            {"user_id": user_id}, on_conflict="user_id"
        ).execute()
        if response.data:
            logger.info(f"Пользователь {user_id} сохранён")
        else:
            # На всякий случай, если нет data, но и ошибки не было
            logger.warning(f"Неизвестный ответ для {user_id}")
    except Exception as e:
        logger.error(f"Ошибка при сохранении {user_id}: {e}")

# ---------- Бот и диспетчер ----------
bot = Bot(token=TOKEN)
dp = Dispatcher()

# ---------- Обработчик /start ----------
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Привет!")
    # Выполняем синхронную операцию в отдельном потоке, чтобы не блокировать событийный цикл
    await asyncio.to_thread(new_user_sync, message.from_user.id)

# ---------- Flask для пинга ----------
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "Бот работает!"

@flask_app.route("/health")
def health():
    return "OK", 200

# ---------- Запуск бота в фоновом потоке ----------
def run_bot():
    try:
        logger.info("Бот запущен")
        dp.run_polling(bot, handle_signals=False)
    except Exception as e:
        logger.error(f"Ошибка: {e}")

# ---------- Точка входа ----------
if __name__ == "__main__":
    thread = threading.Thread(target=run_bot, daemon=True)
    thread.start()
    logger.info("Поток бота запущен")

    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Flask на порту {port}")
    flask_app.run(host="0.0.0.0", port=port)