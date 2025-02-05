import os
import re
import time
import json
import socket
import string
import random
import logging
import asyncio
import sqlite3
import paramiko
import asyncssh
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from config import BOT_TOKEN
import config

from aiogram import Bot, Dispatcher, Router, F, types
from aiogram.types import (
    Message, 
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    FSInputFile
)
from aiogram.filters import Command, StateFilter
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder 
from config import ADMIN_IDS, ADMIN_IDS2, ADMIN_PREM
 
# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()

# Определение состояний
class RegistrationStates(StatesGroup):
    waiting_for_nickname = State()
    waiting_for_country = State()

class NicknameStates(StatesGroup):
    waiting_for_nickname = State()

class IDChangeStates(StatesGroup):
    waiting_for_id = State()

class ReviewStates(StatesGroup):
    waiting_for_review = State()

class AdminPremiumStates(StatesGroup):
    waiting_for_user_id = State()

class ReferralStates(StatesGroup):
    waiting_for_code = State()

class BanStates(StatesGroup):
    waiting_for_username = State()
    waiting_for_reason = State()
    waiting_for_duration = State()

class UnbanStates(StatesGroup):
    waiting_for_username = State()

class NewsStates(StatesGroup):
    waiting_for_news = State()

class ReportStates(StatesGroup):
    waiting_for_report = State()

class SearchStates(StatesGroup):
    waiting_for_search = State()

# Инициализация базы данных
conn = sqlite3.connect('users.db', check_same_thread=False)
cursor = conn.cursor()

# Создание таблиц
cursor.executescript('''
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    random_id TEXT UNIQUE,
    user_name TEXT UNIQUE,
    registration_date TEXT,
    country TEXT,
    premium TEXT,
    kills INTEGER DEFAULT 0,
    deaths INTEGER DEFAULT 0,
    match_count INTEGER DEFAULT 0,
    adr REAL DEFAULT 0.0,
    avg REAL DEFAULT 0.0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    hidden INTEGER DEFAULT 0,
    active_game TEXT DEFAULT NULL,
    ban_status INTEGER DEFAULT 0,
    ban_until TEXT DEFAULT NULL,
    referral_code INTEGER DEFAULT 0,
    referral_count INTEGER DEFAULT 0,
    ban_reason TEXT,
    used INTEGER DEFAULT 0,
    elo INTEGER DEFAULT 1000,
    ban_end_time DATETIME
);

CREATE TABLE IF NOT EXISTS friends (
    user_id TEXT,
    friend_id TEXT,
    added_date TEXT,
    PRIMARY KEY (user_id, friend_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (friend_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS matches (
    match_id TEXT PRIMARY KEY,
    start_time TEXT,
    end_time TEXT,
    map TEXT,
    server_ip TEXT,
    server_port INTEGER,
    status TEXT
);

CREATE TABLE IF NOT EXISTS match_stats (
    match_id TEXT,
    user_id TEXT,
    team TEXT,
    kills INTEGER DEFAULT 0,
    deaths INTEGER DEFAULT 0,
    assists INTEGER DEFAULT 0,
    score INTEGER DEFAULT 0,
    mvps INTEGER DEFAULT 0,
    ping INTEGER DEFAULT 0,
    PRIMARY KEY (match_id, user_id),
    FOREIGN KEY (match_id) REFERENCES matches(match_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS bans (
    ban_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    admin_id TEXT,
    ban_reason TEXT,
    ban_date TEXT,
    unban_date TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (admin_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS reports (
    report_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    reported_user_id TEXT,
    report_text TEXT,
    report_date TEXT,
    status TEXT DEFAULT 'pending',
    admin_comment TEXT,
    resolved_by TEXT,
    resolved_date TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (reported_user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS reviews (
    review_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    review_text TEXT,
    review_date TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS active_servers (
    server_id TEXT PRIMARY KEY,
    ip TEXT,
    port INTEGER,
    map TEXT,
    status TEXT,
    start_time TEXT,
    player_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS premium_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    start_date TEXT,
    end_date TEXT,
    payment_method TEXT,
    amount REAL,
    status TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS referrals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    referrer_id TEXT,
    referred_id TEXT,
    date TEXT,
    status TEXT,
    FOREIGN KEY (referrer_id) REFERENCES users(user_id),
    FOREIGN KEY (referred_id) REFERENCES users(user_id)
);
''')

# Сохраняем изменения
conn.commit()

# Глобальные переменные
user_data = {}
search_players = []
player_messages = {}
active_servers = {}
active_searches = {}
available_ports = [27015, 27016, 27017, 27018, 27019]
waiting_for_referral_code = {}
users = {}
premium_status_user = False
player_history = {}
user_cooldown = {}
COOLDOWN_TIME = 300
command_cooldowns = {}
def generate_random_id():
    return ''.join(random.choices(string.digits, k=9))
def generate_referral_code() -> str:
    while True:
        code = ''.join(random.choices(string.digits, k=6))
        cursor.execute("SELECT user_id FROM users WHERE referral_code = ?", (code,))
        if not cursor.fetchone():
            return code

def get_main_menu(premium: bool = False) -> ReplyKeyboardMarkup:
    buttons = [
        [
            KeyboardButton(text="👑 Профиль"),
            KeyboardButton(text="👥 Друзья")
        ],
        [
            KeyboardButton(text="📊 Статистика"),
            KeyboardButton(text="/search")
        ],
        [
            KeyboardButton(text="⚙️ Добавить друга"),
            KeyboardButton(text="💳 Премиум" if not premium else "⭐ Премиум меню")
        ],
        [
            KeyboardButton(text="📝Жалоба на игрока"),
            KeyboardButton(text="📝 Отправить отзыв")
        ]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_premium_menu() -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text="✏️ Изменить никнейм")],
        [KeyboardButton(text="🔄 Изменить ID")],
        [KeyboardButton(text="🔒 Скрыть профиль")],
        [KeyboardButton(text="🔙 Главное меню")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_search_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="✅ Начать", callback_data="start_search"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_search")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_duration_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    for duration, price in PRICING.items():
        buttons.append([
            InlineKeyboardButton(
                text=f"⭐ {duration} - {price}₽",
                callback_data=f"duration:{duration}"
            )
        ])
    buttons.append([
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="cancel"
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_payment_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    for method in PAYMENT_DETAILS.keys():
        buttons.append([
            InlineKeyboardButton(
                text=f"💳 {method}",
                callback_data=f"payment:{method}"
            )
        ])
    buttons.append([
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="cancel"
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_keyboard(user_id: int) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm:{user_id}")],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject:{user_id}")]
    ]
    return
def create_inline_keyboard():
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    return markup

def create_reply_keyboard():
    markup = ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True
    )
    return markup

@router.message(Command("start"))
async def start(message: Message):
    try:
        user_id = str(message.from_user.id)

        cursor.execute("SELECT premium FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()

        # Создаем клавиатуру
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Я новичок!", callback_data="newbie")]
        ])

        start_text = (
            "Добро пожаловать в бета-тест! 🎮\n\n"
            "Команда CMTV долго и усердно работала над созданием этого инструмента, чтобы раскрыть весь потенциал Faceit. "
            "Мы стремились учесть всё, что важно для игроков, чтобы процесс игры стал максимально удобным и комфортным. "
            "Теперь вы можете стать частью бета-теста и помочь нам улучшить этот инструмент!\n\n"
            "🔧 **Этот инструмент поможет вам раскрыть весь свой потенциал:**\n"
            "- 📊 Улучшенный анализ вашей статистики.\n"
            "- 🎯 Новое и в разы лучшее игровое меню.\n"
            "- ⚡ Дополнительные функции для комфортной игры.\n\n"
            "💬 **Как начать?**\n"
            "1️⃣ Запустите Faceit ClientMod.\n"
            "2️⃣ Зарегистрируйтесь с помощью команды /register.\n"
            "3️⃣ Наслаждайтесь, и побеждайте!!\n\n"
            "⚠️ **Важно:** Это бета-версия, поэтому возможны баги. Если вы заметите проблему, "
            "отправьте отзыв с помощью кнопки Отправить отзыв в меню. Ваши отзывы помогут нам сделать инструмент лучше!\n\n"
            "🌟 **Начните сейчас и почувствуйте разницу!**"
        )

        if not user:
            try:
                # Пробуем отправить сообщение с фото
                photo = FSInputFile("start.png")
                await message.answer_photo(
                    photo=photo,
                    caption=start_text,
                    reply_markup=markup,
                    parse_mode="Markdown"
                )
            except FileNotFoundError:
                # Если файл не найден, отправляем только текст
                logging.warning("Файл start.png не найден, отправляем сообщение без изображения")
                await message.answer(
                    start_text,
                    reply_markup=markup,
                    parse_mode="Markdown"
                )
            except Exception as e:
                # Если возникла другая ошибка при отправке фото, отправляем текст
                logging.error(f"Ошибка при отправке фото: {e}")
                await message.answer(
                    start_text,
                    reply_markup=markup,
                    parse_mode="Markdown"
                )
        else:
            # Для зарегистрированных пользователей
            premium_status = user[0].lower() == 'да'
            markup = get_main_menu(premium=premium_status)
            await message.answer(
                "👑 Добро пожаловать в наш бета тест! ❤️",
                reply_markup=markup
            )

    except Exception as e:
        logging.error(f"Критическая ошибка в команде start: {e}")
        await message.answer(
            "Произошла ошибка при запуске бота. Пожалуйста, попробуйте позже."
        )

@router.callback_query(F.data == "newbie")
async def handle_newbie(callback: CallbackQuery):
    try:
        await callback.message.answer(
            "❕️<b>Faceit ClientMod</b>❕️\n\n"
            "<b>Что такое Faceit?</b>\n"
            "FACEIT — это платформа, ориентированная на развитие сообществ и предоставление высокоуровневых онлайн-соревнований для множества PvP-игр. Поднимайтесь по рангам и покажите свой уровень игры.\n\n"
            "<b>Как начать играть в Faceit ClientMod?</b>\n"
            "1️⃣ — Запустите Faceit ClientMod\n"
            "2️⃣ — Зарегистрируйтесь с помощью команды: /register\n"
            "3️⃣ — Наслаждайтесь и побеждайте в матчах\n\n"
            "<b>Помощь по использованию команд:</b>\n\n"
            "- <b>Register</b> —> Регистрация вашего Faceit профиля. Необходимо ввести ваш никнейм и страну.\n"
            "- <b>Profile</b> —> Ваш игровой профиль...",  # остальной текст
            parse_mode="HTML"
        )
    except Exception as e:
        await handle_error(e, callback.message)

@router.message(Command("register"))
async def register(message: Message, state: FSMContext):
    try:
        user_id = str(message.from_user.id)

        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        if cursor.fetchone():
            await message.answer("❌ Вы уже зарегистрированы!")
            return

        await message.answer(
            "Введите ваш никнейм (до 10 символов), используя только английские буквы, цифры и спец. символы:"
        )
        await state.set_state(RegistrationStates.waiting_for_nickname)
        await state.update_data(user_id=user_id)

    except Exception as e:
        await handle_error(e, message)

