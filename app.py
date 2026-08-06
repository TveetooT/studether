import os
import logging
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    BotCommand,                          
    InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.webhook import aiohttp_server
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

WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

ROOT_CODE = os.environ.get("ROOT_CODE")
# ---------- Подключение к БД ----------
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------- Константы ----------
BOT_NAME = "Studether"

# ---------- Списки ----------
Actions = [
    "name", "age", "univer", "about", "requirements", "confirm"
]

ActionEdit = [
    "nameEdit", "ageEdit", "univerEdit", "aboutEdit", "requirementsEdit",
]

InlineKeyboardActions = [
    "region", "city"
]

InlineKeyboardActionsEdit = [
    "regionEdit", "cityEdit"
]

# ---------- Словари ----------
Phrases = {
    "StartMessage": "👋 Привет! Я робот хD.\nДавай найдем для тебя \nдруга, с которым ты будешь вместе снимать жилье 🏠.\nНачни заполнять анкету в /form",

    "nameMessage1": "Имя, отображаемое в анкете",
    "ageMessage1": "Возраст, отображаемый в анкете",
    "univerMessage1": "Учебное заведение, отображаемое в профиле",
    "aboutMessage1": "Описание профиля",
    "requirementsMessage1": "Пожелания, отображаемые после описания профиля",
    "regionMessage1": "Регион",
    "cityMessage1": "Город, используемый для поиска",

    "nameMessage2": f"Меня зовут Studether. А под каким именем ты хочешь быть видимым для других людей?",
    "ageMessage2": "Сколько тебе лет?",
    "univerMessage2": "Выбери учебное заведение, в котором ты учишься",
    "aboutMessage2": "Добавь информацию к анкете. Можешь рассказать о себе или о том, какую квартиру ищешь. Что бы ты сам(а) хотел(а) знать о своём будущем соседе?",
    "requirementsMessage2": "Очень чистоплотен/чистоплотна, или наоборот наплевать, сколько носков валяется на полу? Жить вдвоём или целой казармой? Хочешь соседа, с которым интересно поговорить, или перекидываться взглядами раз в день? Расскажи, каким/какой бы ты хотел(а) видеть будущего соседа.",
    "regionMessage2": "Для поиска нужно указать город, в котором ты собираешься снимать квартиру, но сначала укажи регион, в котором этот город находится",
    "cityMessage2": "В каком городе ты собираешься снимать квартиру?",

    "confirmMessage": "Проверь свою анкету",

    "FormSaved": "Анкета сохранена! Теперь ты можешь искать соседей через /find.",
    "Menu": "Ты в меню. Выбери действие на клавиатуре",

    "RootCode": "Спидозные козявки"
}

# ---------- Кнопки ----------
# ---------- главное меню ----------
MainButtons = {
    "Profile": "👤 Моя анкета",
    "Find": "🔍 Найти сожителя",
}

# ---------- Подтверждение анкеты ----------
FormButtons = { #В названии переменной сначала идёт клавиатура к которой привязана кнопка, потом действие
    "Confirm": "Всё хорошо",
    "Restart": "Заполнить заново",
}

# ---------- Редактирование анкеты ----------
EditButtons = {
    "name": "Изменить имя",
    "age": "Изменить возраст",
    "univer": "Изменить учебное заведение",
    "about": "Изменить описание",
    "requirements": "Изменить пожелания",
    "city": "Изменить город",

}

# ---------- Просмотр анкеты ----------
ViewButtons = {
    "like": "👍",
    "dislike": "👎",
    "report": "⚠️ Пожаловаться"
}

# ---------- Кнопка назад ----------
ReturnButton = {
    "Return": "⬅️ Назад",}

NextAction = { 
    "name": "age",
    "age": "univer",
    "univer": "about",
    "about": "requirements",
    "requirements": "region",
    "region": "city",
    "city": "confirm",
}

CommandMenu = {
    "start": "Запустить бота",
    "profile": "Вывести анкету",
    "form": "Заполнить анкету",
    "menu": "Меню",
    "find": "Найти сожителя",
}

