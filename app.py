import os
import threading
import logging
from flask import Flask
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message
from aiogram.utils.markdown import hbold

# ---------- Логирование ----------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------- Конфигурация ----------
TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_TOKEN не задан в переменных окружения")

# ---------- Хранилища данных ----------
profiles = {}          # user_id -> dict с анкетой

# ---------- Определение состояний FSM ----------
class ProfileForm(StatesGroup):
    name = State()
    gender = State()
    age = State()
    city = State()
    max_rent = State()
    preferences = State()

# ---------- Инициализация бота и диспетчера ----------
storage = MemoryStorage()
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=storage)

# ---------- Flask приложение для пинга ----------
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "Бот работает!"

@flask_app.route("/health")
def health():
    return "OK", 200

# ---------- Обработчики команд ----------

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Привет! Я помогу найти сожителя.\n"
        "Используй /add, чтобы создать анкету, и /find для поиска."
    )

@dp.message(Command("help"))
async def cmd_help(message: Message):
    text = (
        "Доступные команды:\n"
        "/start - приветствие\n"
        "/help - эта справка\n"
        "/add - заполнить анкету\n"
        "/find - найти сожителей\n"
        "/cancel - отменить заполнение"
    )
    await message.answer(text)

# ---------- Начало диалога /add ----------
@dp.message(Command("add"))
async def cmd_add(message: Message, state: FSMContext):
    await state.set_state(ProfileForm.name)
    await message.answer("Как тебя зовут?")

# ---------- Шаг 1: Имя ----------
@dp.message(ProfileForm.name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(ProfileForm.gender)
    await message.answer("Какой твой пол? (мужской/женский)")

# ---------- Шаг 2: Пол ----------
@dp.message(ProfileForm.gender)
async def process_gender(message: Message, state: FSMContext):
    await state.update_data(gender=message.text)
    await state.set_state(ProfileForm.age)
    await message.answer("Сколько тебе лет? (введите число)")

# ---------- Шаг 3: Возраст ----------
@dp.message(ProfileForm.age)
async def process_age(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите число (возраст).")
        return
    await state.update_data(age=int(message.text))
    await state.set_state(ProfileForm.city)
    await message.answer("В каком городе ищешь жильё?")

# ---------- Шаг 4: Город ----------
@dp.message(ProfileForm.city)
async def process_city(message: Message, state: FSMContext):
    await state.update_data(city=message.text)
    await state.set_state(ProfileForm.max_rent)
    await message.answer("Какая максимальная арендная плата в месяц (в рублях)?")

# ---------- Шаг 5: Бюджет ----------
@dp.message(ProfileForm.max_rent)
async def process_max_rent(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите число.")
        return
    await state.update_data(max_rent=int(message.text))
    await state.set_state(ProfileForm.preferences)
    await message.answer("Есть ли пожелания по сожителю? (например, некурящий, тишина)")

# ---------- Шаг 6: Предпочтения и сохранение ----------
@dp.message(ProfileForm.preferences)
async def process_preferences(message: Message, state: FSMContext):
    user_data = await state.get_data()
    # Добавляем user_id и сохраняем
    profile = {
        "user_id": message.from_user.id,
        "name": user_data["name"],
        "gender": user_data["gender"],
        "age": user_data["age"],
        "city": user_data["city"],
        "max_rent": user_data["max_rent"],
        "preferences": message.text,
    }
    profiles[message.from_user.id] = profile
    await state.clear()
    await message.answer("Анкета сохранена! Теперь ищи сожителей через /find")

# ---------- Отмена ----------
@dp.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Заполнение анкеты отменено.")

# ---------- Поиск /find ----------
@dp.message(Command("find"))
async def cmd_find(message: Message):
    user_id = message.from_user.id
    if user_id not in profiles:
        await message.answer("Сначала создай анкету через /add")
        return

    my_profile = profiles[user_id]
    city = my_profile["city"]
    matches = [
        p for uid, p in profiles.items()
        if uid != user_id and p["city"].lower() == city.lower()
    ]

    if not matches:
        await message.answer(f"В городе {city} пока нет других анкет.")
        return

    result = "Найдены потенциальные сожители:\n"
    for p in matches:
        result += (
            f"- {p['name']}, {p['age']} лет, "
            f"бюджет до {p['max_rent']} руб., "
            f"предпочтения: {p['preferences']}\n"
        )
    await message.answer(result)

# ---------- Запуск бота в фоновом потоке ----------
def run_bot():
    """Запускает поллинг бота."""
    logger.info("Бот запущен и слушает сообщения...")
    dp.run_polling(bot)

# ---------- Точка входа ----------
if __name__ == "__main__":
    # Запускаем бота в отдельном потоке
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

    # Запускаем Flask в главном потоке для поддержки порта
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Flask сервер запущен на порту {port}")
    flask_app.run(host="0.0.0.0", port=port)