@router.message(RegistrationStates.waiting_for_nickname)
async def save_nickname(message: Message, state: FSMContext):
    nickname = message.text.strip()
    if not re.match(r'^[a-zA-Z0-9!@#$%^&*]{1,10}$', nickname):
        await message.answer(
            "❌ Никнейм должен содержать только английские буквы, цифры или спец. символы и быть длиной до 10 символов."
        )
        return

    cursor.execute("SELECT user_id FROM users WHERE user_name = ?", (nickname,))
    if cursor.fetchone():
        await message.answer("❌ Этот никнейм уже занят. Пожалуйста, выберите другой.")
        return

    await state.update_data(nickname=nickname)
    await message.answer("🌍 Введите вашу страну в виде эмодзи (например, 🇷🇺 для России):")
    await state.set_state(RegistrationStates.waiting_for_country)

# 1. Исправленная валидация страны в RegistrationStates.waiting_for_country
@router.message(RegistrationStates.waiting_for_country)
async def save_country(message: Message, state: FSMContext):
    country = message.text.strip()
    # Обновленное регулярное выражение для проверки эмодзи-флагов
    if not re.match(r'^[\U0001F1E6-\U0001F1FF]{2}$', country):
        await message.answer(
            "❌ Укажите страну только с помощью эмодзи флага (например, 🇷🇺 для России). Попробуйте снова:"
        )
        return

    data = await state.get_data()
    user_id = data['user_id']
    user_name = data['nickname']

    registration_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    random_id = generate_random_id()
    referral_code = generate_referral_code()

    cursor.execute("""
        INSERT INTO users 
        (user_id, random_id, user_name, registration_date, country, premium, 
        kills, deaths, match_count, adr, avg, wins, losses, hidden, referral_code)
        VALUES (?, ?, ?, ?, ?, ?, 0, 0, 0, 0.0, 0.0, 0, 0, 0, ?)
    """, (user_id, random_id, user_name, registration_date, country, 'нет', referral_code))
    conn.commit()

    await message.answer(f"🎉 Пользователь {user_name} зарегистрирован успешно!")
    markup = get_main_menu()
    await message.answer(
        "👑 Добро пожаловать в бета тест! Выберите действие ниже.",
        reply_markup=markup
    )
    await state.clear()  # В
# 2. Добавляем фильтры состояний для обработчиков кнопок
@router.callback_query(
    F.data == "start_search",
    ~StateFilter(RegistrationStates.waiting_for_country)
)
async def handle_start_search(callback: CallbackQuery):
    user_id = str(callback.from_user.id)
    search_id = search_manager.player_searches.get(user_id)

    if not search_id:
        await callback.answer("❌ Поиск не найден.")
        return

    search_data = search_manager.active_searches.get(search_id)
    if not search_data or len(search_data['players']) < config.MIN_PLAYERS_FOR_START:
        await callback.answer("⚠️ Недостаточно игроков для старта!")
        return

    await finish_search(search_id)
    await callback.answer("✅ Запускаем матч!")

@router.callback_query(
    F.data == "cancel_search",
    ~StateFilter(RegistrationStates.waiting_for_country)
)
async def handle_cancel_search(callback: CallbackQuery):
    try:
        user_id = str(callback.from_user.id)
        await search_manager.remove_player(user_id)

        try:
            await callback.message.edit_text("❌ Поиск отменен.")
        except TelegramBadRequest as telegram_error:
            if "message is not modified" not in str(telegram_error):
                await callback.message.answer("❌ Поиск отменен.")

        await callback.answer()

    except Exception as e:
        logger.error(f"Ошибка при отмене поиска для игрока {user_id}: {e}")
        try:
            await callback.message.answer("❌ Поиск отменен.")
        except:
            pass
# Настройки премиум-подписки
PRICING = {
    "1 месяц": 149,
    "3 месяца": 399,
    "1 год": 1299
}

PAYMENT_DETAILS = {
    "Карта (OZON Bank)": "2204 3203 9586 7460",
    "Криптовалюта (TRC20)": "TWvSQvNe7erMeYo218sQDebdzQwqkjWVHo", 
    "Криптовалюта (TON)": "EQDD8dqOzaj4zUK6ziJOo_G2lx6qf1TEktTRkFJ7T1c_fPQb",
    "ЮMoney": "4100118827695775"
}

async def handle_error(e: Exception, message: Message):
    """
    Обработчик ошибок для aiogram 3

    Args:
        e (Exception): Объект исключения
        message (Message): Объект сообщения aiogram
    """
    error_msg = f"Error occurred: {str(e)}"
    logging.error(error_msg)

    try:
        # Отправляем сообщение об ошибке пользователю
        await message.answer(
            "❌ Произошла ошибка. Пожалуйста, попробуйте еще раз.",
            parse_mode="HTML"
        )

        # Если нужно уведомить администраторов об ошибке
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    f"🚨 Ошибка в боте:\n"
                    f"Пользователь: {message.from_user.id}\n"
                    f"Текст ошибки: {error_msg}"
                )
            except Exception as admin_error:
                logging.error(f"Failed to notify admin {admin_id}: {str(admin_error)}")

    except Exception as reply_error:
        logging.error(f"Failed to send error message: {str(reply_error)}")
@router.message(F.text == "👑 Профиль")
async def show_profile(message: Message):
    try:
        user_id = str(message.from_user.id)
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()

        if user:
            premium_status = user[5] == 'да'
            kills = user[6] or 0
            deaths = user[7] or 0
            matches = user[8] or 0
            adr = user[9] or 0.0
            avg_rating = user[10] or 0.0
            wins = user[11] or 0
            losses = user[12] or 0

            kd_ratio = kills if deaths == 0 else kills / deaths

            cursor.execute('SELECT referral_code, referral_count FROM users WHERE user_id = ?', (user_id,))
            referral_data = cursor.fetchone()
            random_id, referral_count = referral_data if referral_data else ("Не установлен", 0)

            profile_text = (
                f"🎮 Профиль игрока: {user[2]}\n"
                f"🆔 Уникальный ID: {user[1]}\n"
                f"📅 Дата регистрации: {user[3]}\n"
                f"🌍 Регион: {user[4]}\n\n"
                f"🔗 Реферальный код: {random_id}\n"
                f"👥 Приглашено друзей: {referral_count}\n"
            )

            if premium_status:
                profile_text += (
                    f"\n🌟 Премиум-аккаунт активирован!\n"
                    f"🔥 Дополнительные функции доступны.\n"
                )

            await message.answer(profile_text)
        else:
            await message.answer("❌ Ваш профиль не найден. Пожалуйста, зарегистрируйтесь /register.")
    except Exception as e:
        await handle_error(e, message)

@router.message(F.text == "💳 Премиум")
async def premium_handler(message: Message, state: FSMContext):
    user_state = await state.get_data()
    if user_state.get("in_progress"):
        await message.answer(
            "Вы уже оформляете заказ. Завершите текущий процесс или нажмите 'Отмена', чтобы начать новый."
        )
        return

    await state.update_data(in_progress=True)
    await message.answer(
        "Добро пожаловать в раздел оформления премиум-подписки!\n\n"
        "Выберите срок подписки, и получите доступ к эксклюзивным функциям.",
        reply_markup=duration_keyboard()
    )
def get_db_connection():
    return sqlite3.connect("users.db")

def duration_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=f"⭐ {duration} - {price}₽", callback_data=f"duration:{duration}")]
        for duration, price in config.PREMIUM_DURATION.items()
    ]

    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)  # Кнопки в столбец

def payment_method_keyboard() -> InlineKeyboardMarkup:
    payment_methods = {
        "Карта (OZON Bank)": "2204 3203 9586 7460",
        "Криптовалюта (TRC20)": "TWvSQvNe7erMeYo218sQDebdzQwqkjWVHo",
        "Криптовалюта (TON)": "EQDD8dqOzaj4zUK6ziJOo_G2lx6qf1TEktTRkFJ7T1c_fPQb",
        "ЮMoney": "4100118827695775"
    }

    buttons = [
        [InlineKeyboardButton(text=f"💳 {method}", callback_data=f"payment:{method}")]
        for method in payment_methods.keys()
    ]

    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)  # Кнопки в столбец

def admin_keyboard(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm:{user_id}")],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject:{user_id}")]
    ])  # Кнопки в столбец

@router.callback_query(F.data.startswith("duration:"))
async def select_duration(callback: CallbackQuery, state: FSMContext):
    duration = callback.data.split(":")[1]
    await state.update_data(duration=duration)
    await callback.message.edit_text(
        f"Вы выбрали срок: {duration}. Теперь выберите способ оплаты.",
        reply_markup=payment_method_keyboard()
    )

@router.callback_query(F.data.startswith("payment:"))
async def select_payment_method(callback: CallbackQuery, state: FSMContext):
    method = callback.data.split(":")[1]
    await state.update_data(payment_method=method)

    payment_methods = {
        "Карта (OZON Bank)": "2204 3203 9586 7460",
        "Криптовалюта (TRC20)": "TWvSQvNe7erMeYo218sQDebdzQwqkjWVHo",
        "Криптовалюта (TON)": "EQDD8dqOzaj4zUK6ziJOo_G2lx6qf1TEktTRkFJ7T1c_fPQb",
        "ЮMoney": "4100118827695775"
    }

    user_data = await state.get_data()
    duration = user_data.get('duration', 'не указан')
    details = payment_methods.get(method, "Информация недоступна.")

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
    ])

    await callback.message.edit_text(
        f"Вы выбрали способ оплаты: {method}.\n\n"
        f"Срок подписки: {duration}\n"
        f"Реквизиты для оплаты:\n{details}\n\n"
        f"⚠️ Обратите внимание: комиссия за перевод лежит на вас.\n"
        f"После оплаты отправьте скриншот для подтверждения.",
        reply_markup=keyboard
    )

@router.callback_query(F.data == "cancel")
async def cancel_process(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Операция отменена.")

@router.callback_query(F.data.startswith("confirm:"))
async def confirm_payment(callback: CallbackQuery):
    user_id = int(callback.data.split(":")[1])

    try:
        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute("UPDATE users SET premium = 'да' WHERE user_id = ?", (user_id,))
        db.commit()
        db.close()

        await callback.message.edit_text(f"✅ Платеж пользователя {user_id} подтвержден.")
        await bot.send_message(user_id, "✅ Ваша подписка активирована! Пропишите /start для обновления меню.")

    except Exception as e:
        logging.error(f"Ошибка при подтверждении платежа: {e}")
        await callback.message.answer("❌ Ошибка при подтверждении. Попробуйте позже.")

@router.callback_query(F.data.startswith("reject:"))
async def reject_payment(callback: CallbackQuery):
    user_id = int(callback.data.split(":")[1])
    await callback.message.edit_text(f"❌ Платеж пользователя {user_id} отклонен.")
    await bot.send_message(user_id, "❌ Ваш платеж отклонен. Попробуйте снова или свяжитесь с поддержкой.")

@router.message(F.photo)
async def handle_photo(message: Message, state: FSMContext):
    try:
        # Проверяем регистрацию
        cursor.execute("SELECT user_name FROM users WHERE user_id = ?", (message.from_user.id,))
        player = cursor.fetchone()

        if not player:
            await message.answer("Вы не зарегистрированы. Пожалуйста, зарегистрируйтесь для продолжения.")
            return

        # Проверяем активный заказ
        user_data = await state.get_data()
        if not user_data.get("in_progress"):
            await message.answer("У вас нет активного заказа. Используйте /start, чтобы начать.")
            return

        duration = user_data.get('duration', 'не указан')
        payment_method = user_data.get('payment_method', 'не указан')

        # Отправляем админу
        admin_message = await bot.send_message(
            chat_id=config.ADMIN_PREM,
            text=f"Скриншот оплаты от @{message.from_user.username}.\n"
                 f"Срок подписки: {duration}\n"
                 f"Способ оплаты: {payment_method}.",
            reply_markup=admin_keyboard(message.from_user.id)
        )

        await message.forward(config.ADMIN_PREM)
        await message.answer("Скриншот отправлен администратору. Ожидайте подтверждения.")
        await state.clear()

    except Exception as e:
        logging.error(f"Ошибка при обработке фото: {e}")
        await message.answer("Произошла ошибка при отправке скриншота. Попробуйте позже.")
        await state.clear()

def create_premium_menu():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Изменить никнейм")],
            [KeyboardButton(text="Изменить ID")],
            [KeyboardButton(text="Вернуться в главное меню")]
        ],
        resize_keyboard=True
    )
    return keyboard