Regions = {
    "Республика Адыгея": [
        "Майкоп", "Адыгейск"
    ],
    "Республика Алтай": [
        "Горно-Алтайск"
    ],
    "Республика Башкортостан": [
        "Уфа", "Агидель", "Баймак", "Белебей", "Белорецк", "Бирск", "Благовещенск",
        "Давлеканово", "Дюртюли", "Ишимбай", "Кумертау", "Межгорье", "Мелеуз",
        "Нефтекамск", "Октябрьский", "Салават", "Сибай", "Стерлитамак", "Туймазы",
        "Учалы", "Янаул"
    ],
    "Республика Бурятия": [
        "Улан-Удэ", "Бабушкин", "Гусиноозёрск", "Закаменск", "Кяхта", "Северобайкальск"
    ],
    "Республика Дагестан": [
        "Махачкала", "Буйнакск", "Дагестанские Огни", "Дербент", "Избербаш", "Каспийск",
        "Кизилюрт", "Кизляр", "Хасавюрт", "Южно-Сухокумск"
    ],
    "Республика Ингушетия": [
        "Магас", "Карабулак", "Малгобек", "Назрань"
    ],
    "Кабардино-Балкарская Республика": [
        "Нальчик", "Баксан", "Майский", "Нарткала", "Прохладный", "Терек", "Тырныауз", "Чегем"
    ],
    "Республика Калмыкия": [
        "Элиста", "Городовиковск", "Лагань"
    ],
    "Карачаево-Черкесская Республика": [
        "Черкесск", "Карачаевск", "Теберда", "Усть-Джегута"
    ],
    "Республика Карелия": [
        "Петрозаводск", "Беломорск", "Кемь", "Кондопога", "Костомукша",
        "Лахденпохья", "Медвежьегорск", "Олонец", "Питкяранта", "Пудож",
        "Сегежа", "Сортавала", "Суоярви"
    ],
    "Республика Коми": [
        "Сыктывкар", "Воркута", "Вуктыл", "Емва", "Инта", "Микунь",
        "Печора", "Сосногорск", "Усинск", "Ухта"
    ],
    "Республика Крым": [
        "Симферополь", "Алупка", "Алушта", "Армянск", "Бахчисарай", "Белогорск",
        "Джанкой", "Евпатория", "Керчь", "Красноперекопск", "Саки", "Старый Крым",
        "Судак", "Феодосия", "Щёлкино", "Ялта"
    ],
    "Республика Марий Эл": [
        "Йошкар-Ола", "Волжск", "Звенигово", "Козьмодемьянск"
    ],
    "Республика Мордовия": [
        "Саранск", "Ардатов", "Инсар", "Ковылкино", "Краснослободск", "Рузаевка", "Темников"
    ],
    "Республика Саха (Якутия)": [
        "Якутск", "Алдан", "Верхоянск", "Вилюйск", "Ленск", "Мирный",
        "Нерюнгри", "Нюрба", "Олёкминск", "Покровск", "Среднеколымск", "Томмот",
        "Удачный"
    ],
    "Республика Северная Осетия — Алания": [
        "Владикавказ", "Алагир", "Ардон", "Беслан", "Дигора", "Моздок"
    ],
    "Республика Татарстан": [
        "Казань", "Азнакаево", "Альметьевск", "Арск", "Бавлы", "Болгар", "Бугульма",
        "Буинск", "Елабуга", "Заинск", "Зеленодольск", "Иннополис", "Лаишево",
        "Лениногорск", "Мамадыш", "Менделеевск", "Мензелинск", "Набережные Челны",
        "Нижнекамск", "Нурлат", "Тетюши", "Чистополь"
    ],
    "Республика Тыва": [
        "Кызыл", "Ак-Довурак", "Туран", "Чадан", "Шагонар"
    ],
    "Удмуртская Республика": [
        "Ижевск", "Воткинск", "Глазов", "Камбарка", "Можга", "Сарапул"
    ],
    "Республика Хакасия": [
        "Абакан", "Абаза", "Саяногорск", "Сорск", "Черногорск"
    ],
    "Чеченская Республика": [
        "Грозный", "Аргун", "Гудермес", "Курчалой", "Урус-Мартан", "Шали"
    ],
    "Чувашская Республика": [
        "Чебоксары", "Алатырь", "Канаш", "Козловка", "Мариинский Посад", "Новочебоксарск", "Цивильск", "Шумерля", "Ядрин"
    ],
    "Алтайский край": [
        "Барнаул", "Алейск", "Белокуриха", "Бийск", "Горняк", "Заринск", "Змеиногорск",
        "Камень-на-Оби", "Новоалтайск", "Рубцовск", "Славгород", "Яровое"
    ],
    "Забайкальский край": [
        "Чита", "Балей", "Борзя", "Краснокаменск", "Могоча", "Нерчинск", "Петровск-Забайкальский",
        "Сретенск", "Хилок", "Шилка"
    ],
    "Камчатский край": [
        "Петропавловск-Камчатский", "Вилючинск", "Елизово"
    ],
    "Краснодарский край": [
        "Краснодар", "Абинск", "Анапа", "Апшеронск", "Армавир", "Белореченск", "Геленджик",
        "Горячий Ключ", "Гулькевичи", "Ейск", "Кореновск", "Кропоткин", "Крымск",
        "Лабинск", "Новокубанск", "Новороссийск", "Приморско-Ахтарск", "Славянск-на-Кубани",
        "Сочи", "Темрюк", "Тимашёвск", "Тихорецк", "Туапсе", "Усть-Лабинск", "Хадыженск"
    ],
    "Красноярский край": [
        "Красноярск", "Артёмовск", "Ачинск", "Боготол", "Бородино", "Дивногорск",
        "Дудинка", "Енисейск", "Железногорск", "Заозёрный", "Зеленогорск", "Игарка",
        "Иланский", "Канск", "Кодинск", "Лесосибирск", "Минусинск", "Назарово",
        "Норильск", "Сосновоборск", "Ужур", "Уяр", "Шарыпово"
    ],
    "Пермский край": [
        "Пермь", "Александровск", "Березники", "Верещагино", "Горнозаводск", "Гремячинск",
        "Губаха", "Добрянка", "Кизел", "Красновишерск", "Краснокамск", "Кудымкар",
        "Кунгур", "Лысьва", "Нытва", "Оса", "Оханск", "Очёр", "Соликамск", "Усолье",
        "Чайковский", "Чердынь", "Чёрмоз", "Чернушка", "Чусовой"
    ],
    "Приморский край": [
        "Владивосток", "Арсеньев", "Артём", "Большой Камень", "Дальнегорск", "Дальнереченск",
        "Лесозаводск", "Находка", "Партизанск", "Спасск-Дальний", "Уссурийск", "Фокино"
    ],
    "Ставропольский край": [
        "Ставрополь", "Благодарный", "Будённовск", "Георгиевск", "Ессентуки", "Железноводск",
        "Зеленокумск", "Изобильный", "Ипатово", "Кисловодск", "Лермонтов", "Минеральные Воды",
        "Михайловск", "Невинномысск", "Нефтекумск", "Новоалександровск", "Новопавловск",
        "Пятигорск", "Светлоград"
    ],
    "Хабаровский край": [
        "Хабаровск", "Амурск", "Бикин", "Вяземский", "Комсомольск-на-Амуре", "Николаевск-на-Амуре",
        "Советская Гавань"
    ],
    "Амурская область": [
        "Благовещенск", "Белогорск", "Завитинск", "Зея", "Райчихинск", "Свободный",
        "Сковородино", "Тында", "Циолковский", "Шимановск"
    ],
    "Архангельская область": [
        "Архангельск", "Вельск", "Каргополь", "Коряжма", "Котлас",
        "Мезень", "Мирный", "Новодвинск", "Няндома", "Онега",
        "Северодвинск", "Сольвычегодск", "Шенкурск"
    ],
    "Астраханская область": [
        "Астрахань", "Ахтубинск", "Знаменск", "Камызяк", "Нариманов", "Харабали"
    ],
    "Белгородская область": [
        "Белгород", "Алексеевка", "Бирюч", "Валуйки", "Грайворон", "Губкин",
        "Короча", "Новый Оскол", "Старый Оскол", "Строитель", "Шебекино"
    ],
    "Брянская область": [
        "Брянск", "Дятьково", "Жуковка", "Злынка", "Карачев", "Клинцы",
        "Мглин", "Новозыбков", "Почеп", "Севск", "Стародуб", "Сураж", "Трубчевск", "Унеча"
    ],
    "Владимирская область": [
        "Владимир", "Александров", "Вязники", "Гороховец", "Гусь-Хрустальный",
        "Камешково", "Карабаново", "Киржач", "Ковров", "Кольчугино",
        "Костерево", "Курлово", "Лакинск", "Меленки", "Муром",
        "Петушки", "Покров", "Радужный", "Собинка", "Струнино", "Судогда", "Суздаль", "Юрьев-Польский"
    ],
    "Волгоградская область": [
        "Волгоград", "Волжский", "Дубовка", "Жирновск", "Калач-на-Дону", "Камышин",
        "Котельниково", "Котово", "Краснослободск", "Ленинск", "Михайловка",
        "Николаевск", "Новоаннинский", "Палласовка", "Петров Вал", "Серафимович",
        "Суровикино", "Урюпинск", "Фролово"
    ],
    "Вологодская область": [
        "Вологда", "Бабаево", "Белозерск", "Великий Устюг", "Вытегра",
        "Грязовец", "Кадников", "Кириллов", "Красавино", "Никольск",
        "Сокол", "Тотьма", "Устюжна", "Харовск", "Череповец"
    ],
    "Воронежская область": [
        "Воронеж", "Бобров", "Богучар", "Борисоглебск", "Бутурлиновка",
        "Калач", "Лиски", "Нововоронеж", "Новохопёрск", "Острогожск",
        "Павловск", "Поворино", "Россошь", "Семилуки", "Эртиль"
    ],
    "Ивановская область": [
        "Иваново", "Вичуга", "Гаврилов Посад", "Заволжск", "Кинешма",
        "Комсомольск", "Кохма", "Наволоки", "Плёс", "Приволжск",
        "Пучеж", "Родники", "Тейково", "Фурманов", "Шуя", "Южа", "Юрьевец"
    ],
    "Иркутская область": [
        "Иркутск", "Алзамай", "Ангарск", "Байкальск", "Бирюсинск", "Бодайбо",
        "Братск", "Вихоревка", "Железногорск-Илимский", "Зима", "Киренск",
        "Нижнеудинск", "Саянск", "Свирск", "Слюдянка", "Тайшет",
        "Тулун", "Усолье-Сибирское", "Усть-Илимск", "Усть-Кут", "Черемхово", "Шелехов"
    ],
    "Калининградская область": [
        "Калининград", "Багратионовск", "Балтийск", "Гвардейск", "Гурьевск",
        "Гусев", "Зеленоградск", "Краснознаменск_", "Ладушкин", "Мамоново",
        "Неман", "Нестеров", "Озёрск", "Пионерский", "Полесск",
        "Правдинск", "Приморск", "Светлогорск", "Светлый", "Славск",
        "Советск", "Черняховск"
    ],
    "Калужская область": [
        "Калуга", "Балабаново", "Белоусово", "Боровск", "Ермолино",
        "Жиздра", "Жуков", "Киров_", "Козельск", "Кондрово",
        "Кремёнки", "Людиново", "Малоярославец", "Медынь", "Мещовск",
        "Мосальск", "Обнинск", "Сосенский", "Спас-Деменск", "Сухиничи",
        "Таруса", "Юхнов"
    ],
    "Кемеровская область — Кузбасс": [
        "Кемерово", "Анжеро-Судженск", "Белово", "Берёзовский", "Гурьевск",
        "Калтан", "Киселёвск", "Ленинск-Кузнецкий", "Мариинск", "Междуреченск",
        "Мыски", "Новокузнецк", "Осинники", "Полысаево", "Прокопьевск",
        "Салаир", "Тайга", "Таштагол", "Топки", "Юрга"
    ],
    "Кировская область": [
        "Киров", "Белая Холуница", "Вятские Поляны", "Зуевка", "Кирово-Чепецк",
        "Кирс", "Котельнич", "Луза", "Малмыж", "Мураши", "Нолинск",
        "Омутнинск", "Орлов", "Слободской", "Советск_", "Сосновка", "Уржум", "Яранск"
    ],
    "Костромская область": [
        "Кострома", "Буй", "Волгореченск", "Галич", "Кологрив", "Макарьев",
        "Мантурово", "Нерехта", "Нея", "Солигалич", "Чухлома", "Шарья"
    ],
    "Курганская область": [
        "Курган", "Далматово", "Катайск", "Куртамыш", "Макушино", "Петухово",
        "Шадринск", "Шумиха", "Щучье"
    ],
    "Курская область": [
        "Курск", "Дмитриев", "Железногорск", "Курчатов", "Льгов",
        "Обоянь", "Рыльск", "Суджа", "Фатеж", "Щигры"
    ],
    "Ленинградская область": [
        "Санкт-Петербург",
        "Бокситогорск", "Волосово", "Волхов", "Всеволожск", "Выборг",
        "Высоцк", "Гатчина", "Ивангород", "Каменногорск", "Кингисепп",
        "Кириши", "Кировск", "Коммунар", "Кудрово", "Лодейное Поле",
        "Луга", "Любань", "Мурино", "Никольское", "Новая Ладога",
        "Отрадное", "Пикалёво", "Подпорожье", "Приморск_", "Приозерск",
        "Светогорск", "Сертолово", "Сланцы", "Сосновый Бор", "Тихвин",
        "Тосно", "Шлиссельбург"
    ],
    "Липецкая область": [
        "Липецк", "Грязи", "Данков", "Елец", "Задонск", "Лебедянь", "Усмань", "Чаплыгин"
    ],
    "Магаданская область": [
        "Магадан", "Сусуман"
    ],
    "Московская область": [
        "Москва",
        "Апрелевка", "Балашиха", "Белоозёрский", "Бронницы", "Верея",
        "Видное", "Волоколамск", "Воскресенск", "Высоковск", "Голицыно",
        "Дедовск", "Дзержинский", "Дмитров", "Долгопрудный", "Домодедово",
        "Дрезна", "Дубна", "Егорьевск", "Жуковский", "Зарайск",
        "Звенигород", "Ивантеевка", "Истра", "Кашира", "Клин",
        "Коломна", "Королёв", "Котельники", "Красноармейск", "Красногорск",
        "Краснозаводск", "Краснознаменск", "Кубинка", "Куровское", "Лыткарино",
        "Люберцы", "Можайск", "Мытищи", "Наро-Фоминск", "Ногинск",
        "Одинцово", "Озёры", "Орехово-Зуево", "Павловский Посад", "Пересвет",
        "Подольск", "Протвино", "Пушкино", "Пущино", "Раменское",
        "Реутов", "Рошаль", "Руза", "Сергиев Посад", "Серпухов",
        "Солнечногорск", "Старая Купавна", "Ступино", "Талдом", "Фрязино",
        "Химки", "Хотьково", "Черноголовка", "Чехов", "Шатура",
        "Щёлково", "Электрогорск", "Электросталь", "Электроугли", "Юбилейный",
        "Яхрома"
    ],
    "Мурманская область": [
        "Мурманск", "Апатиты", "Гаджиево", "Заозёрск", "Заполярный",
        "Кандалакша", "Кировск", "Ковдор", "Кола", "Мончегорск",
        "Оленегорск", "Островной", "Полярные Зори", "Полярный", "Североморск",
        "Снежногорск"
    ],
    "Нижегородская область": [
        "Нижний Новгород", "Арзамас", "Балахна", "Богородск", "Бор",
        "Ветлуга", "Володарск", "Ворсма", "Выкса", "Горбатов",
        "Городец", "Дзержинск", "Заволжье", "Княгинино", "Кстово",
        "Кулебаки", "Лукоянов", "Лысково", "Навашино", "Павлово",
        "Первомайск", "Перевоз", "Саров", "Семёнов", "Сергач",
        "Урень", "Чкаловск", "Шахунья"
    ],
    "Новгородская область": [
        "Великий Новгород", "Боровичи", "Валдай", "Малая Вишера", "Окуловка",
        "Пестово", "Сольцы", "Старая Русса", "Холм", "Чудово"
    ],
    "Новосибирская область": [
        "Новосибирск", "Барабинск", "Бердск", "Болотное", "Искитим",
        "Карасук", "Каргат", "Куйбышев", "Купино", "Обь",
        "Татарск", "Тогучин", "Черепаново", "Чулым"
    ],
    "Омская область": [
        "Омск", "Исилькуль", "Калачинск", "Называевск", "Тара", "Тюкалинск"
    ],
    "Оренбургская область": [
        "Оренбург", "Абдулино", "Бугуруслан", "Бузулук", "Гай",
        "Кувандык", "Медногорск", "Новотроицк", "Орск", "Соль-Илецк",
        "Сорочинск", "Ясный"
    ],
    "Орловская область": [
        "Орёл", "Болхов", "Дмитровск", "Ливны", "Малоархангельск", "Мценск", "Новосиль"
    ],
    "Пензенская область": [
        "Пенза", "Белинский", "Городище", "Заречный", "Каменка", "Кузнецк",
        "Нижний Ломов", "Никольск", "Сердобск", "Спасск", "Сурск"
    ],
    "Псковская область": [
        "Псков", "Великие Луки", "Гдов", "Дно", "Невель", "Новоржев",
        "Новосокольники", "Опочка", "Остров", "Печоры", "Порхов",
        "Пустошка", "Пыталово", "Себеж"
    ],
    "Ростовская область": [
        "Ростов-на-Дону", "Азов", "Аксай", "Батайск", "Белая Калитва",
        "Волгодонск", "Гуково", "Донецк", "Зверево", "Зерноград",
        "Каменск-Шахтинский", "Константиновск", "Красный Сулин", "Миллерово",
        "Морозовск", "Новочеркасск", "Новошахтинск", "Пролетарск",
        "Сальск", "Семикаракорск", "Таганрог", "Цимлянск", "Шахты"
    ],
    "Рязанская область": [
        "Рязань", "Касимов", "Кораблино", "Михайлов", "Новомичуринск",
        "Рыбное", "Ряжск", "Сасово", "Скопин", "Спас-Клепики", "Спасск-Рязанский", "Шацк"
    ],
    "Самарская область": [
        "Самара", "Жигулёвск", "Кинель", "Нефтегорск", "Новокуйбышевск",
        "Октябрьск", "Отрадный", "Похвистнево", "Сызрань", "Тольятти", "Чапаевск"
    ],
    "Саратовская область": [
        "Саратов", "Аркадак", "Аткарск", "Балаково", "Балашов",
        "Вольск", "Ершов", "Калининск", "Красноармейск", "Красный Кут",
        "Маркс", "Новоузенск", "Петровск", "Пугачёв", "Ртищево", "Хвалынск", "Шиханы", "Энгельс"
    ],
    "Сахалинская область": [
        "Южно-Сахалинск", "Александровск-Сахалинский", "Анива", "Долинск",
        "Корсаков", "Курильск", "Макаров", "Невельск", "Оха",
        "Поронайск", "Северо-Курильск", "Томари", "Углегорск", "Холмск", "Шахтёрск"
    ],
    "Свердловская область": [
        "Екатеринбург", "Алапаевск", "Арамиль", "Артёмовский", "Асбест",
        "Берёзовский", "Богданович", "Верхний Тагил", "Верхняя Пышма",
        "Верхняя Салда", "Верхняя Тура", "Верхотурье", "Волчанск",
        "Дегтярск", "Заречный", "Ивдель", "Ирбит", "Каменск-Уральский",
        "Камышлов", "Карпинск", "Качканар", "Кировград", "Краснотурьинск",
        "Красноуральск", "Красноуфимск", "Кушва", "Лесной", "Михайловск",
        "Невьянск", "Нижние Серги", "Нижний Тагил", "Нижняя Салда",
        "Нижняя Тура", "Новая Ляля", "Новоуральск", "Первоуральск",
        "Полевской", "Ревда", "Реж", "Североуральск", "Серов",
        "Среднеуральск", "Сухой Лог", "Сысерть", "Тавда", "Талица",
        "Туринск"
    ],
    "Смоленская область": [
        "Смоленск", "Велиж", "Вязьма", "Гагарин", "Демидов", "Десногорск",
        "Дорогобуж", "Духовщина", "Ельня", "Починок", "Рославль",
        "Рудня", "Сафоново", "Сычёвка", "Ярцево"
    ],
    "Тамбовская область": [
        "Тамбов", "Жердевка", "Кирсанов", "Котовск", "Мичуринск",
        "Моршанск", "Рассказово", "Уварово"
    ],
    "Тверская область": [
        "Тверь", "Андреаполь", "Бежецк", "Белый", "Бологое", "Весьегонск",
        "Вышний Волочёк", "Западная Двина", "Зубцов", "Калязин",
        "Кашин", "Кимры", "Конаково", "Красный Холм", "Кувшиново",
        "Лихославль", "Нелидово", "Осташков", "Ржев", "Старица",
        "Торжок", "Торопец", "Удомля"
    ],
    "Томская область": [
        "Томск", "Асино", "Кедровый", "Колпашево", "Северск", "Стрежевой"
    ],
    "Тульская область": [
        "Тула", "Алексин", "Белёв", "Богородицк", "Болохово",
        "Венёв", "Донской", "Ефремов", "Кимовск", "Киреевск",
        "Липки", "Новомосковск", "Плавск", "Советск__", "Суворов",
        "Узловая", "Чекалин", "Щёкино", "Ясногорск"
    ],
    "Тюменская область": [
        "Тюмень", "Заводоуковск", "Ишим", "Тобольск", "Ялуторовск"
    ],
    "Ульяновская область": [
        "Ульяновск", "Барыш", "Димитровград", "Инза", "Новоульяновск", "Сенгилей"
    ],
    "Челябинская область": [
        "Челябинск", "Аша", "Бакал", "Верхнеуральск", "Верхний Уфалей",
        "Еманжелинск", "Златоуст", "Карабаш", "Карталы", "Касли",
        "Катав-Ивановск", "Копейск", "Коркино", "Куса", "Кыштым",
        "Магнитогорск", "Миасс", "Миньяр", "Нязепетровск", "Озёрск",
        "Пласт", "Сатка", "Сим", "Снежинск", "Трёхгорный", "Троицк",
        "Усть-Катав", "Чебаркуль", "Южноуральск", "Юрюзань"
    ],
    "Ярославская область": [
        "Ярославль", "Гаврилов-Ям", "Данилов", "Любим", "Мышкин",
        "Переславль-Залесский", "Пошехонье", "Ростов", "Рыбинск", "Тутаев", "Углич"
    ],
    "Севастополь": [
        "Севастополь"
    ],
    "Ненецкий автономный округ": [
        "Нарьян-Мар"
    ],
    "Ханты-Мансийский автономный округ — Югра": [
        "Ханты-Мансийск", "Белоярский", "Когалым", "Лангепас", "Лянтор",
        "Мегион", "Нефтеюганск", "Нижневартовск", "Нягань", "Покачи",
        "Пыть-Ях", "Радужный", "Советский", "Сургут", "Урай", "Югорск"
    ],
    "Чукотский автономный округ": [
        "Анадырь", "Билибино", "Певек"
    ],
    "Ямало-Ненецкий автономный округ": [
        "Салехард", "Губкинский", "Лабытнанги", "Муравленко", "Надым",
        "Новый Уренгой", "Ноябрьск", "Тарко-Сале"
    ],
    "Донецкая Народная Республика": [
        "Донецк", "Горловка", "Дебальцево", "Докучаевск", "Енакиево",
        "Ждановка", "Кировское", "Макеевка", "Мариуполь", "Снежное",
        "Торез", "Углегорск_", "Харцызск", "Шахтёрск", "Ясиноватая"
    ],
    "Луганская Народная Республика": [
        "Луганск", "Алмазная", "Алчевск", "Антрацит", "Брянка",
        "Кировск", "Краснодон", "Красный Луч", "Лисичанск", "Первомайск",
        "Ровеньки", "Рубежное", "Свердловск", "Северодонецк", "Стаханов",
        "Суходольск"
    ],
    "Запорожская область": [
        "Мелитополь", "Бердянск", "Токмак", "Энергодар", "Пологи", "Васильевка", "Каменка-Днепровская"
    ],
    "Херсонская область": [
        "Херсон", "Геническ", "Каховка", "Новая Каховка", "Скадовск", "Голая Пристань", "Алёшки"
    ]
}

