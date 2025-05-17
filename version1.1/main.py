import sqlite3
import random
import string
import re
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN, ADMIN_ID

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot=bot, storage=storage)

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('pride_ranked.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        telegram_id INTEGER PRIMARY KEY,
        username TEXT,
        unique_id TEXT,
        region TEXT,
        referral_code TEXT,
        invited_count INTEGER DEFAULT 0,
        registration_date TEXT,
        rank_5v5 TEXT DEFAULT 'Unranked',
        rank_2v2 TEXT DEFAULT 'Unranked'
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS friends (
        user_id INTEGER,
        friend_id INTEGER,
        PRIMARY KEY (user_id, friend_id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS friend_requests (
        from_id INTEGER,
        to_id INTEGER,
        status TEXT DEFAULT 'pending',
        PRIMARY KEY (from_id, to_id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER,
        username TEXT,
        type TEXT,  -- 'review' or 'complaint'
        rating INTEGER,  -- 1-5 for reviews, NULL for complaints
        category TEXT,  -- NULL for reviews, category for complaints
        feedback_text TEXT,
        media_type TEXT,  -- 'photo', 'video', or NULL
        media_id TEXT,  -- Telegram file ID for media
        submission_date TEXT
    )''')
    conn.commit()
    conn.close()

init_db()

# Состояния
class Registration(StatesGroup):
    username = State()
    region = State()
    referral = State()

class AddFriend(StatesGroup):
    search = State()

class Feedback(StatesGroup):
    review_rating = State()
    review_text = State()
    complaint_category = State()
    complaint_text = State()
    complaint_media = State()

# Генерация случайных кодов
def generate_unique_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def generate_referral_code():
    return ''.join(random.choices(string.digits, k=6))

# Главное меню
def get_main_menu():
    buttons = [
        [KeyboardButton(text="🎮 Профиль"), KeyboardButton(text="🏆 Играть")],
        [KeyboardButton(text="⚙️ Настройки"), KeyboardButton(text="📩 Обратная связь")],
        [KeyboardButton(text="⭐ Premium"), KeyboardButton(text="👥 Друзья")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# Список флагов
REGIONS = [
    "🇷🇺 Россия",
    "🇺🇸 США",
    "🇪🇺 Европа",
    "🇨🇳 Китай",
    "🇧🇷 Бразилия",
    "🇯🇵 Япония",
]

# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    conn = sqlite3.connect('pride_ranked.db')
    c = conn.cursor()
    c.execute("SELECT telegram_id FROM users WHERE telegram_id = ?", (message.from_user.id,))
    if c.fetchone():
        await message.answer("🌈 Добро пожаловать в Pride Ranked!", reply_markup=get_main_menu())
        conn.close()
        return
    conn.close()

    welcome_text = (
        "🌈 *Добро пожаловать в Pride Ranked v1\\.1* 🌈\n\n"
        "Ощутите совершенно новый уровень соревновательного матчмейкинга Clientmod с помощью данного телеграм\\-бота\\. Вас ждет:\n\n"
        "🏆 Рейтинговые матчи\n"
        "👥 Режимы 2на2 и 5на5\n"
        "📊 Автомониторинг и автостатистика\n"
        "🎨 Удобный интерфейс\n"
        "\\.\\.\\.и многое другое\\!\n\n"
        "Прежде чем продолжить, прочтите правила и условия пользования Pride Ranked\\. "
        "Если вы согласны, нажмите /register"
    )
    await message.answer(welcome_text, parse_mode="MarkdownV2", reply_markup=get_main_menu())

# Команда /register
@dp.message(Command("register"))
async def cmd_register(message: types.Message, state: FSMContext):
    conn = sqlite3.connect('pride_ranked.db')
    c = conn.cursor()
    c.execute("SELECT telegram_id FROM users WHERE telegram_id = ?", (message.from_user.id,))
    if c.fetchone():
        await message.answer("❌ Вы уже зарегистрированы!", reply_markup=get_main_menu())
        conn.close()
        return
    conn.close()

    await state.set_state(Registration.username)
    await message.answer(
        "📝 Введите ваш никнейм (только латиница, 3-16 символов, допускаются _ и -):",
        reply_markup=types.ReplyKeyboardRemove()
    )

# Обработка никнейма
@dp.message(Registration.username)
async def process_username(message: types.Message, state: FSMContext):
    username = message.text.strip()
    if not re.match(r'^[a-zA-Z0-9_-]{3,16}$', username):
        await message.answer(
            "❌ Никнейм должен содержать 3-16 символов, только латиницу, цифры, _ или -. Попробуйте еще раз:"
        )
        return

    await state.update_data(username=username)
    await state.set_state(Registration.region)

    keyboard = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=region)] for region in REGIONS], resize_keyboard=True)
    await message.answer("🌍 Выберите регион:", reply_markup=keyboard)

# Обработка региона
@dp.message(Registration.region)
async def process_region(message: types.Message, state: FSMContext):
    region = message.text.strip()
    if region not in REGIONS:
        await message.answer("❌ Пожалуйста, выберите регион из предложенных!")
        return

    await state.update_data(region=region)
    await state.set_state(Registration.referral)

    keyboard = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="➡️ Пропустить")]], resize_keyboard=True)
    await message.answer(
        "🔑 Введите реферальный код (если есть) или нажмите 'Пропустить':",
        reply_markup=keyboard
    )

# Обработка реферального кода
@dp.message(Registration.referral)
async def process_referral(message: types.Message, state: FSMContext):
    referral = message.text.strip() if message.text != "➡️ Пропустить" else None
    data = await state.get_data()

    unique_id = generate_unique_id()
    referral_code = generate_referral_code()
    registration_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect('pride_ranked.db')
    c = conn.cursor()
    c.execute('''INSERT INTO users (telegram_id, username, unique_id, region, referral_code, registration_date)
                 VALUES (?, ?, ?, ?, ?, ?)''',
              (message.from_user.id, data['username'], unique_id, data['region'], referral_code, registration_date))
    conn.commit()
    conn.close()

    await state.clear()
    await message.answer(
        "🌈 Добро пожаловать в Pride Ranked!",
        reply_markup=get_main_menu()
    )

# Команда Профиль
@dp.message(lambda message: message.text == "🎮 Профиль")
async def show_profile(message: types.Message):
    conn = sqlite3.connect('pride_ranked.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE telegram_id = ?", (message.from_user.id,))
    user = c.fetchone()
    conn.close()

    if not user:
        await message.answer("❌ Вы не зарегистрированы! Используйте /register", reply_markup=get_main_menu())
        return

    profile_text = (
        f"🎮 *Профиль игрока: {user[1]}*\n\n"
        f"🆔 *Уникальный ID:* {user[2]}\n"
        f"📅 *Дата регистрации:* {user[6]}\n"
        f"🌍 *Регион:* {user[3]}\n"
        f"🏆 *Звание 5vs5:* {user[7]}\n"
        f"🏆 *Звание 2vs2:* {user[8]}\n\n"
        f"🔗 *Реферальный код:* {user[4]}\n"
        f"👥 *Приглашено друзей:* {user[5]}"
        .replace(".", "\\.")
        .replace("-", "\\-")
        .replace("_", "\\_")
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="stats")]
    ])
    await message.answer(profile_text, parse_mode="MarkdownV2", reply_markup=get_main_menu())

# Команда Друзья
@dp.message(lambda message: message.text == "👥 Друзья")
async def show_friends(message: types.Message):
    conn = sqlite3.connect('pride_ranked.db')
    c = conn.cursor()
    c.execute('''SELECT u.username FROM users u
                 JOIN friends f ON u.telegram_id = f.friend_id
                 WHERE f.user_id = ?''', (message.from_user.id,))
    friends = c.fetchall()
    conn.close()

    if not friends:
        friends_text = "👥 Ваш список друзей пуст"
    else:
        friends_text = "👥 Ваш список друзей:\n" + "\n".join([f"• {friend[0]}" for friend in friends])

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить друга", callback_data="add_friend")],
        [InlineKeyboardButton(text="➖ Удалить друга", callback_data="delete_friend")],
        [InlineKeyboardButton(text="🔔 Уведомления", callback_data="notifications")]
    ])
    await message.answer(friends_text, reply_markup=keyboard)

# Обработка добавления друга
@dp.callback_query(lambda c: c.data == "add_friend")
async def add_friend(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AddFriend.search)
    await callback.message.answer(
        "🔍 Введите никнейм, уникальный ID, Telegram ID, ссылку на профиль или @username для поиска друга:",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await callback.answer()

# Поиск друга
@dp.message(AddFriend.search)
async def process_friend_search(message: types.Message, state: FSMContext):
    search_query = message.text.strip()
    conn = sqlite3.connect('pride_ranked.db')
    c = conn.cursor()

    user = None
    if search_query.startswith('@'):
        c.execute("SELECT telegram_id, username FROM users WHERE telegram_id = ?",
                  (search_query[1:],))
        user = c.fetchone()
    elif search_query.startswith('t.me/') or search_query.startswith('https://t.me/'):
        username = search_query.split('/')[-1]
        c.execute("SELECT telegram_id, username FROM users WHERE telegram_id = ?",
                  (username,))
        user = c.fetchone()
    elif re.match(r'^[A-Z0-9]{8}$', search_query):
        c.execute("SELECT telegram_id, username FROM users WHERE unique_id = ?",
                  (search_query,))
        user = c.fetchone()
    elif search_query.isdigit():
        c.execute("SELECT telegram_id, username FROM users WHERE telegram_id = ?",
                  (search_query,))
        user = c.fetchone()
    else:
        c.execute("SELECT telegram_id, username FROM users WHERE username = ?",
                  (search_query,))
        user = c.fetchone()

    if not user:
        await message.answer("❌ Пользователь не найден!", reply_markup=get_main_menu())
        await state.clear()
        conn.close()
        return

    if user[0] == message.from_user.id:
        await message.answer("❌ Нельзя добавить себя в друзья!", reply_markup=get_main_menu())
        await state.clear()
        conn.close()
        return

    c.execute("SELECT * FROM friends WHERE user_id = ? AND friend_id = ?",
              (message.from_user.id, user[0]))
    if c.fetchone():
        await message.answer("❌ Этот пользователь уже ваш друг!", reply_markup=get_main_menu())
        await state.clear()
        conn.close()
        return

    c.execute("SELECT * FROM friend_requests WHERE from_id = ? AND to_id = ? AND status = 'pending'",
              (message.from_user.id, user[0]))
    if c.fetchone():
        await message.answer("❌ Запрос уже отправлен этому пользователю!", reply_markup=get_main_menu())
        await state.clear()
        conn.close()
        return

    c.execute("INSERT INTO friend_requests (from_id, to_id) VALUES (?, ?)",
              (message.from_user.id, user[0]))
    conn.commit()
    conn.close()

    await message.answer(f"✅ Запрос в друзья отправлен пользователю {user[1]}!", reply_markup=get_main_menu())
    try:
        await bot.send_message(
            user[0],
            f"🔔 Вы получили запрос в друзья от {message.from_user.username or message.from_user.first_name}! "
            "Проверьте уведомления в разделе 'Друзья'.",
            reply_markup=get_main_menu()
        )
    except:
        pass

    await state.clear()

# Обработка уведомлений
@dp.callback_query(lambda c: c.data == "notifications")
async def show_notifications(callback: types.CallbackQuery):
    conn = sqlite3.connect('pride_ranked.db')
    c = conn.cursor()
    c.execute('''SELECT u.username, u.telegram_id FROM users u
                 JOIN friend_requests fr ON u.telegram_id = fr.from_id
                 WHERE fr.to_id = ? AND fr.status = 'pending' ''',
              (callback.from_user.id,))
    requests = c.fetchall()
    conn.close()

    if not requests:
        await callback.message.answer("🔔 У вас нет новых запросов в друзья.", reply_markup=get_main_menu())
        await callback.answer()
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for req in requests:
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text=f"✅ Принять {req[0]}", callback_data=f"accept_{req[1]}"),
            InlineKeyboardButton(text=f"❌ Отклонить {req[0]}", callback_data=f"reject_{req[1]}")
        ])

    await callback.message.answer("🔔 Запросы в друзья:", reply_markup=keyboard)
    await callback.answer()

# Принятие запроса
@dp.callback_query(lambda c: c.data.startswith("accept_"))
async def accept_friend(callback: types.CallbackQuery):
    friend_id = int(callback.data.split("_")[1])
    conn = sqlite3.connect('pride_ranked.db')
    c = conn.cursor()

    c.execute("UPDATE friend_requests SET status = 'accepted' WHERE from_id = ? AND to_id = ?",
              (friend_id, callback.from_user.id))
    c.execute("INSERT OR IGNORE INTO friends (user_id, friend_id) VALUES (?, ?)",
              (callback.from_user.id, friend_id))
    c.execute("INSERT OR IGNORE INTO friends (user_id, friend_id) VALUES (?, ?)",
              (friend_id, callback.from_user.id))
    c.execute("SELECT username FROM users WHERE telegram_id = ?", (friend_id,))
    friend_username = c.fetchone()[0]
    conn.commit()
    conn.close()

    await callback.message.answer(f"✅ Вы добавили {friend_username} в друзья!", reply_markup=get_main_menu())
    try:
        await bot.send_message(friend_id, f"✅ {callback.from_user.username or callback.from_user.first_name} принял ваш запрос в друзья!", reply_markup=get_main_menu())
    except:
        pass
    await callback.answer()

# Отклонение запроса
@dp.callback_query(lambda c: c.data.startswith("reject_"))
async def reject_friend(callback: types.CallbackQuery):
    friend_id = int(callback.data.split("_")[1])
    conn = sqlite3.connect('pride_ranked.db')
    c = conn.cursor()
    c.execute("UPDATE friend_requests SET status = 'rejected' WHERE from_id = ? AND to_id = ?",
              (friend_id, callback.from_user.id))
    c.execute("SELECT username FROM users WHERE telegram_id = ?", (friend_id,))
    friend_username = c.fetchone()[0]
    conn.commit()
    conn.close()

    await callback.message.answer(f"❌ Вы отклонили запрос от {friend_username}.", reply_markup=get_main_menu())
    try:
        await bot.send_message(friend_id, f"❌ {callback.from_user.username or callback.from_user.first_name} отклонил ваш запрос в друзья.", reply_markup=get_main_menu())
    except:
        pass
    await callback.answer()

# Удаление друга
@dp.callback_query(lambda c: c.data == "delete_friend")
async def delete_friend(callback: types.CallbackQuery):
    conn = sqlite3.connect('pride_ranked.db')
    c = conn.cursor()
    c.execute('''SELECT u.username, u.telegram_id FROM users u
                 JOIN friends f ON u.telegram_id = f.friend_id
                 WHERE f.user_id = ?''', (callback.from_user.id,))
    friends = c.fetchall()
    conn.close()

    if not friends:
        await callback.message.answer("❌ У вас нет друзей для удаления.", reply_markup=get_main_menu())
        await callback.answer()
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🗑 Удалить {friend[0]}", callback_data=f"remove_{friend[1]}")]
        for friend in friends
    ])
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_friends")])
    await callback.message.answer("👥 Выберите друга для удаления:", reply_markup=keyboard)
    await callback.answer()

# Подтверждение удаления
@dp.callback_query(lambda c: c.data.startswith("remove_"))
async def confirm_remove_friend(callback: types.CallbackQuery):
    friend_id = int(callback.data.split("_")[1])
    conn = sqlite3.connect('pride_ranked.db')
    c = conn.cursor()
    c.execute("SELECT username FROM users WHERE telegram_id = ?", (friend_id,))
    friend_username = c.fetchone()
    if not friend_username:
        await callback.message.answer("❌ Пользователь не найден.", reply_markup=get_main_menu())
        conn.close()
        await callback.answer()
        return

    friend_username = friend_username[0]
    c.execute("DELETE FROM friends WHERE user_id = ? AND friend_id = ?", 
              (callback.from_user.id, friend_id))
    c.execute("DELETE FROM friends WHERE user_id = ? AND friend_id = ?",
              (friend_id, callback.from_user.id))
    conn.commit()
    conn.close()

    await callback.message.answer(f"🗑 {friend_username} удален из друзей.", reply_markup=get_main_menu())
    try:
        await bot.send_message(friend_id, f"❌ {callback.from_user.username or callback.from_user.first_name} удалил вас из друзей.", reply_markup=get_main_menu())
    except:
        pass
    await callback.answer()

# Возврат к списку друзей
@dp.callback_query(lambda c: c.data == "back_to_friends")
async def back_to_friends(callback: types.CallbackQuery):
    conn = sqlite3.connect('pride_ranked.db')
    c = conn.cursor()
    c.execute('''SELECT u.username FROM users u
                 JOIN friends f ON u.telegram_id = f.friend_id
                 WHERE f.user_id = ?''', (callback.from_user.id,))
    friends = c.fetchall()
    conn.close()

    if not friends:
        friends_text = "👥 Ваш список друзей пуст"
    else:
        friends_text = "👥 Ваш список друзей:\n" + "\n".join([f"• {friend[0]}" for friend in friends])

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить друга", callback_data="add_friend")],
        [InlineKeyboardButton(text="➖ Удалить друга", callback_data="delete_friend")],
        [InlineKeyboardButton(text="🔔 Уведомления", callback_data="notifications")]
    ])
    await callback.message.edit_text(friends_text, reply_markup=keyboard)
    await callback.answer()

# Обратная связь
@dp.message(lambda message: message.text == "📩 Обратная связь")
async def feedback_menu(message: types.Message):
    conn = sqlite3.connect('pride_ranked.db')
    c = conn.cursor()
    c.execute("SELECT telegram_id, username FROM users WHERE telegram_id = ?", (message.from_user.id,))
    user = c.fetchone()
    conn.close()

    if not user:
        await message.answer("❌ Вы не зарегистрированы! Используйте /register", reply_markup=get_main_menu())
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Отзыв", callback_data="review")],
        [InlineKeyboardButton(text="⚠️ Жалоба", callback_data="complaint")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]
    ])
    await message.answer(
        f"📩 *Обратная связь*\\~\\~\\~\n\n"
        f"Здравствуйте, {user[1]}\\! Выберите действие:",
        parse_mode="MarkdownV2",
        reply_markup=keyboard
    )

# Обработка отзыва
@dp.callback_query(lambda c: c.data == "review")
async def start_review(callback: types.CallbackQuery, state: FSMContext):
    conn = sqlite3.connect('pride_ranked.db')
    c = conn.cursor()
    c.execute("SELECT submission_date FROM feedback WHERE telegram_id = ? AND type = 'review' ORDER BY submission_date DESC LIMIT 1",
              (callback.from_user.id,))
    last_review = c.fetchone()
    conn.close()

    if last_review:
        last_date = datetime.strptime(last_review[0], "%Y-%m-%d %H:%M:%S")
        if datetime.now() - last_date < timedelta(days=3):
            await callback.message.answer(
                "❌ Вы можете оставить новый отзыв только раз в 3 дня.",
                reply_markup=get_main_menu()
            )
            await callback.answer()
            return

    await state.set_state(Feedback.review_rating)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ 1", callback_data="rating_1"),
         InlineKeyboardButton(text="⭐⭐ 2", callback_data="rating_2")],
        [InlineKeyboardButton(text="⭐⭐⭐ 3", callback_data="rating_3"),
         InlineKeyboardButton(text="⭐⭐⭐⭐ 4", callback_data="rating_4")],
        [InlineKeyboardButton(text="⭐⭐⭐⭐⭐ 5", callback_data="rating_5")]
    ])
    await callback.message.answer("🌟 Выберите оценку (1-5 звезд):", reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("rating_"))
async def process_review_rating(callback: types.CallbackQuery, state: FSMContext):
    rating = int(callback.data.split("_")[1])
    await state.update_data(rating=rating)
    await state.set_state(Feedback.review_text)
    await callback.message.answer(
        "✍️ Введите текст отзыва (10-500 символов):",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await callback.answer()

@dp.message(Feedback.review_text)
async def save_review(message: types.Message, state: FSMContext):
    feedback_text = message.text.strip()
    if len(feedback_text) > 500 or len(feedback_text) < 10:
        await message.answer("❌ Отзыв должен быть от 10 до 500 символов.", reply_markup=get_main_menu())
        return

    data = await state.get_data()
    rating = data['rating']
    conn = sqlite3.connect('pride_ranked.db')
    c = conn.cursor()
    c.execute("SELECT username FROM users WHERE telegram_id = ?", (message.from_user.id,))
    username = c.fetchone()[0]
    submission_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute('''INSERT INTO feedback (telegram_id, username, type, rating, feedback_text, submission_date)
                 VALUES (?, ?, ?, ?, ?, ?)''',
              (message.from_user.id, username, 'review', rating, feedback_text, submission_date))
    conn.commit()
    conn.close()

    # Отправка отзыва администратору
    admin_text = (
        f"⭐ *Новый отзыв*\n\n"
        f"👤 От: {username}\n"
        f"🆔 ID: {message.from_user.id}\n"
        f"⭐ Оценка: {rating}\n"
        f"📅 Дата: {submission_date}\n"
        f"📝 Текст: {feedback_text}"
        .replace(".", "\\.")
        .replace("-", "\\-")
        .replace("_", "\\_")
        .replace("!", "\\!")
    )
    
    try:
        await bot.send_message(ADMIN_ID, admin_text, parse_mode="MarkdownV2")
    except Exception as e:
        print(f"Ошибка отправки отзыва админу: {e}")

    await state.clear()
    await message.answer("✅ Ваш отзыв успешно отправлен! Спасибо! 🎉", reply_markup=get_main_menu())

# Команда статистики отзывов для админов
@dp.message(Command("review"))
async def review_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    conn = sqlite3.connect('pride_ranked.db')
    c = conn.cursor()
    
    # Получаем статистику по отзывам
    c.execute("SELECT COUNT(*), AVG(rating) FROM feedback WHERE type = 'review'")
    review_count, avg_rating = c.fetchone()
    
    # Получаем количество жалоб по категориям
    c.execute("""
        SELECT category, COUNT(*) 
        FROM feedback 
        WHERE type = 'complaint' 
        GROUP BY category
    """)
    complaints = c.fetchall()
    
    # Формируем текст статистики
    stats_text = (
        f"📊 *Статистика отзывов и жалоб*\n\n"
        f"📝 Всего отзывов: {review_count}\n"
        f"⭐ Средний рейтинг: {round(avg_rating, 2) if avg_rating else 0}\n\n"
        f"⚠️ *Статистика жалоб:*\n"
    ).replace(".", "\\.").replace("-", "\\-").replace("_", "\\_")
    
    for category, count in complaints:
        stats_text += f"• {category}: {count}\n"
    
    conn.close()
    
    await message.answer(stats_text, parse_mode="MarkdownV2")

# Обработка жалобы
@dp.callback_query(lambda c: c.data == "complaint")
async def start_complaint(callback: types.CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 Жалоба на бота", callback_data="complaint_bot")],
        [InlineKeyboardButton(text="🏆 Жалоба на матч", callback_data="complaint_match")],
        [InlineKeyboardButton(text="👤 Жалоба на игрока", callback_data="complaint_player")],
        [InlineKeyboardButton(text="❓ Другое", callback_data="complaint_other")]
    ])
    await callback.message.answer("⚠️ Выберите категорию жалобы:", reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("complaint_"))
async def process_complaint_category(callback: types.CallbackQuery, state: FSMContext):
    category = {
        "complaint_bot": "Жалоба на бота",
        "complaint_match": "Жалоба на матч",
        "complaint_player": "Жалоба на игрока",
        "complaint_other": "Другое"
    }[callback.data]
    await state.update_data(category=category)
    await state.set_state(Feedback.complaint_text)
    await callback.message.answer(
        "✍️ Опишите вашу жалобу (10-500 символов):",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await callback.answer()

@dp.message(Feedback.complaint_text)
async def process_complaint_text(message: types.Message, state: FSMContext):
    complaint_text = message.text.strip()
    if len(complaint_text) > 500 or len(complaint_text) < 10:
        await message.answer("❌ Жалоба должна быть от 10 до 500 символов.", reply_markup=get_main_menu())
        return

    await state.update_data(complaint_text=complaint_text)
    await state.set_state(Feedback.complaint_media)
    keyboard = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="➡️ Пропустить")]], resize_keyboard=True)
    await message.answer(
        "📎 Прикрепите фото или видео (если есть) или нажмите 'Пропустить':",
        reply_markup=keyboard
    )

@dp.message(Feedback.complaint_media)
async def process_complaint_media(message: types.Message, state: FSMContext):
    data = await state.get_data()
    complaint_text = data['complaint_text']
    category = data['category']
    media_type = None
    media_id = None

    if message.text == "➡️ Пропустить":
        pass
    elif message.photo:
        media_type = 'photo'
        media_id = message.photo[-1].file_id
    elif message.video:
        media_type = 'video'
        media_id = message.video.file_id
    else:
        await message.answer("❌ Пожалуйста, прикрепите фото/видео или нажмите 'Пропустить'.", reply_markup=get_main_menu())
        return

    conn = sqlite3.connect('pride_ranked.db')
    c = conn.cursor()
    c.execute("SELECT username FROM users WHERE telegram_id = ?", (message.from_user.id,))
    username = c.fetchone()[0]
    submission_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute('''INSERT INTO feedback (telegram_id, username, type, category, feedback_text, media_type, media_id, submission_date)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
              (message.from_user.id, username, 'complaint', category, complaint_text, media_type, media_id, submission_date))
    conn.commit()
    conn.close()

    # Пересылка жалобы админу
    admin_text = (
        f"⚠️ *Новая жалоба*\n\n"
        f"👤 Пользователь: {username}\n"
        f"🆔 ID: {message.from_user.id}\n"
        f"📅 Дата: {submission_date}\n"
        f"📋 Категория: {category}\n"
        f"📜 Текст: {complaint_text}"
        .replace(".", "\\.")
        .replace("-", "\\-")
        .replace("_", "\\_")
        .replace("!", "\\!")
    )
    try:
        await bot.send_message(ADMIN_ID, admin_text, parse_mode="MarkdownV2")
        if media_type == 'photo':
            await bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)
        elif media_type == 'video':
            await bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)
    except:
        await message.answer("❌ Ошибка при отправке жалобы админу.", reply_markup=get_main_menu())
        await state.clear()
        return

    await state.clear()
    await message.answer("✅ Ваша жалоба отправлена администрации!", reply_markup=get_main_menu())

# Возврат в главное меню
@dp.callback_query(lambda c: c.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "↩️ Вы вернулись в главное меню.",
        reply_markup=get_main_menu()
    )
    await callback.answer()

# Обработчик статистики
@dp.callback_query(lambda c: c.data == "stats")
async def process_stats(callback: types.CallbackQuery):
    await callback.message.answer("📊 Статистика пока в разработке!", reply_markup=get_main_menu())
    await callback.answer()

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())