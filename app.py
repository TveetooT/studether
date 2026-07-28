import os
import threading
import logging
import asyncio
from flask import Flask
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ---------- Настройка логирования (подробно) ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ---------- Конфигурация ----------
TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TOKEN:
    logger.error("❌ TELEGRAM_TOKEN не задан в переменных окружения!")
    raise ValueError("TELEGRAM_TOKEN is not set")

logger.info("✅ Токен получен")

# ---------- Хранилище анкет ----------
profiles = {}

# ---------- FSM состояния ----------
class ProfileForm(StatesGroup):
    name = State()
    gender = State()
    age = State()
    city = State()
    max_rent = State()
    preferences = State()

# ---------- Бот и диспетчер ----------
storage = MemoryStorage()
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=storage)

# ---------- Flask ----------
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "Бот работает!"

@flask_app.route("/health")
def health():
    return "OK", 200

# ---------- Обработчики команд ----------
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    logger.info(f"Команда /start от {message.from_user.id}")
    await message.answer("Привет! Я помогу найти сожителя.\nИспользуй /add и /find.")

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer("Команды: /start, /help, /add, /find, /cancel")

@dp.message(Command("add"))
async def cmd_add(message: types.Message, state: FSMContext):
    await state.set_state(ProfileForm.name)
    await message.answer("Как тебя зовут?")

@dp.message(ProfileForm.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(ProfileForm.gender)
    await message.answer("Какой твой пол? (мужской/женский)")

@dp.message(ProfileForm.gender)
async def process_gender(message: types.Message, state: FSMContext):
    await state.update_data(gender=message.text)
    await state.set_state(ProfileForm.age)
    await message.answer("Сколько тебе лет? (число)")

@dp.message(ProfileForm.age)
async def process_age(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Введите число.")
        return
    await state.update_data(age=int(message.text))
    await state.set_state(ProfileForm.city)
    await message.answer("В каком городе ищешь жильё?")

@dp.message(ProfileForm.city)
async def process_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text)
    await state.set_state(ProfileForm.max_rent)
    await message.answer("Максимальная арендная плата (руб)?")

@dp.message(ProfileForm.max_rent)
async def process_max_rent(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Введите число.")
        return
    await state.update_data(max_rent=int(message.text))
    await state.set_state(ProfileForm.preferences)
    await message.answer("Пожелания по сожителю?")

@dp.message(ProfileForm.preferences)
async def process_preferences(message: types.Message, state: FSMContext):
    data = await state.get_data()
    profile = {
        "user_id": message.from_user.id,
        "name": data["name"],
        "gender": data["gender"],
        "age": data["age"],
        "city": data["city"],
        "max_rent": data["max_rent"],
        "preferences": message.text,
    }
    profiles[message.from_user.id] = profile
    await state.clear()
    await message.answer("Анкета сохранена! Используй /find.")

@dp.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Отменено.")

@dp.message(Command("find"))
async def cmd_find(message: types.Message):
    user_id = message.from_user.id
    if user_id not in profiles:
        await message.answer("Сначала создай анкету через /add")
        return
    my = profiles[user_id]
    matches = [p for uid, p in profiles.items() if uid != user_id and p["city"].lower() == my["city"].lower()]
    if not matches:
        await message.answer(f"В городе {my['city']} пока нет анкет.")
        return
    text = "Найдены:\n" + "\n".join(
        f"- {p['name']}, {p['age']} лет, до {p['max_rent']} руб., {p['preferences']}"
        for p in matches
    )
    await message.answer(text)

# ---------- Функция запуска бота с обработкой ошибок ----------
def run_bot():
    """Запускает поллинг с перехватом исключений."""
    try:
        logger.info("🚀 Запуск поллинга бота...")
        # Запускаем поллинг (синхронный метод, внутри asyncio)
        dp.run_polling(bot)
    except Exception as e:
        logger.error(f"❌ Ошибка в боте: {e}", exc_info=True)
        # Можно попробовать перезапустить, но для простоты просто логируем

# ---------- Точка входа ----------
if __name__ == "__main__":
    # Запускаем бота в фоновом потоке
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    logger.info("✅ Поток бота запущен")

    # Запускаем Flask (главный поток)
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"🌐 Flask сервер на порту {port}")
    flask_app.run(host="0.0.0.0", port=port)