# ---------- Reply Клавиатуры ----------
# ---------- Главная клавиатура ----------
MainReplyKeyboardBuilder = ReplyKeyboardBuilder()
for text in MainButtons:
    MainReplyKeyboardBuilder.button(text=MainButtons[text])
MainReplyKeyboardBuilder.adjust(1, 2) #Столбцы, ряды
MainMenuKeyboard = MainReplyKeyboardBuilder.as_markup(resize_keyboard=True)
# ---------- Клавиатура в конце анкеты ----------
FormConfirmKeyboardBuilder = ReplyKeyboardBuilder()
for text in FormButtons:
    FormConfirmKeyboardBuilder.button(text=FormButtons[text])
FormConfirmKeyboardBuilder.adjust(1, 2)
FormConfirmKeyboard = FormConfirmKeyboardBuilder.as_markup(resize_keyboard=True, one_time_keyboard=True)
# ---------- Клавиатура в анкете ----------
FormReturnKeyboardBuilder = ReplyKeyboardBuilder()
FormReturnKeyboardBuilder.button(text=ReturnButton["Return"])
FormReturnKeyboard = FormReturnKeyboardBuilder.as_markup(resize_keyboard=True, one_time_keyboard=True)

# ---------- Inline Клавиатуры ----------
# ---------- Выбор региона ----------
RegionInlineKeyboardBuilder = InlineKeyboardBuilder()
region_keys = list(Regions.keys())  
for idx, region in enumerate(region_keys):
    RegionInlineKeyboardBuilder.button(text=region, callback_data=f"reg_{idx}" )
