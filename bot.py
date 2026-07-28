import os
import threading
from flask import Flask
from telegram.ext import Updater, CommandHandler

# --- 1. НАСТРОЙКА ВЕБ-СЕРВЕРА (Flask) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!" # Просто для проверки

@app.route('/health')
def health():
    return "OK", 200

# --- 2. КОД ВАШЕГО ТЕЛЕГРАМ-БОТА ---
TOKEN = os.environ.get('TELEGRAM_TOKEN') # Берем токен из переменных окружения!

def start(update, context):
    update.message.reply_text("Привет! Я бот для поиска сожителей!")

def main():
    # Инициализация бота
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    
    # Регистрируем хендлеры
    dp.add_handler(CommandHandler("start", start))
    # ... сюда добавьте все ваши остальные хендлеры ...
    
    # Запускаем бота в режиме long polling в отдельном потоке
    # Это позволит Flask-серверу работать параллельно
    threading.Thread(target=updater.start_polling).start()

if __name__ == '__main__':
    main()
    # Запускаем веб-сервер на порту, который задаст Render
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)