@router.message(F.text == "⭐ Премиум меню")
async def premium_menu_handler(message: Message):
    try:
        db = get_db_connection()
        cursor = db.cursor()

        user_id = str(message.from_user.id)
        cursor.execute("SELECT premium FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        db.close()

        if user and user[0] == 'да':
            markup = create_premium_menu()
            await message.answer("⭐ Добро пожаловать в премиум-меню!", reply_markup=markup)
        else:
            await message.answer("❌ Для доступа к премиум-меню необходима премиум-подписка.")

    except Exception as e:
        logging.error(f"Ошибка в premium_menu_handler: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")


# Обработчик кнопки "Вернуться в главное меню"
@router.message(F.text == "Вернуться в главное меню")
async def back_to_main_menu(message: Message):
    # Удаляем сообщение с кнопкой
    await message.bot.delete_message(message.chat.id, message.message_id)

    # Прямо вызываем функцию start, чтобы обработать возвращение в главное меню
    await start(message)

# Создание состояний для машины состояний (FSM)
class ChangeNicknameState(StatesGroup):
    waiting_for_nickname = State()


class ChangeIDState(StatesGroup):
    waiting_for_id = State()


# Обработчик кнопки "Изменить никнейм"
@router.message(F.text == "Изменить никнейм")
async def change_nickname(message: Message, state: FSMContext):
    await message.answer("Введите новый никнейм:")
    await state.set_state(ChangeNicknameState.waiting_for_nickname)


# Обработчик ввода нового никнейма
@router.message(ChangeNicknameState.waiting_for_nickname)
async def process_new_nickname(message: Message, state: FSMContext):
    new_nickname = message.text.strip()
    db = get_db_connection()
    cursor = db.cursor()

    # Проверяем, существует ли никнейм в базе
    cursor.execute("SELECT * FROM users WHERE user_name=?", (new_nickname,))
    existing_user = cursor.fetchone()

    if existing_user:
        await message.answer("❌ Этот никнейм уже занят. Пожалуйста, выберите другой.")
    else:
        # Обновляем никнейм в базе данных
        cursor.execute("UPDATE users SET user_name=? WHERE user_id=?", (new_nickname, message.from_user.id))
        db.commit()
        await message.answer(f"✅ Никнейм успешно изменен на {new_nickname}.", reply_markup=create_premium_menu())

    db.close()
    await state.clear()  # Очистка состояния


# Обработчик кнопки "Изменить ID"
@router.message(F.text == "Изменить ID")
async def change_id(message: Message, state: FSMContext):
    await message.answer("Введите новый ID:")
    await state.set_state(ChangeIDState.waiting_for_id)


# Обработчик ввода нового ID
@router.message(ChangeIDState.waiting_for_id)
async def process_new_id(message: Message, state: FSMContext):
    new_random_id = message.text.strip()
    forbidden_ids = ["admin", "00000000"]  # Запрещенные ID

    db = get_db_connection()
    cursor = db.cursor()

    # Проверяем, является ли ID запрещенным
    if new_random_id in forbidden_ids and message.from_user.id not in ADMIN_IDS2:
        await message.answer("❌ Этот ID недопустим. Пожалуйста, выберите другой.")
        db.close()
        return

    # Проверяем, существует ли ID в базе
    cursor.execute("SELECT * FROM users WHERE random_id=?", (new_random_id,))
    existing_user = cursor.fetchone()

    if existing_user:
        await message.answer("❌ Этот ID уже занят. Пожалуйста, выберите другой.")
    else:
        # Обновляем ID в базе данных
        cursor.execute("UPDATE users SET random_id=? WHERE user_id=?", (new_random_id, message.from_user.id))
        db.commit()
        await message.answer(f"✅ ID успешно изменён на {new_random_id}.", reply_markup=create_premium_menu())

    db.close()
    await state.clear()

@router.message(F.text == "📝 Отправить отзыв")
async def ask_for_review(message: Message, state: FSMContext):
    try:
        # Проверяем регистрацию пользователя
        user_id = str(message.from_user.id)
        cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        if not cursor.fetchone():
            await message.answer("❌ Пожалуйста, сначала зарегистрируйтесь используя /register")
            return

        await message.answer("Пожалуйста, напишите ваш отзыв.")
        await state.set_state(ReviewStates.waiting_for_review)
    except Exception as e:
        logging.error(f"Ошибка при запросе отзыва: {e}")
        await message.answer("❌ Произошла ошибка. Пожалуйста, попробуйте позже.")

@router.message(ReviewStates.waiting_for_review)
async def handle_review(message: Message, state: FSMContext):
    try:
        user_id = str(message.from_user.id)
        review_text = message.text.strip()

        if not review_text:
            await message.answer("❌ Отзыв не может быть пустым. Пожалуйста, напишите что-нибудь.")
            return

        # Сохраняем отзыв в базу данных
        cursor.execute("""
            INSERT INTO reviews (user_id, review_text, review_date)
            VALUES (?, ?, ?)
        """, (user_id, review_text, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()

        # Отправляем отзыв администратору
        admin_message = (
            f"📝 Новый отзыв\n"
            f"От: @{message.from_user.username or 'Нет username'} (ID: {user_id})\n"
            f"Текст: {review_text}"
        )
        await bot.send_message(chat_id=int(config.ADMIN_PREM), text=admin_message)

        await message.answer("✅ Спасибо за ваш отзыв! Мы обязательно учтем ваше мнение.")

    except Exception as e:
        logging.error(f"Ошибка при обработке отзыва: {e}")
        await message.answer("❌ Произошла ошибка при сохранении отзыва. Пожалуйста, попробуйте позже.")
    finally:
        await state.clear()

class AdminPremiumStates(StatesGroup):
    waiting_for_user_id_take = State()  # Состояние для команды /take_premium
    waiting_for_user_id_give = State()  # Состояние для команды /give_premium


@router.message(Command("take_premium"))
async def take_premium(message: Message, state: FSMContext):
    if str(message.from_user.id) not in ADMIN_IDS:
        await message.answer("У вас нет прав на выполнение этой команды.")
        return

    await message.answer("Введите ID игрока, у которого вы хотите забрать премиум-статус:")
    await state.set_state(AdminPremiumStates.waiting_for_user_id_take)  # Устанавливаем состояние для /take_premium


@router.message(AdminPremiumStates.waiting_for_user_id_take)
async def process_take_premium_id(message: Message, state: FSMContext):
    player_id = message.text.strip()

    if not player_id.isdigit():
        await message.answer("Ошибка: Введенный ID не является числом.")
        await state.clear()
        return

    cursor.execute("SELECT user_name, premium, user_id FROM users WHERE random_id = ?", (player_id,))
    player = cursor.fetchone()

    if not player:
        await message.answer("Ошибка: Игрок с таким ID не найден.")
        await state.clear()
        return

    try:
        # Забираем премиум-статус
        cursor.execute("UPDATE users SET premium = 'нет' WHERE random_id = ?", (player_id,))
        conn.commit()

        await message.answer(f"Премиум-статус был успешно убран у игрока с ID {player_id}.")

        # Обновляем меню
        markup = get_main_menu(premium=False)
        await bot.send_message(
            player[2],
            "Ваш премиум-статус был убран. Теперь у вас больше нет доступа к эксклюзивным функциям.",
            reply_markup=markup
        )
        await bot.send_message(player[2], "Меню обновлено!")

    except Exception as e:
        conn.rollback()
        await message.answer(f"Ошибка при обновлении базы данных: {str(e)}")
    finally:
        await state.clear()


@router.message(Command("give_premium"))
async def give_premium(message: Message, state: FSMContext):
    if str(message.from_user.id) not in ADMIN_IDS:
        await message.answer("У вас нет прав на выполнение этой команды.")
        return

    await message.answer("Введите ID игрока, которому вы хотите выдать премиум-статус:")
    await state.set_state(AdminPremiumStates.waiting_for_user_id_give)  # Устанавливаем состояние для /give_premium


@router.message(AdminPremiumStates.waiting_for_user_id_give)
async def process_give_premium_id(message: Message, state: FSMContext):
    player_id = message.text.strip()

    # Логирование ID
    print(f"Введен ID игрока: {player_id}")  # Логируем введенный ID

    if not player_id.isdigit():
        await message.answer("Ошибка: Введенный ID не является числом.")
        await state.clear()
        return

    cursor.execute("SELECT user_name, premium, user_id FROM users WHERE random_id = ?", (player_id,))
    player = cursor.fetchone()

    if not player:
        await message.answer("Ошибка: Игрок с таким ID не найден.")
        await state.clear()
        return

    print(f"Данные игрока из базы: {player}")  # Логируем данные игрока из базы

    # Убираем пробелы, если они есть
    if player[1].strip() == 'да':
        await message.answer("Ошибка: У этого игрока уже есть премиум-статус.")
        await state.clear()
        return

    try:
        # Обновляем статус игрока на 'да'
        cursor.execute("UPDATE users SET premium = 'да' WHERE random_id = ?", (player_id,))
        conn.commit()

        await message.answer(f"Премиум-статус был успешно выдан игроку с ID {player_id}.")

        # Обновляем меню
        markup = get_main_menu(premium=True)
        await bot.send_message(
            player[2],
            f"Поздравляем, {player[0]}! Вы получили премиум-статус. Теперь у вас доступ к эксклюзивным функциям.",
            reply_markup=markup
        )
        await bot.send_message(player[2], "Меню обновлено!")

    except Exception as e:
        conn.rollback()
        await message.answer(f"Ошибка при обновлении базы данных: {str(e)}")
    finally:
        await state.clear()
@router.message(F.text == "👥 Друзья")
async def show_friends(message: Message):
    try:
        user_id = str(message.from_user.id)

        cursor.execute("""
            SELECT u.user_name, u.country, u.random_id, u.hidden, u.active_game
            FROM friends f
            JOIN users u ON f.friend_id = u.user_id
            WHERE f.user_id = ?
            UNION
            SELECT u.user_name, u.country, u.random_id, u.hidden, u.active_game
            FROM friends f
            JOIN users u ON f.user_id = u.user_id
            WHERE f.friend_id = ?
        """, (user_id, user_id))
        friends = cursor.fetchall()

        if not friends:
            try:
                photo = FSInputFile('friends.png')
                await message.answer_photo(
                    photo=photo,
                    caption="👥 Ваш список друзей пуст."
                )
            except:
                await message.answer("👥 Ваш список друзей пуст.")
            return

        response = "👥 Ваши друзья:\n\n"
        for friend in friends:
            if friend[3] == 0:  # Если профиль друга не скрыт
                status = "🎮 В игре" if friend[4] else "🟢 Онлайн"
                response += f"👤 {friend[0]} | {friend[1]} | ID: {friend[2]} | {status}\n"

        try:
            photo = FSInputFile('friends.png')
            await message.answer_photo(
                photo=photo,
                caption=response
            )
        except:
            await message.answer(response)

    except Exception as e:
        logging.error(f"Ошибка при обработке списка друзей: {e}")
        await message.answer("❌ Произошла ошибка при получении списка друзей.")

class FriendStates(StatesGroup):
    waiting_for_friend = State()

@router.message(F.text == "⚙️ Добавить друга")
async def add_friend_handler(message: Message, state: FSMContext):
    try:
        await state.update_data(user_id=str(message.from_user.id))
        await message.reply("Введите ID или никнейм вашего друга:")
        await state.set_state(FriendStates.waiting_for_friend)
    except Exception as e:
        await handle_error(e, message)

@router.message(FriendStates.waiting_for_friend)
async def process_friend_request(message: Message, state: FSMContext):
    try:
        data = await state.get_data()
        user_id = data['user_id']
        target = message.text.strip()

        if not target:
            await message.reply("❌ Вы не ввели ID или никнейм. Попробуйте снова.")
            await state.clear()
            return

        cursor.execute("""
            SELECT user_id, user_name, hidden, 
                   (SELECT COUNT(*) FROM friends WHERE 
                    (user_id = users.user_id AND friend_id = ?) OR 
                    (user_id = ? AND friend_id = users.user_id)) as is_friend
            FROM users 
            WHERE random_id = ? OR user_name = ?
        """, (user_id, user_id, target, target))
        result = cursor.fetchone()

        if not result:
            await message.reply("❌ Пользователь с таким ID или никнеймом не найден.")
            await state.clear()
            return

        friend_id, friend_name, is_hidden, is_friend = result

        if user_id == friend_id:
            await message.reply("❌ Вы не можете добавить себя в друзья.")
        elif is_hidden == 1:
            await message.reply(f"❌ Профиль {friend_name} скрыт.")
        elif is_friend > 0:
            await message.reply("❌ Этот пользователь уже в вашем списке друзей.")
        else:
            try:
                cursor.execute(
                    "INSERT INTO friends (user_id, friend_id, added_date) VALUES (?, ?, ?)",
                    (user_id, friend_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                )
                conn.commit()
                await message.reply(f"✅ Пользователь {friend_name} успешно добавлен в друзья!")
            except Exception as e:
                conn.rollback()
                await message.reply("❌ Произошла ошибка при добавлении друга.")
                logging.error(f"Error adding friend: {e}")

    except Exception as e:
        await handle_error(e, message)
    finally:
        await state.clear()
@router.message(F.text == "🎮 Все игроки")
async def show_all_players(message: Message):
    try:
        cursor.execute("""
            SELECT user_name, country, random_id, hidden, active_game,
                   kills, deaths, match_count, premium
            FROM users 
            WHERE hidden = 0
            ORDER BY match_count DESC, kills DESC
        """)
        players = cursor.fetchall()

        if not players:
            await message.reply("👥 Список игроков пуст")
            return

        response = "👥 Список всех игроков:\n\n"
        for player in players:
            name, country, player_id, _, active_game, kills, deaths, matches, premium = player
            kd_ratio = kills / max(deaths, 1)
            status = "🎮 В игре" if active_game else "🟢 Онлайн"
            premium_status = "⭐" if premium == 'да' else ""

            response += (
                f"{premium_status}👤 {name} | {country}\n"
                f"📊 K/D: {kd_ratio:.2f} | Матчи: {matches}\n"
                f"🆔 ID: {player_id} | {status}\n"
                f"───────────────\n"
            )

        # Разбиваем длинное сообщение
        if len(response) > 4096:
            for x in range(0, len(response), 4096):
                await message.answer(response[x:x+4096])
        else:
            await message.answer(response)

    except Exception as e:
        await handle_error(e, message)

class SearchManager:
    def __init__(self):
        self.player_searches = {}
        self.active_searches = {}
        self.active_servers = {}

    def create_new_search(self):
        search_id = len(self.active_searches) + 1
        self.active_searches[search_id] = {'players': []}
        return search_id

search_manager = SearchManager()

@router.message(F.text == "📊 Статистика")
async def show_statistics(message: Message):
    try:
        user_id = str(message.from_user.id)
        cursor.execute("""
            SELECT kills, deaths, match_count, wins, losses, 
                   adr, avg, premium, elo
            FROM users 
            WHERE user_id = ?
        """, (user_id,))
        stats = cursor.fetchone()

        if not stats:
            await message.reply("❌ Статистика не найдена.")
            return

        kills, deaths, matches, wins, losses, adr, avg, premium, elo = stats
        kd_ratio = kills / max(deaths, 1)
        win_rate = wins / max(matches, 1) * 100

        # Расчет уровня
        level = 1
        if elo > 500: level = 2
        if elo > 750: level = 3
        if elo > 900: level = 4
        if elo > 1050: level = 5
        if elo > 1200: level = 6
        if elo > 1350: level = 7
        if elo > 1530: level = 8
        if elo > 1750: level = 9
        if elo > 2000: level = 10

        stats_message = (
            "📊 Ваша статистика:\n"
            f"🎯 K/D: {kd_ratio:.2f}\n"
            f"🎮 Матчей сыграно: {matches}\n"
            f"🔫 Убийств: {kills}\n"
            f"💀 Смертей: {deaths}\n"
            f"🏆 Побед: {wins}\n"
            f"❌ Поражений: {losses}\n"
            f"📈 Процент побед: {win_rate:.1f}%\n"
            f"⭐️ Уровень: {level} ({elo} ELO)\n"
        )

        if premium == 'да':
            stats_message += (
                "\n⭐ Премиум статистика:\n"
                f"💢 ADR: {adr:.1f}\n"
                f"📊 Средний рейтинг: {avg:.1f}\n"
            )

        try:
            photo = FSInputFile('stats.png')
            await message.answer_photo(photo=photo, caption=stats_message)
        except:
            await message.answer(stats_message)

    except Exception as e:
        logging.error(f"Ошибка при показе статистики: {e}")
        await message.answer("❌ Произошла ошибка. Пожалуйста, попробуйте еще раз.")

@router.callback_query(F.data.startswith("admin_"))
async def handle_admin_actions(callback: CallbackQuery):
    try:
        user_id = str(callback.from_user.id)
        if user_id not in ADMIN_IDS:
            await callback.answer("❌ Недостаточно прав.")
            return

        action = callback.data.split("_")[1]

        if action == "restart_servers":
            await cleanup_servers()
            await callback.answer("✅ Серверы перезапущены.")
            await callback.message.edit_text("✅ Серверы успешно перезапущены.")

        elif action == "system_stats":
            stats = await get_system_stats()
            await callback.message.edit_text(stats)

        elif action == "manage_bans":
            await show_banned_users(callback.message)

    except Exception as e:
        await handle_error(e, callback.message)

async def get_system_stats():
    try:
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM users WHERE premium = 'да'")
        premium_users = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM bans WHERE unban_date > datetime('now')")
        active_bans = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*), 
                   SUM(match_count), 
                   SUM(kills), 
                   SUM(deaths)
            FROM users
        """)
        stats = cursor.fetchone()

        return (
            "📊 Статистика системы:\n\n"
            f"👥 Всего пользователей: {total_users}\n"
            f"⭐ Премиум пользователей: {premium_users}\n"
            f"🚫 Активных банов: {active_bans}\n"
            f"🎮 Всего матчей: {stats[1] or 0}\n"
            f"💥 Всего убийств: {stats[2] or 0}\n"
            f"💀 Всего смертей: {stats[3] or 0}\n"
            f"🎲 Активных серверов: {len(search_manager.active_servers)}\n"
            f"🔍 Игроков в поиске: {len(search_manager.player_searches)}"
        )
    except Exception as e:
        logging.error(f"Error getting system stats: {e}")
        return "❌ Ошибка получения статистики"
async def show_banned_users(message: Message):
    try:
        cursor.execute("""
            SELECT u.user_name, b.ban_reason, b.ban_date, b.unban_date
            FROM bans b
            JOIN users u ON b.user_id = u.user_id
            WHERE b.unban_date > datetime('now')
            ORDER BY b.unban_date DESC
        """)
        bans = cursor.fetchall()

        if not bans:
            await message.edit_text("🚫 Нет активных банов")
            return

        ban_list = "🚫 Список забаненных пользователей:\n\n"
        for ban in bans:
            ban_list += (
                f"👤 {ban[0]}\n"
                f"📝 Причина: {ban[1]}\n"
                f"📅 Дата бана: {ban[2]}\n"
                f"📅 Разбан: {ban[3]}\n"
                "───────────────\n"
            )

        await message.edit_text(ban_list)
    except Exception as e:
        await handle_error(e, message)

class ReportStates(StatesGroup):
    waiting_for_report = State()

@router.message(F.text == "📝Жалоба на игрока")
async def start_report(message: Message, state: FSMContext):
    try:
        # Проверяем регистрацию пользователя
        user_id = str(message.from_user.id)
        cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        if not cursor.fetchone():
            await message.answer("❌ Пожалуйста, сначала зарегистрируйтесь используя /register")
            return

        await message.answer(
            "📝 Опишите вашу жалобу в одном сообщении:\n\n"
            "• Никнейм игрока\n"
            "• Причина жалобы\n"
            "• Описание ситуации"
        )
        await state.set_state(ReportStates.waiting_for_report)

    except Exception as e:
        logging.error(f"Ошибка при создании жалобы: {e}")
        await message.answer("❌ Произошла ошибка. Пожалуйста, попробуйте позже.")

@router.message(ReportStates.waiting_for_report)
async def process_report(message: Message, state: FSMContext):
    try:
        user_id = str(message.from_user.id)
        report_text = message.text.strip()

        if not report_text:
            await message.answer("❌ Жалоба не может быть пустой. Пожалуйста, опишите ситуацию.")
            return

        # Сохраняем жалобу в базу данных
        cursor.execute("""
            INSERT INTO reports (user_id, report_text, report_date, status)
            VALUES (?, ?, ?, 'pending')
        """, (user_id, report_text, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()

        # Отправляем жалобу администратору
        admin_message = (
            f"📝 Новая жалоба\n"
            f"От: @{message.from_user.username or 'Нет username'} (ID: {user_id})\n"
            f"Текст жалобы:\n{report_text}"
        )
        await bot.send_message(chat_id=int(config.ADMIN_PREM), text=admin_message)

        await message.answer("✅ Ваша жалоба отправлена администратору. Мы рассмотрим её в ближайшее время.")

    except Exception as e:
        logging.error(f"Ошибка при обработке жалобы: {e}")
        await message.answer("❌ Произошла ошибка при отправке жалобы. Пожалуйста, попробуйте позже.")
    finally:
        await state.clear()

class NewsStates(StatesGroup):
    waiting_for_news = State()

@router.message(Command("send_news"))
async def send_news(message: Message, state: FSMContext):
    if str(message.from_user.id) in ADMIN_IDS:
        await message.answer("Пожалуйста, введите текст новости.")
        await state.set_state(NewsStates.waiting_for_news)
    else:
        await message.answer("У вас нет прав для отправки новостей.")

@router.message(NewsStates.waiting_for_news)
async def send_news_to_all(message: Message, state: FSMContext):
    try:
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()

        if users:
            failed_users = []
            for user in users:
                try:
                    await bot.send_message(user[0], f"📰 Новость: {message.text}")
                except Exception as e:
                    failed_users.append(user[0])
                    logging.error(f"Failed to send news to user {user[0]}: {e}")

            success_count = len(users) - len(failed_users)
            await message.answer(
                f"Новость успешно отправлена {success_count} пользователям!\n"
                f"Не удалось отправить {len(failed_users)} пользователям."
            )
        else:
            await message.answer("В базе данных нет пользователей для рассылки.")
    except Exception as e:
        await message.answer(f"Произошла ошибка при отправке новости: {e}")
    finally:
        await state.clear()

async def activate_premium(user_id: str, inviter_id: str):
    try:
        cursor.execute('UPDATE users SET premium = "да" WHERE user_id = ?', (user_id,))

        cursor.execute('SELECT premium FROM users WHERE user_id = ?', (inviter_id,))
        inviter = cursor.fetchone()

        if inviter and inviter[0] != 'да':
            cursor.execute('UPDATE users SET premium = "да" WHERE user_id = ?', (inviter_id,))

        cursor.execute('UPDATE users SET referral_count = referral_count + 1 WHERE user_id = ?', (inviter_id,))
        conn.commit()

        await bot.send_message(
            user_id,
            "Вы успешно зарегистрировались по реферальному коду! Вы теперь премиум-пользователь!"
        )

        await bot.send_message(
            inviter_id,
            f"Ваш реферальный код был использован! {user_id} стал премиум-пользователем."
        )

        markup_user = create_main_menu(premium=True)
        markup_inviter = create_main_menu(premium=True)

        await bot.send_message(user_id, "Меню обновлено!", reply_markup=markup_user)
        await bot.send_message(inviter_id, "Меню обновлено!", reply_markup=markup_inviter)

        # Планируем деактивацию через 100 секунд
        asyncio.create_task(deactivate_premium_later(user_id))

    except Exception as e:
        logging.error(f"Error in activate_premium: {e}")
        raise

async def deactivate_premium_later(user_id: str):
    await asyncio.sleep(100)
    await deactivate_premium(user_id)

async def deactivate_premium(user_id: str):
    try:
        cursor.execute('UPDATE users SET premium = "нет" WHERE user_id = ?', (user_id,))
        conn.commit()

        markup = create_main_menu(premium=False)
        await bot.send_message(
            user_id,
            "Ваш премиум статус истек.",
            reply_markup=markup
        )
    except Exception as e:
        logging.error(f"Error in deactivate_premium: {e}")

class ReferralStates(StatesGroup):
    waiting_for_code = State()
def generate_referral_code() -> str:
    """Генерирует уникальный реферальный код"""
    while True:
        # Генерируем 6-значный код
        code = ''.join(random.choices(string.digits, k=6))

        # Проверяем, не существует ли уже такой код
        cursor.execute("SELECT user_id FROM users WHERE referral_code = ?", (code,))
        if not cursor.fetchone():
            return code

def generate_random_password(length: int = 8) -> str:
    """Генерирует случайный пароль"""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choices(characters, k=length))

def search_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру для поиска игры"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Начать", callback_data="start_search"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_search")
        ]
    ])
    return keyboard

def generate_status_message(search_id: int) -> str:
    """Генерирует сообщение о статусе поиска"""
    search_data = search_manager.active_searches.get(search_id)
    if not search_data:
        return "❌ Поиск не найден"

    current_players = len(search_data['players'])
    player_list = "\n".join([f"👤 {p['name']}" for p in search_data['players']])

    return (
        f"🔍 Поиск игры\n\n"
        f"👥 Игроки ({current_players}/{config.MAX_PLAYERS}):\n"
        f"{player_list}\n\n"
        f"⏳ Ожидание игроков..."
    )
@router.message(Command("referalcode"))
async def referalcode(message: Message, state: FSMContext):
    await message.answer("Введите реферальный код:")
    await state.set_state(ReferralStates.waiting_for_code)

@router.message(ReferralStates.waiting_for_code)
async def handle_referral_code(message: Message, state: FSMContext):
    try:
        user_id = str(message.from_user.id)
        referral_code = message.text.strip()

        cursor.execute(
            'SELECT user_id, premium, used FROM users WHERE referral_code = ?',
            (referral_code,)
        )
        result = cursor.fetchone()

        if not result:
            await message.answer("Недействительный реферальный код.")
            await state.clear()
            return

        inviter_id, inviter_premium, used = result

        cursor.execute('SELECT used FROM users WHERE user_id = ?', (user_id,))
        user_data = cursor.fetchone()

        if user_data and user_data[0] == 1:
            await message.answer("Вы уже использовали реферальный код.")
        elif str(inviter_id) == user_id:
            await message.answer("Невозможно использовать свой собственный код.")
        else:
            await activate_premium(user_id, inviter_id)
            cursor.execute('UPDATE users SET used = 1 WHERE user_id = ?', (user_id,))
            conn.commit()

    except Exception as e:
        await message.answer(f"Произошла ошибка при обработке кода: {str(e)}")
        logging.error(f"Error in handle_referral_code: {e}")
    finally:
        await state.clear()
class BanStates(StatesGroup):
    waiting_for_username = State()
    waiting_for_reason = State()
    waiting_for_duration = State()

class UnbanStates(StatesGroup):
    waiting_for_username = State()

@router.message(Command("ban"))
async def ban_user(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS2:
        await message.answer("У вас нет прав для выполнения этой команды.")
        return

    await message.answer("Введите имя пользователя, которого нужно забанить:")
    await state.set_state(BanStates.waiting_for_username)

@router.message(BanStates.waiting_for_username)
async def process_ban_by_name(message: Message, state: FSMContext):
    user_name_to_ban = message.text.strip()

    cursor.execute(
        "SELECT user_id, user_name, ban_end_time FROM users WHERE user_name=?",
        (user_name_to_ban,)
    )
    user = cursor.fetchone()

    if not user:
        await message.answer("Пользователь с таким именем не найден.")
        await state.clear()
        return

    user_id_to_ban, user_name, ban_end_time = user

    if ban_end_time:
        ban_end_time = datetime.strptime(ban_end_time, '%Y-%m-%d %H:%M:%S')
        if ban_end_time < datetime.now():
            cursor.execute(
                "UPDATE users SET ban_status=0, ban_reason=NULL WHERE user_id=?",
                (user_id_to_ban,)
            )
            conn.commit()
            await message.answer(f"Бан у пользователя {user_name} истек. Статус снят.")
            await state.clear()
            return

    await state.update_data(user_id_to_ban=user_id_to_ban, user_name=user_name)
    await message.answer(
        f"Пользователь {user_name} найден (ID: {user_id_to_ban}). Укажите причину бана:"
    )
    await state.set_state(BanStates.waiting_for_reason)

@router.message(BanStates.waiting_for_reason)
async def ask_ban_duration(message: Message, state: FSMContext):
    await state.update_data(reason=message.text.strip())
    await message.answer(
        "Теперь укажите, на какое время забанить пользователя "
        "(например, 1d - 1 день, 2h - 2 часа, 1w - 1 неделя):"
    )
    await state.set_state(BanStates.waiting_for_duration)

@router.message(BanStates.waiting_for_duration)
async def apply_ban(message: Message, state: FSMContext):
    try:
        duration = message.text.strip()
        data = await state.get_data()
        user_id_to_ban = data['user_id_to_ban']
        reason = data['reason']
        user_name = data['user_name']

        time_units = {'h': 'hours', 'd': 'days', 'w': 'weeks'}
        time_value = 0
        time_unit = None

        for unit, full_unit in time_units.items():
            if unit in duration:
                time_value = int(''.join(filter(str.isdigit, duration)))
                time_unit = full_unit
                break

        if time_value == 0 or not time_unit:
            await message.answer(
                "Неверный формат времени. Укажите время в формате 1d, 2h, 1w и т.д."
            )
            return

        if time_unit == 'hours':
            ban_end_time = datetime.now() + timedelta(hours=time_value)
        elif time_unit == 'days':
            ban_end_time = datetime.now() + timedelta(days=time_value)
        else:  # weeks
            ban_end_time = datetime.now() + timedelta(weeks=time_value)

        ban_end_time_str = ban_end_time.strftime('%Y-%m-%d %H:%M:%S')

        cursor.execute(
            """UPDATE users 
               SET ban_status=1, ban_reason=?, ban_end_time=? 
               WHERE user_id=?""",
            (reason, ban_end_time_str, user_id_to_ban)
        )
        conn.commit()

        await message.answer(
            f"Пользователь {user_name} забанен.\n"
            f"Причина: {reason}\n"
            f"Время окончания бана: {ban_end_time_str}"
        )

        logging.info(
            f"Пользователь {user_name} ({user_id_to_ban}) забанен. "
            f"Причина: {reason}. Время окончания: {ban_end_time_str}"
        )

    except Exception as e:
        await message.answer(f"Произошла ошибка при бане пользователя: {str(e)}")
        logging.error(f"Ошибка при бане пользователя {user_id_to_ban}: {str(e)}")
    finally:
        await state.clear()

@router.message(Command("unban"))
async def unban_user(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS2:
        await message.answer("У вас нет прав для выполнения этой команды.")
        return

    await message.answer("Введите имя пользователя, которого нужно разбанить:")
    await state.set_state(UnbanStates.waiting_for_username)

@router.message(UnbanStates.waiting_for_username)
async def process_unban_by_name(message: Message, state: FSMContext):
    try:
        user_name_to_unban = message.text.strip()

        cursor.execute(
            "SELECT user_id, user_name, ban_status FROM users WHERE user_name=?",
            (user_name_to_unban,)
        )
        user = cursor.fetchone()

        if not user:
            await message.answer("Пользователь с таким именем не найден.")
            await state.clear()
            return

        user_id_to_unban, user_name, ban_status = user

        if ban_status == 0:
            await message.answer(f"Пользователь {user_name} уже не забанен.")
            await state.clear()
            return

        cursor.execute(
            """UPDATE users 
               SET ban_status=0, ban_reason=NULL, ban_end_time=NULL 
               WHERE user_id=?""",
            (user_id_to_unban,)
        )
        conn.commit()
        await message.answer(f"Пользователь {user_name} разбанен.")

        logging.info(f"Пользователь {user_name} ({user_id_to_unban}) разбанен.")

    except Exception as e:
        await message.answer(f"Произошла ошибка при снятии бана: {str(e)}")
        logging.error(f"Ошибка при разбане пользователя: {str(e)}")
    finally:
        await state.clear()
# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format=config.LOG_FORMAT
)
logger = logging.getLogger(__name__)

# Инициализация бота
bot = Bot(token=config.BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

class SSHManager:
    def __init__(self):
        self.ssh_conn = None
        self.lock = asyncio.Lock()

    async def connect(self):
        """Устанавливает SSH соединение"""
        try:
            if self.ssh_conn:
                try:
                    self.ssh_conn.close()
                except:
                    pass

            max_attempts = 3
            attempt = 0
            retry_delay = 2

            while attempt < max_attempts:
                try:
                    self.ssh_conn = await asyncssh.connect(
                        host=config.SSH_HOST,
                        port=int(config.SSH_PORT),
                        username=config.SSH_USER,
                        password=config.SSH_PASSWORD,
                        known_hosts=None
                    )
                    logger.info("SSH соединение установлено успешно")
                    return True

                except (asyncssh.DisconnectError, asyncssh.ProcessError) as e:
                    logger.error(f"SSH ошибка (попытка {attempt + 1}/{max_attempts}): {str(e)}")
                    attempt += 1

                except Exception as e:
                    logger.error(f"Неожиданная ошибка SSH: {str(e)}")
                    break

                if attempt < max_attempts:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2

            return False

        except Exception as e:
            logger.error(f"Критическая ошибка SSH подключения: {str(e)}")
            return False

    async def execute_command(self, command):
        """Выполняет SSH команду"""
        async with self.lock:
            try:
                if not self.ssh_conn:
                    if not await self.connect():
                        return None, None

                process = await self.ssh_conn.run(command)
                return process.stdout, process.stderr

            except Exception as e:
                logger.error(f"Ошибка выполнения команды: {str(e)}")
                if await self.connect():
                    process = await self.ssh_conn.run(command)
                    return process.stdout, process.stderr
                return None, None

    async def close(self):
        """Закрывает SSH соединение"""
        if self.ssh_conn:
            try:
                self.ssh_conn.close()
            except:
                pass
            self.ssh_conn = None

# Создание глобального SSH менеджера

class SSHManager:
    def __init__(self):
        self.ssh_conn = None
        self.lock = asyncio.Lock()

    async def connect(self):
        """Устанавливает SSH соединение"""
        try:
            if self.ssh_conn:
                try:
                    self.ssh_conn.close()
                except:
                    pass

            max_attempts = 3
            attempt = 0
            retry_delay = 2

            while attempt < max_attempts:
                try:
                    self.ssh_conn = await asyncssh.connect(
                        host=config.SSH_HOST,
                        port=int(config.SSH_PORT),
                        username=config.SSH_USER,
                        password=config.SSH_PASSWORD,
                        known_hosts=None
                    )
                    logger.info("SSH соединение установлено успешно")
                    return True

                except (asyncssh.DisconnectError, asyncssh.ProcessError) as e:
                    logger.error(f"SSH ошибка (попытка {attempt + 1}/{max_attempts}): {str(e)}")
                    attempt += 1

                except Exception as e:
                    logger.error(f"Неожиданная ошибка SSH: {str(e)}")
                    break

                if attempt < max_attempts:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2

            return False

        except Exception as e:
            logger.error(f"Критическая ошибка SSH подключения: {str(e)}")
            return False

    async def execute_command(self, command):
        """Выполняет SSH команду"""
        async with self.lock:
            try:
                if not self.ssh_conn:
                    if not await self.connect():
                        return None, None

                process = await self.ssh_conn.run(command)
                return process.stdout, process.stderr

            except Exception as e:
                logger.error(f"Ошибка выполнения команды: {str(e)}")
                if await self.connect():
                    process = await self.ssh_conn.run(command)
                    return process.stdout, process.stderr
                return None, None

    async def close(self):
        """Закрывает SSH соединение"""
        if self.ssh_conn:
            try:
                self.ssh_conn.close()
            except:
                pass
            self.ssh_conn = None
class SearchManager:
    def __init__(self):
        self.active_searches = {}
        self.player_searches = {}
        self.search_counter = 0
        self.player_active_matches = {}

    def create_new_search(self):
        self.search_counter += 1
        search_id = self.search_counter
        self.active_searches[search_id] = {
            'players': [],
            'messages': {},
            'start_time': datetime.now()
        }
        logger.info(f"Создан новый поиск с ID {search_id}")
        return search_id

    def add_player(self, search_id, player_data):
        user_id = str(player_data['user_id'])

        if user_id in self.player_searches:
            old_search_id = self.player_searches[user_id]
            if old_search_id != search_id:
                self.remove_player(user_id)

        if search_id in self.active_searches:
            if len(self.active_searches[search_id]['players']) >= config.MAX_PLAYERS:
                logger.warning(f"Достигнут максимум игроков в поиске {search_id}")
                return False

            self.active_searches[search_id]['players'].append(player_data)
            self.player_searches[user_id] = search_id
            logger.info(f"Игрок {user_id} добавлен в поиск {search_id}")
            return True
        return False

    def remove_player(self, user_id):
        search_id = self.player_searches.get(str(user_id))
        if search_id and search_id in self.active_searches:
            players = list(self.active_searches[search_id]['players'])
            self.active_searches[search_id]['players'] = [
                player for player in players
                if str(player['user_id']) != str(user_id)
            ]
            self.active_searches[search_id]['messages'].pop(str(user_id), None)
            self.player_searches.pop(str(user_id), None)

            logger.info(f"Игрок {user_id} удален из поиска {search_id}")

            if not self.active_searches[search_id]['players']:
                self.active_searches.pop(search_id, None)
                logger.info(f"Поиск {search_id} удален, так как не осталось игроков")

    def is_player_in_search(self, user_id):
        return str(user_id) in self.player_searches

    def is_player_in_match(self, user_id):
        return str(user_id) in self.player_active_matches

    def add_player_to_match(self, user_id, screen_name):
        self.player_active_matches[str(user_id)] = screen_name
        logger.info(f"Игрок {user_id} добавлен в матч {screen_name}")

    def remove_player_from_match(self, user_id):
        user_id = str(user_id)
        if user_id in self.player_active_matches:
            screen_name = self.player_active_matches.pop(user_id)
            logger.info(f"Игрок {user_id} удален из матча {screen_name}")

    def get_player_search(self, user_id):
        search_id = self.player_searches.get(str(user_id))
        return self.active_searches.get(search_id)

    async def cleanup_inactive_matches(self):
        inactive_players = []

        for user_id, screen_name in self.player_active_matches.items():
            stdout, stderr = await ssh_manager.execute_command(f"screen -ls | grep {screen_name}")
            if stdout and not stdout:
                inactive_players.append(user_id)

        for user_id in inactive_players:
            self.remove_player_from_match(user_id)
            logger.info(f"Очищен неактивный матч для игрока {user_id}")

# Создание глобального менеджера поиска
search_manager = SearchManager()

async def check_port_availability():
    """Проверяет доступность портов"""
    try:
        for port in range(config.SERVER_START_PORT, config.SERVER_END_PORT + 1):
            stdout, stderr = await ssh_manager.execute_command(f"netstat -tuln | grep :{port}")
            if not stdout or not stdout.strip():
                logger.info(f"Найден свободный порт: {port}")
                return port

        logger.error("Все порты заняты")
        return None
    except Exception as e:
        logger.error(f"Ошибка проверки портов: {e}")
        return None

async def check_server_status(screen_name):
    """Проверяет статус сервера"""
    try:
        match_logger = logging.getLogger(screen_name)

        stdout, stderr = await ssh_manager.execute_command(f"screen -ls | grep {screen_name}")
        if stdout:
            screen_status = stdout
            match_logger.debug(f"Статус screen сессии: {screen_status}")

            if not screen_status:
                match_logger.error("Screen сессия не найдена")
                return None

            await ssh_manager.execute_command(f"rm -f /tmp/status_{screen_name}.txt")
            await asyncio.sleep(1)

            await ssh_manager.execute_command(f"screen -S {screen_name} -X stuff 'status\\n'")
            await asyncio.sleep(10)

            await ssh_manager.execute_command(f"screen -S {screen_name} -X hardcopy /tmp/status_{screen_name}.txt")
            await asyncio.sleep(2)

            stdout, stderr = await ssh_manager.execute_command(f"cat /tmp/status_{screen_name}.txt")
            if stdout:
                status_output = stdout
                match_logger.debug(f"Полный вывод статуса:\n{status_output}")

                active_players = set()
                ct_score = 0
                t_score = 0
                game_ended = False

                for line in status_output.split('\n'):
                    if '#' in line and ('STEAM' in line or 'player' in line.lower()):
                        if 'active' in line.lower():
                            parts = line.split()
                            if len(parts) >= 5:
                                try:
                                    player_name = parts[2].strip('"')
                                    player_ip = parts[-1].split(':')[0]
                                    active_players.add(f"{player_name}_{player_ip}")
                                except Exception as e:
                                    match_logger.error(f"Ошибка при обработке строки игрока: {line}. Ошибка: {e}")

                    if 'CT' in line and 'score' in line.lower():
                        try:
                            ct_score = int(line.split()[-1])
                        except Exception as e:
                            match_logger.error(f"Ошибка парсинга CT score: {e}")
                    if 'TERRORIST' in line and 'score' in line.lower():
                        try:
                            t_score = int(line.split()[-1])
                        except Exception as e:
                            match_logger.error(f"Ошибка парсинга T score: {e}")

                    if 'game over' in line.lower() or 'match ended' in line.lower():
                        game_ended = True

                if ct_score >= config.WINNING_SCORE or t_score >= config.WINNING_SCORE:
                    game_ended = True

                return {
                    'active_players': len(active_players),
                    'ct_score': ct_score,
                    't_score': t_score,
                    'game_ended': game_ended
                }

        return None

    except Exception as e:
        match_logger.error(f"Ошибка проверки статуса сервера: {e}")
        return None

async def start_server(selected_map, server_password):
    """Запускает игровой сервер"""
    try:
        port = await check_port_availability()
        if not port:
            logger.error("Нет свободных портов")
            return None

        screen_name = f"server_{selected_map}_{port}_{int(datetime.now().timestamp())}"
        match_logger = setup_match_logger(screen_name)
        match_logger.info(f"Запуск сервера: {screen_name}")

        stdout, stderr = await ssh_manager.execute_command(f"netstat -tuln | grep :{port}")
        if stdout:
            match_logger.error(f"Порт {port} уже занят")
            return None

        config_command = f"echo 'sv_password {server_password}' > {config.BASE_SERVER_PATH}/cfg/server_password.cfg"
        await ssh_manager.execute_command(config_command)
        await asyncio.sleep(2)

        launch_command = (
            f"cd {config.BASE_SERVER_PATH} && "
            f"screen -dmS {screen_name} bash -c '"
            f"export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:./bin && "
            f"./dedicated_launcher -console +map {selected_map} "
            f"-maxplayers {config.MAX_PLAYERS} -port {port} "
            f"+sv_lan 0 -game cm -tickrate 100'"
        )

        await ssh_manager.execute_command(launch_command)
        await asyncio.sleep(15)

        stdout, stderr = await ssh_manager.execute_command(f"screen -ls | grep {screen_name}")
        if not stdout:
            match_logger.error("Сервер не запустился")
            return None

        server_commands = [
            f"sv_password {server_password}",
            "mp_warmuptime 900",
            "mp_autoteambalance 0",
            "mp_limitteams 0",
            "mp_warmup_start"
        ]

        for cmd in server_commands:
            await ssh_manager.execute_command(f"screen -S {screen_name} -X stuff '{cmd}\\n'")
            await asyncio.sleep(2)

        match_logger.info(f"Сервер успешно запущен на порту {port}")
        return screen_name, port

    except Exception as e:
        logger.error(f"Ошибка запуска сервера: {e}")
        return None

def setup_match_logger(screen_name):
    """Создает логгер для матча"""
    log_file = os.path.join(config.LOG_DIRECTORY, f"match_{screen_name}.log")
    match_logger = logging.getLogger(screen_name)
    match_logger.setLevel(logging.INFO)

    if not match_logger.handlers:
        handler = logging.FileHandler(log_file)
        handler.setFormatter(logging.Formatter(config.LOG_FORMAT))
        match_logger.addHandler(handler)

    return match_logger

async def start_match(screen_name):
    """Запускает матч"""
    try:
        await ssh_manager.execute_command(f"screen -S {screen_name} -X stuff 'mp_warmup_end\\n'")
        return True
    except Exception as e:
        logger.error(f"Ошибка запуска матча: {e}")
        return False

async def stop_server(screen_name):
    """Останавливает сервер"""
    try:
        match_logger = logging.getLogger(screen_name)
        match_logger.info("Остановка сервера")

        stdout, stderr = await ssh_manager.execute_command(f"screen -ls | grep {screen_name}")
        if not stdout:
            match_logger.warning("Screen сессия не найдена")
            return True

        await ssh_manager.execute_command(f"screen -S {screen_name} -X stuff 'quit\\n'")
        await asyncio.sleep(2)

        await ssh_manager.execute_command(f"screen -S {screen_name} -X quit")
        await asyncio.sleep(1)

        stdout, stderr = await ssh_manager.execute_command(f"screen -ls | grep {screen_name}")
        if stdout:
            await ssh_manager.execute_command(f"pkill -f {screen_name}")
            await asyncio.sleep(1)

        await ssh_manager.execute_command(f"rm -f /tmp/status_{screen_name}.txt")
        await ssh_manager.execute_command(f"rm -f /tmp/match_start_{screen_name}.txt")

        match_logger.info("Сервер успешно остановлен")
        return True

    except Exception as e:
        logger.error(f"Ошибка остановки сервера {screen_name}: {e}")
        return False

async def monitor_server(screen_name, player_ids):
    """Мониторит состояние сервера"""
    match_logger = setup_match_logger(screen_name)
    match_logger.info(f"Начало мониторинга сервера {screen_name}")
    match_logger.info(f"Игроки: {player_ids}")

    start_time = datetime.now().timestamp()
    empty_server_checks = 0
    warned_times = set()
    match_started = False
    initial_connection_time = 500  # 5 минут на первоначальное подключение
    check_interval = 10  # интервал проверок в секундах

    for user_id in player_ids:
        search_manager.add_player_to_match(str(user_id), screen_name)

    try:
        while True:
            current_time = datetime.now().timestamp()
            elapsed_time = current_time - start_time

            # Отправляем предупреждения только во время периода подключения
            if not match_started:
                for warning_time in config.WARNING_TIMES:
                    time_left = config.TOTAL_WAIT_TIME - elapsed_time
                    if time_left <= warning_time and warning_time not in warned_times:
                        minutes_left = int(warning_time / 60)
                        await notify_time_warning(player_ids, minutes_left)
                        warned_times.add(warning_time)
                        match_logger.info(f"Отправлено предупреждение: {minutes_left} минут до отключения")

                if elapsed_time >= config.TOTAL_WAIT_TIME:
                    match_logger.info("Превышено общее время ожидания")
                    await notify_timeout(player_ids)
                    break

            # Проверяем статус сервера
            status = await check_server_status(screen_name)
            if not status:
                match_logger.error("Не удалось получить статус сервера")
                await notify_players_error(player_ids)
                break

            match_logger.info(f"Статус сервера: {status}")

            if status['game_ended'] and match_started:
                match_logger.info("Матч завершен")
                await notify_match_end(player_ids, status['ct_score'], status['t_score'])
                break

            # Начинаем проверять пустой сервер только после истечения времени на подключение
            if elapsed_time > initial_connection_time:
                if status['active_players'] == 0:
                    empty_server_checks += 1
                    match_logger.warning(f"Сервер пуст. Проверка {empty_server_checks}/{config.MAX_EMPTY_CHECKS}")
                    if empty_server_checks >= config.MAX_EMPTY_CHECKS:
                        match_logger.info("Сервер пуст более установленного количества проверок")
                        await notify_server_empty(player_ids)
                        break
                else:
                    empty_server_checks = 0

            # Запускаем матч только когда подключились все игроки
            if not match_started and status['active_players'] >= len(player_ids):
                match_logger.info("Все игроки подключились, запускаем матч")
                match_started = await start_match(screen_name)
                if match_started:
                    await notify_match_start(player_ids)
                    initial_connection_time = 0  # После старта матча сразу начинаем проверять пустой сервер

            await asyncio.sleep(check_interval)

    except Exception as e:
        match_logger.error(f"Ошибка мониторинга: {e}", exc_info=True)
        await notify_players_error(player_ids)

    finally:
        for user_id in player_ids:
            search_manager.remove_player_from_match(str(user_id))

        await stop_server(screen_name)
        match_logger.info("Завершение мониторинга сервера")

def generate_random_password(length=8):
    """Генерирует случайный пароль"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def generate_status_message(search_id):
    """Генерирует сообщение о статусе поиска"""
    search_data = search_manager.active_searches.get(search_id)
    if search_data:
        count = len(search_data['players'])
        return (
            f"👥 Идёт подбор игроков:\n"
            f"👨‍👦 Найдено: {count} из {config.MIN_PLAYERS_FOR_START} ✅"
        )
    return "👥 Поиск не активен"

def search_keyboard():
    """Создает клавиатуру для поиска"""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="🔍 Поиск", callback_data="start_search")
    keyboard.button(text="❌ Отмена", callback_data="cancel_search")
    return keyboard.as_markup()

async def notify_match_start(player_ids):
    """Уведомляет игроков о начале матча"""
    message = "🎮 Матч начался! Удачной игры!"
    for user_id in player_ids:
        try:
            await bot.send_message(chat_id=user_id, text=message)
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления о начале матча игроку {user_id}: {e}")

async def notify_match_end(player_ids, ct_score, t_score):
    """Уведомляет игроков о завершении матча"""
    message = (
        f"🏆 Игра завершена!\n\n"
        f"Нажмите /search, чтобы начать новый поиск!"
    )
    for user_id in player_ids:
        try:
            await bot.send_message(chat_id=user_id, text=message)
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления о завершении матча игроку {user_id}: {e}")

async def notify_time_warning(player_ids, minutes_left):
    """Отправляет предупреждение о времени до отключения сервера"""
    message = (
        f"⚠️ Внимание! До отключения сервера осталось {minutes_left} минут!\n"
        f"Пожалуйста, подключитесь к серверу, иначе он будет остановлен."
    )
    for user_id in player_ids:
        try:
            await bot.send_message(chat_id=user_id, text=message)
        except Exception as e:
            logger.error(f"Ошибка отправки предупреждения игроку {user_id}: {e}")

async def notify_timeout(player_ids):
    """Уведомляет игроков о превышении времени ожидания"""
    message = (
        "⏰ Время ожидания истекло!\n"
        "Недостаточно игроков подключилось к серверу.\n\n"
        "Нажмите /search, чтобы начать новый поиск."
    )
    for user_id in player_ids:
        try:
            await bot.send_message(chat_id=user_id, text=message)
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления о таймауте игроку {user_id}: {e}")

async def notify_server_empty(player_ids):
    """Уведомляет игроков о пустом сервере"""
    message = (
        "Матч завершен!!\n"
        "Нажмите /search, чтобы начать новый поиск."
    )
    for user_id in player_ids:
        try:
            await bot.send_message(chat_id=user_id, text=message)
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления о пустом сервере игроку {user_id}: {e}")
def confirmation_keyboard():
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="✅ Подтвердить участие", callback_data="confirm_ready")
    return keyboard.as_markup()
async def notify_players_error(player_ids):
    """Уведомляет игроков об ошибке"""
    message = (
        "⚠️ Произошла ошибка на сервере!\n"
        "Сервер был остановлен.\n\n"
        "Нажмите /search, чтобы начать новый поиск игры."
    )
    for user_id in player_ids:
        try:
            await bot.send_message(chat_id=user_id, text=message)
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления об ошибке игроку {user_id}: {e}")

@dp.message(Command("search"))
async def handle_search(message: types.Message):
    user_id = str(message.from_user.id)
    current_time = time.time()

    # Проверяем кулдаун команды /search
    if user_id in command_cooldowns and command_cooldowns[user_id] > current_time:
        remaining_time = int(command_cooldowns[user_id] - current_time)
        await message.answer(f"⏳ Подождите {remaining_time} секунд перед повторным поиском.")
        return

    # Устанавливаем кулдаун на 30 секунд
    command_cooldowns[user_id] = current_time + 30

    # Проверяем кулдаун матча
    if user_id in user_cooldown and user_cooldown[user_id] > current_time:
        remaining_time = int(user_cooldown[user_id] - current_time)
        minutes, seconds = divmod(remaining_time, 60)
        await message.answer(
            f"⏳ Вы недавно завершили матч. Подождите {minutes} минут {seconds} секунд, чтобы начать новый поиск!"
        )
        return

    player_data = {"user_id": user_id, "name": message.from_user.first_name}

    # Ищем активный поиск
    active_search_id = None
    for search_id, search_data in search_manager.active_searches.items():
        if len(search_data["players"]) < config.MAX_PLAYERS:
            active_search_id = search_id
            break

    if active_search_id:
        if search_manager.add_player(active_search_id, player_data):
            search_status = generate_status_message(active_search_id)
            msg = await message.answer(
                search_status,
                reply_markup=search_keyboard()
            )
            search_manager.active_searches[active_search_id]["messages"][user_id] = msg
            await update_all_players(active_search_id)
        else:
            await message.answer("⚠️ Не удалось присоединиться к поиску.")
        return

    # Создаем новый поиск
    new_search_id = search_manager.create_new_search()
    if search_manager.add_player(new_search_id, player_data):
        search_status = generate_status_message(new_search_id)
        msg = await message.answer(
            search_status,
            reply_markup=search_keyboard()
        )
        search_manager.active_searches[new_search_id]["messages"][user_id] = msg
    else:
        await message.answer("⚠️ Ошибка создания поиска.")
@dp.callback_query(lambda call: call.data == "start_search")
async def handle_start_search(call: types.CallbackQuery):
    user_id = str(call.from_user.id)
    search_id = search_manager.player_searches.get(user_id)

    if not search_id:
        await call.answer("❌ Поиск не найден.")
        return

    search_data = search_manager.active_searches.get(search_id)
    if not search_data:
        await call.answer("❌ Поиск не найден.")
        return

    if search_data.get('server_creating', False):
        await call.answer("⚠️ Сервер уже создается!")
        return

    if len(search_data['players']) < config.MIN_PLAYERS_FOR_START:
        await call.answer("⚠️ Недостаточно игроков для старта!")
        return

    await finish_search(search_id)
    await call.answer("✅ Запускаем матч!")
    
@dp.callback_query(lambda call: call.data == "cancel_search")
async def handle_cancel_search(call: types.CallbackQuery):
    try:
        user_id = str(call.from_user.id)
        search_manager.remove_player(user_id)

        try:
            await bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="❌ Поиск отменен."
            )
        except Exception as e:
            if "message is not modified" not in str(e):
                await call.message.answer("❌ Поиск отменен.")

        await call.answer()

    except Exception as e:
        logger.error(f"Ошибка при отмене поиска для игрока {user_id}: {e}")
        try:
            await call.message.answer("❌ Поиск отменен.")
        except:
            pass