RegionInlineKeyboardBuilder.adjust(1)
RegionInlineKeyboard = RegionInlineKeyboardBuilder.as_markup()
# ---------- Редактирование анкеты ----------
FormEditKeyboardBuilder = InlineKeyboardBuilder()
for text in EditButtons:
    FormEditKeyboardBuilder.button(text=EditButtons[text], callback_data=f"edit_{text}")
FormEditKeyboardBuilder.adjust(1, 2)
FormEditKeyboard = FormEditKeyboardBuilder.as_markup(resize_keyboard=True, one_time_keyboard=True)
# ---------- Просмотр анкеты ----------
FormViewKeyboardBuilder = InlineKeyboardBuilder()
for text in ViewButtons:
    FormViewKeyboardBuilder.button(text=ViewButtons[text], callback_data=f"view_{text}")
FormViewKeyboardBuilder.adjust(1)
FormViewKeyboard = FormViewKeyboardBuilder.as_markup(resize_keyboard=True, one_time_keyboard=True)

# ---------- Выбор города ----------
Cities = {}
for region in region_keys:
    builder = InlineKeyboardBuilder()
    for city in Regions[region]:
        builder.button(text=city, callback_data=f"city_{city}")
    builder.adjust(1)
    Cities[region] = builder.as_markup()   
    
