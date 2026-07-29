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
    """Создаёт запись пользователя, если её нет (синхронная версия)."""
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

# ---------- Обработчик /start ----------
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
<<<<<<< Updated upstream
    await message.answer("У ромы маленький член!")
    # Вызываем синхронную функцию в отдельном потоке, чтобы не блокировать асинхронный цикл
    await asyncio.to_thread(new_user_sync, message.from_user.id)
=======
    await message.answer("Мы сидели дома с моим другом Ромой, он достал огромный")
    await new_user_sync(message.from_user.id)
>>>>>>> Stashed changes

# ---------- Эхо-камера для /echo ----------
@dp.message(Command("echo"))
async def cmd_echo_message(message: types.Message):
    await message.send_copy(chat_id=message.chat.id)

# ---------- Flask-приложение ----------
flask_app = Flask(__name__)

# Эндпоинт для пинга (проверка, что бот жив)
@flask_app.route("/")
def home():
    return "Бот работает!"

@flask_app.route("/health")
def health():
    return "OK", 200

# Эндпоинт для приёма вебхуков от Telegram
@flask_app.route("/webhook", methods=["POST"])
async def webhook():
    """Принимает обновления от Telegram и передаёт их диспетчеру."""
    # Получаем JSON из запроса
    json_data = request.get_json()
    if not json_data:
        return jsonify({"error": "No data"}), 400

    # Преобразуем JSON в объект Update
    try:
        update = types.Update(**json_data)
        # Передаём обновление диспетчеру
        await dp.process_update(update)
    except Exception as e:
        logger.error(f"Ошибка при обработке вебхука: {e}")
        return jsonify({"error": "Internal error"}), 500

    # Возвращаем пустой ответ с кодом 200 (Telegram этого ждёт)
    return "", 200

# ---------- Функция установки вебхука ----------
async def set_webhook():
    """Устанавливает вебхук для бота при старте."""
    # Публичный URL твоего сервиса (замени, если имя другое)
    WEBHOOK_URL = "https://studether.onrender.com/webhook"
    await bot.set_webhook(WEBHOOK_URL)
    logger.info(f"Вебхук установлен на {WEBHOOK_URL}")

# ---------- Точка входа ----------
if __name__ == "__main__":
    # Устанавливаем вебхук перед запуском сервера
    asyncio.run(set_webhook())

    # Запускаем Flask-сервер (главный поток)
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Flask на порту {port}")
    flask_app.run(host="0.0.0.0", port=port)