async def cancel_if_not_confirmed(search_id):
    """Отменяет поиск, если не все игроки подтвердили участие в течение заданного времени."""
    await asyncio.sleep(60)  # Ждем 60 секунд

    search_data = search_manager.active_searches.get(search_id)
    if not search_data:
        return

    # Проверяем, подтвердили ли все игроки участие
    if len(search_data.get("confirmed_players", set())) < len(search_data['players']):
        for player in search_data['players']:
            user_id = str(player['user_id'])
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text="❌ Кто-то не подтвердил участие. Поиск отменён."
                )
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления игроку {user_id}: {e}")

        # Удаляем поиск из активных
        search_manager.active_searches.pop(search_id, None)
async def update_all_players(search_id):
    """Обновляет сообщения всех игроков в поиске и проверяет готовность"""
    search_data = search_manager.active_searches.get(search_id)
    if not search_data:
        return

    # Генерируем новый статус сообщения
    new_status_message = generate_status_message(search_id)

    # Создаем копию сообщений, чтобы избежать изменений во время итерации
    messages_copy = dict(search_data['messages'])

    # Обновляем статус поиска для всех игроков
    for user_id, msg in messages_copy.items():
        try:
            # Проверяем, что игрок всё ещё в поиске
            if user_id not in [player['user_id'] for player in search_data['players']]:
                # Если игрок покинул поиск, удаляем его сообщение
                if msg:
                    try:
                        await bot.delete_message(chat_id=msg.chat.id, message_id=msg.message_id)
                    except Exception as e:
                        logger.error(f"Ошибка удаления сообщения игрока {user_id}: {e}")
                # Удаляем запись о сообщении из данных поиска
                search_data['messages'].pop(user_id, None)
                continue

            # Обновляем сообщение, если текст изменился
            if msg and msg.text != new_status_message:
                try:
                    await bot.edit_message_text(
                        chat_id=msg.chat.id,
                        message_id=msg.message_id,
                        text=new_status_message,
                        reply_markup=search_keyboard()
                    )
                except Exception as e:
                    if "message is not modified" not in str(e):
                        logger.error(f"Ошибка API Telegram для игрока {user_id}: {e}")
        except Exception as e:
            logger.error(f"Ошибка обновления сообщения игрока {user_id}: {e}")
            # Если произошла ошибка, удаляем запись о сообщении из данных поиска
            if search_id in search_manager.active_searches:
                search_data['messages'].pop(user_id, None)

    # Если достигнуто максимальное количество игроков, отправляем подтверждение
    if len(search_data["players"]) >= config.MAX_PLAYERS:
        search_data["confirmed_players"] = set()  # Инициализируем множество подтвержденных игроков
        for player in search_data["players"]:
            user_id = player["user_id"]
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text="🎮 Все игроки в сборе! Подтвердите участие.",
                    reply_markup=confirmation_keyboard()
                )
            except Exception as e:
                logger.error(f"Ошибка отправки кнопки подтверждения игроку {user_id}: {e}")

        # Запускаем таймер отмены, если не все подтвердят участие
        asyncio.create_task(cancel_if_not_confirmed(search_id))

    # Если достигнуто минимальное количество игроков, завершаем поиск
    if len(search_data['players']) >= config.MIN_PLAYERS_FOR_START:
        await finish_search(search_id)

