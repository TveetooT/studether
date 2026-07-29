import os
import threading
import logging
from flask import Flask
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from supabase import create_client

# ---------- Логирование ----------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------- Подключение к БД ----------
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------- Токен ----------
TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_TOKEN не задан")

# ---------- Бот и диспетчер ----------
bot = Bot(token=TOKEN)
dp = Dispatcher()

# ---------- Единственный обработчик ----------
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Привет!")
    reserve_user(message.from_user.id)


#------------ Эхо камера --------
@dp.message()
async def echo_message(message: types.Message):
    await message.reply(text=message.text)
    await message.send_copy(chat_id=message.chat.id)



# ---------- Flask для пинга (чтобы Render не уснул) ----------
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
        # handle_signals=False обязательно для работы в фоновом потоке
        dp.run_polling(bot, handle_signals=False)
    except Exception as e:
        logger.error(f"Ошибка: {e}")

# ---------- Точка входа ----------
if __name__ == "__main__":
    # Запускаем бота в отдельном потоке
    thread = threading.Thread(target=run_bot, daemon=True)
    thread.start()
    logger.info("Поток бота запущен")

    # Запускаем Flask в главном потоке (для порта)
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Flask на порту {port}")
    flask_app.run(host="0.0.0.0", port=port)



# ---------- БД ----------
def reserve_user(id: int):
    user = {
        "user_id": id,
        "username": None,
        "first_name": None,
        "last_name": None
    }
    response = supabase.table("users").upsert(user).execute()
    