# ---------- Функция для БД ----------
#--------- Добавляем нового пользователя ----------
def new_user_sync(user_id: int):
    response = supabase.table("users").upsert(
        {"user_id": user_id}, on_conflict="user_id"
    ).execute()

async def set_string_field(user_id: int, field: str, value: str, table: str = "users", additional_field: str=None, additional_value: str=None):
    def _update():
        if additional_field is not None and additional_value is not None:
            return supabase.table(table).update({field: value}).eq("user_id", user_id).eq(additional_field, additional_value).execute()
        return supabase.table(table).update({field: value}).eq("user_id", user_id).execute()
    await asyncio.to_thread(_update)

async def set_int_field(user_id: int, field: str, value: int, table: str = "users", additional_field: str=None, additional_value: int=None):
    def _update():
        if additional_field is not None and additional_value is not None:
            return supabase.table(table).update({field: value}).eq("user_id", user_id).eq(additional_field, additional_value).execute()
        return supabase.table(table).update({field: value}).eq("user_id", user_id).execute()
    await asyncio.to_thread(_update)


# ---------- Получаем поле из БД ----------
async def get_field(user_id: int, field: str):
    def _select():
        return supabase.table("users").select(field).eq("user_id", user_id).execute()
    try:
        response = await asyncio.to_thread(_select)
        if response.data:
            return response.data[0][field]
        return None
    except Exception as e:
        return None

