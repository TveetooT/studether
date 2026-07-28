import os
import threading
import logging
from flask import Flask
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    ContextTypes,
)

# ---------- Логирование ----------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------- Переменные окружения ----------
TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TOKEN:
    raise ValueError("Переменная TELEGRAM_TOKEN не задана!")

# ---------- Состояния для ConversationHandler ----------
NAME, GENDER, AGE, CITY, MAX_RENT, PREFERENCES = range(6)

# ---------- Хранилища данных (в памяти) ----------
profiles = {}          # user_id -> dict с анкетой
temp_profile = {}      # временные данные при заполнении

# ---------- Flask-приложение для пинга ----------
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "Бот работает!"

@flask_app.route("/health")
def health():
    return "OK", 200

# ---------- Команды бота ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я помогу найти сожителя.\n"
        "Используй /add, чтобы создать анкету, и /find для поиска."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "Доступные команды:\n"
        "/start - приветствие\n"
        "/help - эта справка\n"
        "/add - заполнить анкету\n"
        "/find - найти сожителей\n"
        "/cancel - отменить заполнение"
    )
    await update.message.reply_text(text)

# ---------- Обработчики ConversationHandler ----------

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    temp_profile[user_id] = {}
    await update.message.reply_text("Как тебя зовут?")
    return NAME

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    temp_profile[user_id]["name"] = update.message.text
    await update.message.reply_text("Какой твой пол? (мужской/женский)")
    return GENDER

async def ask_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    temp_profile[user_id]["gender"] = update.message.text
    await update.message.reply_text("Сколько тебе лет?")
    return AGE

async def ask_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        age = int(update.message.text)
        temp_profile[user_id]["age"] = age
        await update.message.reply_text("В каком городе ищешь жильё?")
        return CITY
    except ValueError:
        await update.message.reply_text("Пожалуйста, введи число (возраст).")
        return AGE

async def ask_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    temp_profile[user_id]["city"] = update.message.text
    await update.message.reply_text("Какая максимальная арендная плата в месяц (в рублях)?")
    return MAX_RENT

async def ask_max_rent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        rent = int(update.message.text)
        temp_profile[user_id]["max_rent"] = rent
        await update.message.reply_text("Есть ли пожелания по сожителю? (например, некурящий, тишина)")
        return PREFERENCES
    except ValueError:
        await update.message.reply_text("Введи число.")
        return MAX_RENT

async def ask_preferences(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    temp_profile[user_id]["preferences"] = update.message.text
    # Сохраняем анкету
    profile = temp_profile[user_id]
    profile["user_id"] = user_id
    profiles[user_id] = profile
    del temp_profile[user_id]
    await update.message.reply_text("Анкета сохранена! Теперь ищи сожителей через /find")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in temp_profile:
        del temp_profile[user_id]
    await update.message.reply_text("Заполнение анкеты отменено.")
    return ConversationHandler.END

# ---------- Команда /find ----------

async def find(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in profiles:
        await update.message.reply_text("Сначала создай анкету через /add")
        return

    my_profile = profiles[user_id]
    city = my_profile["city"]
    matches = [
        p for uid, p in profiles.items()
        if uid != user_id and p["city"].lower() == city.lower()
    ]

    if not matches:
        await update.message.reply_text(f"В городе {city} пока нет других анкет.")
        return

    result = "Найдены потенциальные сожители:\n"
    for p in matches:
        result += (
            f"- {p['name']}, {p['age']} лет, "
            f"бюджет до {p['max_rent']} руб., "
            f"предпочтения: {p['preferences']}\n"
        )
    await update.message.reply_text(result)

# ---------- Запуск бота (в отдельном потоке) ----------

def run_bot():
    """Создаёт Application и запускает поллинг."""
    app = Application.builder().token(TOKEN).build()

    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("find", find))

    # ConversationHandler для /add
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("add", add)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_gender)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_age)],
            CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_city)],
            MAX_RENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_max_rent)],
            PREFERENCES: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_preferences)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(conv_handler)

    logger.info("Бот запущен и слушает сообщения...")
    app.run_polling()

# ---------- Точка входа ----------

if __name__ == "__main__":
    # Запускаем бота в фоновом потоке
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

    # Запускаем Flask-сервер (главный поток)
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Flask сервер запущен на порту {port}")
    flask_app.run(host="0.0.0.0", port=port)