@dp.callback_query(lambda call: call.data == "confirm_ready")
async def handle_confirm_ready(call: types.CallbackQuery):
    """Обработчик подтверждения участия в матче"""
    user_id = str(call.from_user.id)
    search_id = search_manager.player_searches.get(user_id)

    if not search_id:
        await call.answer("❌ Ошибка: поиск не найден.")
        return

    search_data = search_manager.active_searches.get(search_id)
    if not search_data:
        await call.answer("❌ Ошибка: поиск не найден.")
        return

    # Добавляем игрока в список подтвержденных
    if user_id not in search_data["confirmed_players"]:
        search_data["confirmed_players"].add(user_id)

    confirmed_count = len(search_data["confirmed_players"])
    total_count = len(search_data["players"])

    # Обновляем статус для всех игроков в поиске
    updated_message = f"✅ Подтвердили участие: {confirmed_count}/{total_count}\n\nЖдём остальных..."

    for player in search_data["players"]:
        player_id = str(player["user_id"])
        try:
            await bot.edit_message_text(
                chat_id=player_id,
                message_id=search_data["messages"][player_id].message_id,
                text=updated_message,
                reply_markup=confirmation_keyboard()
            )
        except Exception as e:
            if "message is not modified" not in str(e):
                logger.error(f"Ошибка обновления сообщения для {player_id}: {e}")

    # Если все подтвердили, запускаем матч
    if confirmed_count >= total_count:
        await finish_search(search_id)
    else:
        await call.answer("✅ Подтверждено! Ждём остальных.")