# ---------- Получаем пользователя ----------
def get_user_sync(user_id: int) -> dict | None:
    response = supabase.table("users").select("*").eq("user_id", user_id).execute()
    if response.data:
        return response.data[0] 
    return None

# ---------- Удаляем пользователя ----------
def delete_user_sync(user_id: int):
    response = supabase.table("users").delete().eq("user_id", user_id).execute()

# ---------- Добавляем просмотр ----------
async def add_view(user_id: int, viewed_user_id: int):
    def _update():
        response = supabase.table("views").upsert({"user_id": user_id, "viewed_user_id": viewed_user_id}, on_conflict="user_id,viewed_user_id").execute()
        return response
    await asyncio.to_thread(_update)

# ---------- Получаем анкету ----------
async def get_unseen_form(user_id: int, city: str):
    def _sync():
        response = supabase.rpc("get_unseen_users", {"p_user_id": user_id, "p_city": city, "p_limit": 1}).execute()
        if response.data:
            return response.data[0]
        return None
    form = await asyncio.to_thread(_sync)
    if form:
        await add_view(user_id, form["user_id"])
    return form

# ---------- Выводим и получаем вопрос в анкете ----------
async def form_question(message: types.Message):
    text = message.text
    user_id = message.from_user.id
    action = await get_field(user_id, "action")
    nextaction = NextAction[action]
    reply = None
    await set_string_field(user_id, action, text)
    if nextaction == "region":
        reply = RegionInlineKeyboard
    if nextaction == "city":
        reply = Cities[await get_field(user_id, "region")]
    if await get_field(user_id, "form") != "true": #Если проходим анкету впервые выводим приветливые сообщения
        await message.answer(Phrases[nextaction+"Message2"])
    await message.answer(Phrases[nextaction+"Message1"], reply_markup=reply)
    await set_string_field(user_id, "action", nextaction)
    if nextaction == "confirm":
        await message.answer(await print_profile(user_id=user_id), reply_markup=FormConfirmKeyboard, parse_mode="HTML")

