import os
import logging
import asyncio
from flask import Flask, request, jsonify
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
    try:
        response = supabase.table("users").upsert(
            {"user_id": user_id}, on_conflict="user_id"
        ).execute()
        if response.data:
            logger.info(f"Пользователь {user_id} сохранён")
        else:
            logger.warning(f"Неизвестный ответ для {user_id}")
    except Exception as e:
        logger.error(f"Ошибка при сохранении {user_id}: {e}")

# ---------- Бот и диспетчер ----------
bot = Bot(token=TOKEN)
dp = Dispatcher()

# ---------- Обработчики команд ----------
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
<<<<<<< Updated upstream
    await message.answer("У ромы маленький член!")
    # Выполняем синхронный запрос к БД в отдельном потоке, чтобы не блокировать асинхронный цикл
    await asyncio.to_thread(new_user_sync, message.from_user.id)
=======
    await message.answer("Мы сидели дома с моим другом Ромой, он достал огромный")
    await new_user_sync(message.from_user.id)
>>>>>>> Stashed changes

@dp.message(Command("echo"))
async def cmd_echo_message(message: types.Message):
    await message.send_copy(chat_id=message.chat.id)

# ---------- Flask-приложение ----------
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "Бот работает!"

@flask_app.route("/health")
def health():
    return "OK", 200

@flask_app.route("/webhook", methods=["POST"])
async def webhook():
    """Принимает обновления от Telegram и передаёт их диспетчеру."""
    json_data = request.get_json()
    if not json_data:
        return jsonify({"error": "No data"}), 400
    
    try:
        update = types.Update(**json_data)
        await dp.process_update(update)
    except Exception as e:
        logger.error(f"Ошибка при обработке вебхука: {e}")
        return jsonify({"error": "Internal error"}), 500
    
    return "", 200

# ---------- Установка вебхука ----------
async def set_webhook():
    """Удаляет старый вебхук и устанавливает новый."""
    # Сначала удаляем вебхук, чтобы избежать конфликтов
    await bot.delete_webhook()
    # Устанавливаем новый вебхук
    webhook_url = "https://studether.onrender.com/webhook"  # Убедись, что имя совпадает
    await bot.set_webhook(webhook_url)
    logger.info(f"Вебхук установлен на {webhook_url}")

# ---------- Точка входа ----------
if __name__ == "__main__":
    # Устанавливаем вебхук при старте
    asyncio.run(set_webhook())
    
    # Запускаем Flask-сервер
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Flask на порту {port}")
    flask_app.run(host="0.0.0.0", port=port)