async def finish_search(search_id):
    """Завершает поиск и запускает сервер"""
    search_data = search_manager.active_searches.get(search_id)
    if not search_data or len(search_data['players']) < config.MIN_PLAYERS_FOR_START:
        logger.error(f"Поиск {search_id} не может быть завершен: недостаточно игроков")
        return

    # Проверяем, что все игроки подтвердили участие
    if len(search_data.get("confirmed_players", set())) < len(search_data['players']):
        logger.error(f"Поиск {search_id} не может быть завершен: не все игроки подтвердили участие")
        for user_id, msg in search_data['messages'].items():
            try:
                await bot.send_message(
                    msg.chat.id,
                    "⚠️ Ждите когда все игроки подтвердят участие!."
                )
            except Exception as e:
                logger.error(f"Ошибка отправки сообщения об ошибке игроку {user_id}: {e}")
        return

    # Добавляем блокировку для предотвращения повторного запуска
    if search_data.get('server_creating', False):
        logger.warning(f"Сервер для поиска {search_id} уже создается")
        return

    search_data['server_creating'] = True

    try:
        messages_copy = dict(search_data['messages'])
        players_copy = list(search_data['players'])

        # Получаем ники игроков из базы данных
        player_ids = [int(player['user_id']) for player in players_copy]
        player_names = await get_player_names_from_db(player_ids)

        selected_map = random.choice(config.MAPS)
        server_password = generate_random_password()

        server_info = await start_server(selected_map, server_password)
        if not server_info:
            for user_id, msg in messages_copy.items():
                try:
                    await bot.send_message(
                        msg.chat.id,
                        "⚠️ Ошибка создания сервера. Попробуйте позже."
                    )
                except Exception as e:
                    logger.error(f"Ошибка отправки сообщения об ошибке игроку {user_id}: {e}")
            return

        screen_name, port = server_info

        random.shuffle(players_copy)
        ct_players = [player_names[p['user_id']] for i, p in enumerate(players_copy) if i % 2 == 0]
        t_players = [player_names[p['user_id']] for i, p in enumerate(players_copy) if i % 2 != 0]

        server_message = (
            f"🎮 Сервер создан!\n\n"
            f"🔵 Counter-Terrorist:\n{chr(10).join(ct_players)}\n\n"
            f"🔴 Terrorist:\n{chr(10).join(t_players)}\n\n"
            f"🗺 Карта: {selected_map}\n\n"
            f"🔐 Пароль: {server_password}\n"
            f"🌐 IP: {config.SERVER_IP}:{port}\n\n"
            f"📝 Команда для консоли:\n"
            f"connect {config.SERVER_IP}:{port}; password {server_password}"
        )

        for user_id, msg in messages_copy.items():
            try:
                await bot.send_message(msg.chat.id, server_message)
            except Exception as e:
                logger.error(f"Ошибка отправки сообщения игроку {user_id}: {e}")

        # Запускаем мониторинг сервера
        asyncio.create_task(monitor_server(screen_name, player_ids))

        # Очищаем поиск после создания сервера
        if search_id in search_manager.active_searches:
            for player in players_copy:
                search_manager.player_searches.pop(str(player['user_id']), None)
            search_manager.active_searches.pop(search_id, None)

        # Добавляем блокировку на 5 минут для всех игроков
        current_time = time.time()
        for player in players_copy:
            user_cooldown[str(player['user_id'])] = current_time + 300  # 300 секунд = 5 минут

    except Exception as e:
        logger.error(f"Ошибка при завершении поиска {search_id}: {e}")
        search_data['server_creating'] = False