# ---------- Редактируем анкету ----------
async def form_edit(message: types.Message, action: str):
    user_id = message.from_user.id
    text = message.text
    await set_string_field(user_id, action, text)
    await message.answer(await print_profile(user_id=user_id), reply_markup=FormEditKeyboard, parse_mode="HTML")

# ----------- Выводим профиль -----------
async def print_profile(user_id=None, data=None):
    if data is None:
        data = await asyncio.to_thread(get_user_sync, user_id)
    if data:
        name = data.get("name")
        age = data.get("age")
        univer = data.get("univer")
        about = data.get("about")
        requirements = data.get("requirements")
        yearword = ""
        if age is None:
            age = ""
        elif age < 5:
            yearword = "года"
        elif age < 21:
            yearword = "лет"
        elif age % 10 == 1 and age % 100 != 11:
            yearword = "год"
        elif age % 10 in [2, 3, 4] and age % 100 not in [12, 13, 14]:
            yearword = "года"
        else:
            yearword = "лет"
        return (
            f"<b>{name}</b>, {age} {yearword} | {univer}\n\n"
            f"<b>О себе: </b>\n"
            f"<i>{about}</i>\n\n"
            f"<b>Пожелания к соседу: </b>\n"
            f"<i>{requirements}</i>\n\n"
        )
    return None


# ----------- Возращаемся в меню -----------
async def print_menu(message: types.Message):
    await message.answer(Phrases["Menu"], reply_markup=MainMenuKeyboard)

# ----------- Старт анкеты -----------
async def start_form(message: types.Message, user_id: int):
    await message.answer(Phrases['nameMessage1'])
    if await get_field(user_id, "form") != "true":
        await message.answer(Phrases['nameMessage2'])
    await set_string_field(user_id, "action", "name")

# ----------- Меню команд -----------
async def set_commands(bot: Bot):
    commands = []
    for command in CommandMenu:
        commands.append(BotCommand(command=command, description=CommandMenu[command]))
    await bot.set_my_commands(commands)

# ---------- Бот и диспетчер ----------
bot = Bot(token=TOKEN)
dp = Dispatcher()

# ---------- Команды ----------
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    await asyncio.to_thread(new_user_sync, user_id)
    await add_view(user_id, user_id) #Что бы не показывать анкету самому себе
    await message.answer(Phrases['StartMessage'])

async def cmd_form(message: types.Message, user_id= None):
    if message.from_user.id == user_id and user_id is not None:
        await message.answer(f"Город поиска: {await get_field(user_id, 'city')}({await get_field(user_id, 'region')})")
    if user_id is None:
        user_id = message.from_user.id
    else:
        user_id = int(user_id)
    text = await print_profile(user_id=user_id)
    if text is not None:
        await message.answer(text, parse_mode="HTML", reply_markup=FormEditKeyboard)
    else:
        await message.answer("Профиль не существует")

async def cmd_menu(message: types.Message):
     await print_menu(message)

async def cmd_test(message: types.Message):
    TestIKB = InlineKeyboardBuilder()
    TestIKB.button(text="testText", callback_data="testCD")
    TestIKB.adjust(1)
    TestIK = TestIKB.as_markup()
    await message.answer("TestAnswer", reply_markup=TestIK)

async def cmd_find(message: types.Message, user_id=None):
    if user_id is None:
        user_id = message.from_user.id
    city = await get_field(user_id, "city")
    if city is None:
        await message.answer("Вы не указали город поиска. Пожалуйста, заполните анкету.")
        return
    form = await get_unseen_form(user_id, city)
    if form is None:
        await message.answer("Нет доступных анкет для просмотра в вашем городе.")
        return
    profile_text = await print_profile(data=form)
    if profile_text is not None:
        await message.answer(profile_text, parse_mode="HTML", reply_markup=FormViewKeyboard)
    else:
        await message.answer("Ошибка при получении профиля.")
    await set_string_field(user_id, "action", f"viewing_{form.get('user_id')}")
