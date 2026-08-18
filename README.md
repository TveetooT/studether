# README — Studether Bot

**Studether** — Telegram-бот для поиска соседа/сожителя среди студентов. Бот позволяет заполнить анкету, указать город, просматривать анкеты других пользователей, ставить лайки и получать взаимные совпадения.

---

## ✨ Возможности

- 📝 Заполнение анкеты: имя, возраст, вуз, о себе, пожелания к соседу, регион и город.
- 👤 Редактирование своей анкеты в любой момент.
- 🔍 Поиск анкет по городу.
- 👍👎 Лайки / дизлайки, уведомления о взаимных симпатиях.
- 📬 Раздел «Запросы на сожительство» — просмотр тех, кто лайкнул вас.
- ⚠️ Жалобы на пользователей.
- ❓ ЧаВо.
- 🔐 Административные команды (очистка БД, диагностика, пересоздание таблиц).
- 🧪 Встроенная самодиагностика (`cmd_selftest`).

---

## 🧱 Технологии

- [aiogram 3.x](https://aiogram.dev/) — фреймворк для Telegram Bot API.
- [aiohttp](https://docs.aiohttp.org/) — веб-сервер для вебхуков.
- [Supabase](https://supabase.com/) (PostgreSQL + REST API) — база данных.
- Python 3.10+

---

## 📋 Требования

- Установленный Python 3.10 или выше.
- Аккаунт Telegram бота (токен от [@BotFather](https://t.me/BotFather)).
- Проект в [Supabase](https://supabase.com/) с доступом к REST API (URL и ключ).

---

## 🚀 Установка и настройка

### 1. Клонирование репозитория

```bash
git clone https://github.com/your/repo.git
cd studether-bot
```

### 2. Установка зависимостей

```bash
pip install -r requirements.txt
```

**requirements.txt**:
```
aiogram
aiohttp
supabase
```

### 3. Переменные окружения

Создайте файл `.env` (или задайте переменные окружения на сервере). Пример:

```env
TELEGRAM_TOKEN=123456:ABC-DEF...
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-or-service-role-key
WEBHOOK_URL=https://your-domain.com/webhook
ROOT_CODE=секретный_код_для_админа
PORT=5000  # по умолчанию 5000, можно изменить
```

- `TELEGRAM_TOKEN` — токен бота.
- `SUPABASE_URL`, `SUPABASE_KEY` — данные для подключения к Supabase.
- `WEBHOOK_URL` — публичный HTTPS URL для вебхука (без него бот не запустится).
- `ROOT_CODE` — строка, отправка которой в чат даёт права администратора бота.
- `PORT` (необязательно) — порт для aiohttp, по умолчанию 5000.

### 4. Настройка Supabase

Необходимо создать таблицы и функции, используемые ботом. Выполните следующие SQL-запросы в SQL Editor вашего проекта Supabase.

#### Таблица `users`
```sql
CREATE TABLE users (
  user_id BIGINT PRIMARY KEY,
  username TEXT,
  form TEXT DEFAULT 'false',
  action TEXT,
  root TEXT DEFAULT 'false',
  name TEXT,
  age INTEGER,
  univer TEXT,
  about TEXT,
  requirements TEXT,
  region TEXT,
  city TEXT,
  reports INTEGER DEFAULT 0
);
```

#### Таблица `views`
```sql
CREATE TABLE views (
  user_id BIGINT,
  viewed_user_id BIGINT,
  state TEXT DEFAULT 'unseen',  -- 'unseen', 'like_unseen', 'seen'
  PRIMARY KEY (user_id, viewed_user_id)
);
```

#### Функция `get_unseen_users`
Функция возвращает случайную анкету пользователя из того же города, которую ещё не просматривал (или не лайкал) текущий пользователь.

```sql
CREATE OR REPLACE FUNCTION get_unseen_users(p_user_id BIGINT, p_city TEXT, p_limit INT)
RETURNS SETOF users AS $$
BEGIN
  RETURN QUERY
  SELECT u.*
  FROM users u
  WHERE u.city = p_city
    AND u.user_id <> p_user_id
    AND u.form = 'true'
    AND NOT EXISTS (
      SELECT 1 FROM views v
      WHERE v.user_id = p_user_id
        AND v.viewed_user_id = u.user_id
        AND v.state IN ('unseen', 'like_unseen', 'seen')
    )
  ORDER BY random()
  LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;
```

> При необходимости можно исключить уже просмотренные анкеты (state = 'seen'), изменив условие `v.state = 'unseen'`.

#### Функция `recreate_database` (опционально, для команды `cmd_recreatedb`)

```sql
CREATE OR REPLACE FUNCTION recreate_database()
RETURNS void AS $$
BEGIN
  DROP TABLE IF EXISTS views;
  DROP TABLE IF EXISTS users;
  CREATE TABLE users (...); -- как выше
  CREATE TABLE views (...);
  -- Пересоздать функцию get_unseen_users после этого
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

Если вам не нужна возможность пересоздания БД из бота, можно пропустить этот шаг.

### 5. Запуск

```bash
python bot.py
```

При запуске бот:
- Удалит старый вебхук и установит новый на указанный `WEBHOOK_URL`.
- Зарегистрирует команды бота.
- Запустит aiohttp-сервер на порту `PORT` с эндпоинтами `/health` и `/webhook`.

---

## 🤖 Использование

### Основные команды

| Команда    | Описание                                            |
|------------|-----------------------------------------------------|
| `/start`   | Запуск бота, регистрация пользователя               |
| `/form`    | Начать заполнение анкеты (или продолжить)           |
| `/profile` | Показать свою анкету с возможностью редактирования  |
| `/menu`    | Открыть главное меню                                |
| `/find`    | Найти сожителя в своём городе                       |
| `/likes`   | Показать пользователей, которые лайкнули вас        |
| `/faq`     | Часто задаваемые вопросы                            |

### Процесс заполнения анкеты

1. Нажмите `/form`.
2. Введите имя, возраст, вуз, описание, пожелания, выберите регион и город (из инлайн-клавиатур).
3. Проверьте анкету и подтвердите («Всё хорошо») или начните заново.
4. После сохранения анкеты можно использовать `/find` для поиска.

### Просмотр анкет и лайки

- При просмотре анкеты вы можете нажать:
  - 👍 — поставить лайк,
  - 👎 — пропустить,
  - ⚠️ Пожаловаться — отправить жалобу.
- Если лайк взаимный, оба пользователя получат уведомление с контактом (username).

### Административные команды

Для получения прав администратора отправьте боту строку `ROOT_CODE` (значение переменной окружения). После этого поле `root` в таблице `users` будет установлено в `'true'`.

Доступные команды администратора (отправляются как обычное сообщение):

| Команда                  | Описание                                                                                    |
|--------------------------|---------------------------------------------------------------------------------------------|
| `cmd_deleteform`         | Удалить свою анкету. Можно указать ID: `cmd_deleteform 123456789`                           |
| `cmd_cleardata`          | Запрос на полную очистку всех данных (требует подтверждения)                                |
| `cmd_cleardata_confirm`  | Подтвердить очистку                                                                         |
| `cmd_recreatedb`         | Запрос на пересоздание таблиц (требует подтверждения и наличия функции `recreate_database`) |
| `cmd_recreatedb_confirm` | Подтвердить пересоздание                                                                    |
| `cmd_selftest`           | Запустить диагностику бота (проверка API, БД, функций)                                      |

---

## 🧪 Диагностика

Команда `cmd_selftest` (доступна только администратору) проверяет:

- соединение с Telegram API,
- чтение таблиц `users` и `views`,
- работу RPC-функции `get_unseen_users`,
- запись и чтение полей,
- очистку тестовых данных.

Результаты выводятся в чат.

---

## 🌐 Деплой

Для работы вебхука необходимо:
- HTTPS-домен (можно использовать [Ngrok](https://ngrok.com/) для локального тестирования).
- Убедиться, что порт, на котором запущен бот, доступен из интернета и проброшен.
- Указать `WEBHOOK_URL` в формате `https://ваш_домен/webhook`.

Пример запуска через systemd, Docker, Heroku и т.п. остаётся на ваше усмотрение.

---

## 📝 TODO / Идеи для улучшения

- Валидация возраста и других полей.
- Обработка не-текстовых сообщений во время заполнения анкеты.
- Улучшение UX: пагинация при выборе региона (слишком много кнопок).
- Отправка взаимных лайков с контактными данными (телефон/Telegram) если пользователь разрешил.
- Интеграция с медиа (фото профиля).

---

## 📄 Лицензия

MIT License. Подробности в файле [LICENSE](LICENSE).