async def get_player_names_from_db(player_ids):
    """Получает ники игроков из базы данных"""
    player_names = {}
    try:
        # Предполагаем, что у вас есть объект cursor для работы с базой данных
        cursor.execute(
            "SELECT user_id, user_name FROM users WHERE user_id IN ({})".format(','.join('?' for _ in player_ids)),
            player_ids)
        rows = cursor.fetchall()
        for row in rows:
            player_names[str(row[0])] = row[1]
    except Exception as e:
        logger.error(f"Ошибка при получении ников игроков из базы данных: {e}")
    return player_names


async def main():
    """Основная функция запуска бота"""
    logging.basicConfig(
        level=logging.INFO,
        format=config.LOG_FORMAT
    )
    logger = logging.getLogger(__name__)
    
    # Создаем папку для логов если её нет
    if not os.path.exists(config.LOG_DIRECTORY):
        os.makedirs(config.LOG_DIRECTORY)
    
    # Регистрируем все обработчики
    dp.include_router(router)
    
    logger.info("Бот запущен")
    last_cleanup = datetime.now().timestamp()

    while True:
        try:
            current_time = datetime.now().timestamp()
            if current_time - last_cleanup > 300:
                await search_manager.cleanup_inactive_matches()
                last_cleanup = current_time

            await dp.start_polling(bot)

        except Exception as e:
            logger.error(f"Критическая ошибка в работе бота: {e}", exc_info=True)
            await asyncio.sleep(5)

ssh_manager = SSHManager() 
if __name__ == "__main__":
    asyncio.run(main())