# ----------- Обработка команд -------------
async def command(message: types.Message):
    text = message.text
    if text == "/start":
        await cmd_start(message)
    elif text == "/form":
        await start_form(message, message.from_user.id)
    elif text == "/profile":
        await cmd_form(message)
    elif text == "/menu":
        await cmd_menu(message)
    elif text == "/test":
        await cmd_test(message)
    elif text == "/find":
        await cmd_find(message)
# ---------- Обработка сообщений ----------
async def text(message: types.Message):
    text = message.text
    user_id = message.from_user.id
    action = await get_field(user_id, "action")
    if text == ROOT_CODE and await get_field(user_id, "root") != "true":
        await set_string_field(user_id, "root", "true")
        await message.answer(Phrases["RootCode"])
        return
    if action in Actions:    
        if action == "confirm":
            await set_string_field(user_id, "form", "true")
            await set_string_field(user_id , "action", "None")
            if text == FormButtons["Restart"]:
                await start_form(message, user_id)
            if text == FormButtons["Confirm"]:
                await message.answer(Phrases["FormSaved"])
                await print_menu(message)
            return
        await form_question(message)
    if action in ActionEdit:
        await form_edit(message, action[:-4])
        await cmd_form(message, user_id=user_id)
    if text == ReturnButton["Return"]:
        await set_string_field(user_id, "action", "None")
        await print_menu(message)
    if text == MainButtons["Profile"]:
        await cmd_form(message, user_id=user_id)
    if text == MainButtons["Find"]:
        await cmd_find(message)
        return

# ---------- Консольные команды ----------
async def cmd(message: types.Message):
    text = message.text
    user_id = message.from_user.id
    if await get_field(user_id, "root") != "true":
        return
    if text.startswith("cmd_deleteform"):
        if len(text) == 14:
            user_id = message.from_user.id
        elif len(text) == 25:
            user_id = int(text[15:])
        else:
            await message.answer("Неверный формат команды")
            return
        await asyncio.to_thread(delete_user_sync, user_id)

# ---------- Принимаем сообщения ----------
@dp.message()
async def message(message: types.Message):
    mtext = message.text
    user_id = message.from_user.id
    if mtext and mtext[0] == "/":
        await command(message)
    elif mtext and mtext[:4] == "cmd_":
        await cmd(message)
    else:
        await text(message)

# ---------- Принимаем сигналы от Inline клавиатуры ----------
@dp.callback_query()
async def callback_query(callback: CallbackQuery):
    data = callback.data
    user_id = callback.from_user.id
    form = await get_field(user_id, "form")
    if data.startswith("reg_"): 
        region_idx = int(data.split("_")[1])
        region_name = list(Regions.keys())[region_idx]
        await set_string_field(user_id, "region", region_name)
        if await get_field(user_id, "action") != "regionEdit":
            await set_string_field(user_id, "action", "city")
        else:
            await set_string_field(user_id, "action", "cityEdit")
        await callback.answer()
        if form != "true":
            await callback.message.answer(Phrases["cityMessage2"])
        await callback.message.answer(Phrases["cityMessage1"], reply_markup=Cities[region_name])
    elif data.startswith("city_"):  
        city_name = data[5:]  
        await set_string_field(user_id, "city", city_name)
        if await get_field(user_id, "action") == "cityEdit":
            await cmd_form(callback.message, user_id=user_id)
            return
        await set_string_field(user_id, "action", "confirm")
        await callback.answer()
        profile_text = await print_profile(user_id=user_id)
        await callback.message.answer(Phrases["confirmMessage"] + "\n" + profile_text, reply_markup=FormConfirmKeyboard, parse_mode="HTML")
    elif data.startswith("edit_"):
        action = data[5:]
        reply = None
        if action == "city":
            reply = RegionInlineKeyboard
            action = "region"
        await set_string_field(user_id, "action", action+"Edit")
        await callback.message.answer(Phrases[action+"Message1"], reply_markup=reply)
        await callback.answer()
    elif data.startswith("view_"):
        reaction = data[5:]
        if reaction == "like":
            await set_string_field(user_id, "state", "like_unseen", table="views", additional_field="viewed_user_id", additional_value=int(await get_field(user_id, "action").split("_")[1]))
        elif reaction == "dislike":
            await set_string_field(user_id, "state", "dislike", table="views", additional_field="viewed_user_id", additional_value=int(await get_field(user_id, "action").split("_")[1]))
        elif reaction == "report":
            await set_int_field(int(await get_field(user_id, "action").split("_")[1]), "reports", await get_field(int(await get_field(user_id, "action").split("_")[1]), "reports") + 1)
        await callback.answer()
        await set_string_field(user_id, "action", "None")
        await cmd_find(callback.message, user_id=user_id)
    else:
        await callback.answer()
        await bot.send_message(user_id, data)

# ---------- Функция установки вебхука (будет вызвана при старте) ----------
async def on_startup(app: web.Application):
    webhook_url = WEBHOOK_URL
    await bot.delete_webhook()
    await bot.set_webhook(WEBHOOK_URL,  allowed_updates=dp.resolve_used_update_types())
    await set_commands(bot) 
    

# ---------- Создание aiohttp-приложения ----------
def create_app():
    app = web.Application()
    async def health(request):
        return web.Response(text="OK", status=200)
    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    webhook_requests = aiohttp_server.SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    webhook_requests.register(app, path="/webhook")
    app.on_startup.append(on_startup)
    return app

# ---------- Точка входа ----------
if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", 5000))
    web.run_app(app, host="0.0.0.0", port=port) 
