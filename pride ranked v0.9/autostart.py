import os
import telebot
import paramiko
import re
import time
import random
import string
import threading
from telebot import types
from datetime import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
import logging
import random
import string
import uuid
import config
from collections import defaultdict
from config import TELEGRAM_TOKEN, SSH_PORT, SSH_PASSWORD, ADMIN_IDS, SSH_USER, ADMIN_PREM, SSH_HOST, SERVER_IP, blacklist, LOG_DIRECTORY, SFTP_DIRECTORY, SFTP_PORT, SFTP_HOST, SFTP_USERNAME, SFTP_PASSWORD, ADMIN_IDS2
# 袧邪褋褌褉芯泄泻邪 谢芯谐懈褉芯胁邪薪懈褟
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# 袠薪懈褑懈邪谢懈蟹邪褑懈褟 斜邪蟹褘 写邪薪薪褘褏
conn = sqlite3.connect('users.db', check_same_thread=False)
cursor = conn.cursor()

# 小芯蟹写邪薪懈械 芯褋薪芯胁薪褘褏 褌邪斜谢懈褑
cursor.execute(''' 
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
    elo INTEGER DEFAULT 1000,  -- 袛芯斜邪胁谢械薪邪 蟹邪锌褟褌邪褟 锌械褉械写 elo
    ban_end_time DATETIME
);
''')
conn.commit()

cursor.execute('''
CREATE TABLE IF NOT EXISTS friends (
    user_id TEXT,
    friend_id TEXT,
    added_date TEXT,
    PRIMARY KEY (user_id, friend_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (friend_id) REFERENCES users(user_id)
);
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS bans (
    user_id TEXT PRIMARY KEY,
    ban_reason TEXT,
    ban_date TEXT,
    unban_date TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS premium_transactions (
    transaction_id TEXT PRIMARY KEY,
    user_id TEXT,
    amount REAL,
    duration TEXT,
    purchase_date TEXT,
    expiry_date TEXT,
    payment_method TEXT,
    status TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY,
    telegram_id INTEGER UNIQUE,
    nickname TEXT UNIQUE,
    flag TEXT,
    banned_until DATETIME,
    matches_played INTEGER DEFAULT 0
);
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS active_matches (
    match_id INTEGER PRIMARY KEY,
    start_time DATETIME,
    map TEXT,
    password TEXT,
    port INTEGER,
    screen_name TEXT,
    status TEXT
);
''')



# 袚谢芯斜邪谢褜薪褘械 锌械褉械屑械薪薪褘械 写谢褟 懈谐褉芯胁芯泄 褋懈褋褌械屑褘
global search_players
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
search_cooldown = {}
COOLDOWN_TIME = 300
def generate_random_id():
    return ''.join(random.choices(string.digits, k=9))
def create_main_menu(premium=False):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    profile_button = types.KeyboardButton("馃憫 袩褉芯褎懈谢褜")
    friends_button = types.KeyboardButton("馃懃 袛褉褍蟹褜褟")
    stats_button = types.KeyboardButton("馃搳 小褌邪褌懈褋褌懈泻邪")
    search_button = types.KeyboardButton("/search")
    add_friend_button = types.KeyboardButton("鈿欙笍 袛芯斜邪胁懈褌褜 写褉褍谐邪")
    report_button = types.KeyboardButton("馃摑袞邪谢芯斜邪 薪邪 懈谐褉芯泻邪")
    premium_button = types.KeyboardButton("馃挸 袩褉械屑懈褍屑" if not premium else "猸� 袩褉械屑懈褍屑 屑械薪褞")
    review_button = types.InlineKeyboardButton("馃摑 袨褌锌褉邪胁懈褌褜 芯褌蟹褘胁")

    markup.add(profile_button, friends_button)
    markup.add(stats_button, search_button)
    markup.add(add_friend_button, premium_button)
    markup.add(report_button, review_button)
    return markup


@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    user_ids.add(user_id)  # 袛芯斜邪胁谢械薪懈械 锌芯谢褜蟹芯胁邪褌械谢褟 胁 屑薪芯卸械褋褌胁芯

    try:
        user_id_str = str(message.from_user.id)  # 袩褉械芯斜褉邪蟹褍械屑 user_id 胁 褋褌褉芯泻褍
        cursor.execute("SELECT premium FROM users WHERE user_id = ?", (user_id_str,))
        user = cursor.fetchone()

        # 小芯蟹写邪械屑 泻谢邪胁懈邪褌褍褉褍 褋 泻薪芯锌泻芯泄 "携 薪芯胁懈褔芯泻!"
        markup = types.InlineKeyboardMarkup()
        btn_newbie = types.InlineKeyboardButton("携 薪芯胁懈褔芯泻!", callback_data="newbie")
        markup.add(btn_newbie)

        if not user:
            # 袩褉懈胁褟蟹泻邪 褎芯褌芯 泻 褋芯芯斜褖械薪懈褞
            with open('start.png', 'rb') as photo:  # 校泻邪卸懈褌械 锌褍褌褜 泻 胁邪褕械屑褍 懈蟹芯斜褉邪卸械薪懈褞
                bot.send_photo(
                    message.chat.id,
                    photo,
                    caption="袛芯斜褉芯 锌芯卸邪谢芯胁邪褌褜 胁 斜械褌邪-褌械褋褌! 馃幃\n\n"
                            "袣芯屑邪薪写邪 CMTV 写芯谢谐芯 懈 褍褋械褉写薪芯 褉邪斜芯褌邪谢邪 薪邪写 褋芯蟹写邪薪懈械屑 褝褌芯谐芯 懈薪褋褌褉褍屑械薪褌邪, 褔褌芯斜褘 褉邪褋泻褉褘褌褜 胁械褋褜 锌芯褌械薪褑懈邪谢 Faceit. 袦褘 褋褌褉械屑懈谢懈褋褜 褍褔械褋褌褜 胁褋褢, 褔褌芯 胁邪卸薪芯 写谢褟 懈谐褉芯泻芯胁, 褔褌芯斜褘 锌褉芯褑械褋褋 懈谐褉褘 褋褌邪谢 屑邪泻褋懈屑邪谢褜薪芯 褍写芯斜薪褘屑 懈 泻芯屑褎芯褉褌薪褘屑. 孝械锌械褉褜 胁褘 屑芯卸械褌械 褋褌邪褌褜 褔邪褋褌褜褞 斜械褌邪-褌械褋褌邪 懈 锌芯屑芯褔褜 薪邪屑 褍谢褍褔褕懈褌褜 褝褌芯褌 懈薪褋褌褉褍屑械薪褌!\n\n"
                            "馃敡 **协褌芯褌 懈薪褋褌褉褍屑械薪褌 锌芯屑芯卸械褌 胁邪屑 褉邪褋泻褉褘褌褜 胁械褋褜 褋胁芯泄 锌芯褌械薪褑懈邪谢:**\n"
                            "- 馃搳 校谢褍褔褕械薪薪褘泄 邪薪邪谢懈蟹 胁邪褕械泄 褋褌邪褌懈褋褌懈泻懈.\n"
                            "- 馃幆 袧芯胁芯械 懈 胁 褉邪蟹褘 谢褍褔褕械械 懈谐褉芯胁芯械 屑械薪褞.\n"
                            "- 鈿� 袛芯锌芯谢薪懈褌械谢褜薪褘械 褎褍薪泻褑懈懈 写谢褟 泻芯屑褎芯褉褌薪芯泄 懈谐褉褘.\n\n"
                            "馃挰 **袣邪泻 薪邪褔邪褌褜?**\n"
                            "1锔忊儯 袟邪锌褍褋褌懈褌械 Faceit ClientMod.\n"
                            "2锔忊儯 袟邪褉械谐懈褋褌褉懈褉褍泄褌械褋褜 褋 锌芯屑芯褖褜褞 泻芯屑邪薪写褘 /register.\n"
                            "3锔忊儯 袧邪褋谢邪卸写邪泄褌械褋褜, 懈 锌芯斜械卸写邪泄褌械!!\n\n"
                            "鈿狅笍 **袙邪卸薪芯:** 协褌芯 斜械褌邪-胁械褉褋懈褟, 锌芯褝褌芯屑褍 胁芯蟹屑芯卸薪褘 斜邪谐懈. 袝褋谢懈 胁褘 蟹邪屑械褌懈褌械 锌褉芯斜谢械屑褍, 芯褌锌褉邪胁褜褌械 芯褌蟹褘胁 褋 锌芯屑芯褖褜褞 泻薪芯锌泻懈 袨褌锌褉邪胁懈褌褜 芯褌蟹褘胁 胁 屑械薪褞. 袙邪褕懈 芯褌蟹褘胁褘 锌芯屑芯谐褍褌 薪邪屑 褋写械谢邪褌褜 懈薪褋褌褉褍屑械薪褌 谢褍褔褕械!\n\n"
                            "馃専 **袧邪褔薪懈褌械 褋械泄褔邪褋 懈 锌芯褔褍胁褋褌胁褍泄褌械 褉邪蟹薪懈褑褍!**",
                    reply_markup=markup,
                    parse_mode="Markdown"
                )
        else:
            # 袩褉芯胁械褉泻邪 薪邪 褋褌邪褌褍褋 锌褉械屑懈褍屑-邪泻泻邪褍薪褌邪
            premium_status = user[0].lower() == '写邪'  # 袩芯薪懈卸邪械屑 褉械谐懈褋褌褉 写谢褟 褋褌邪斜懈谢褜薪芯褋褌懈
            markup = create_main_menu(premium=premium_status)  # 小芯蟹写邪薪懈械 屑械薪褞 胁 蟹邪胁懈褋懈屑芯褋褌懈 芯褌 锌褉械屑懈褍屑邪
            bot.send_message(
                message.chat.id,
                "馃憫 袛芯斜褉芯 锌芯卸邪谢芯胁邪褌褜 胁 薪邪褕 斜械褌邪 褌械褋褌! 鉂わ笍",
                reply_markup=markup
            )

    except Exception as e:
        handle_error(e, message)
@bot.callback_query_handler(func=lambda call: call.data == "newbie")
def handle_newbie(call):
    try:
        bot.send_message(
            call.message.chat.id,
            "鉂曪笍<b>Faceit ClientMod</b>鉂曪笍\n\n"
            "<b>效褌芯 褌邪泻芯械 Faceit?</b>\n"
            "FACEIT 鈥� 褝褌芯 锌谢邪褌褎芯褉屑邪, 芯褉懈械薪褌懈褉芯胁邪薪薪邪褟 薪邪 褉邪蟹胁懈褌懈械 褋芯芯斜褖械褋褌胁 懈 锌褉械写芯褋褌邪胁谢械薪懈械 胁褘褋芯泻芯褍褉芯胁薪械胁褘褏 芯薪谢邪泄薪-褋芯褉械胁薪芯胁邪薪懈泄 写谢褟 屑薪芯卸械褋褌胁邪 PvP-懈谐褉. 袩芯写薪懈屑邪泄褌械褋褜 锌芯 褉邪薪谐邪屑 懈 锌芯泻邪卸懈褌械 褋胁芯泄 褍褉芯胁械薪褜 懈谐褉褘.\n\n"
            "<b>袣邪泻 薪邪褔邪褌褜 懈谐褉邪褌褜 胁 Faceit ClientMod?</b>\n"
            "1锔忊儯 鈥� 袟邪锌褍褋褌懈褌械 Faceit ClientMod\n"
            "2锔忊儯 鈥� 袟邪褉械谐懈褋褌褉懈褉褍泄褌械褋褜 褋 锌芯屑芯褖褜褞 泻芯屑邪薪写褘: /register\n"
            "3锔忊儯 鈥� 袧邪褋谢邪卸写邪泄褌械褋褜 懈 锌芯斜械卸写邪泄褌械 胁 屑邪褌褔邪褏\n\n"
            "<b>袩芯屑芯褖褜 锌芯 懈褋锌芯谢褜蟹芯胁邪薪懈褞 泻芯屑邪薪写:</b>\n\n"
            "- <b>Register</b> 鈥�> 袪械谐懈褋褌褉邪褑懈褟 胁邪褕械谐芯 Faceit 锌褉芯褎懈谢褟. 袧械芯斜褏芯写懈屑芯 胁胁械褋褌懈 胁邪褕 薪懈泻薪械泄屑 懈 褋褌褉邪薪褍.\n"
            "- <b>Profile</b> 鈥�> 袙邪褕 懈谐褉芯胁芯泄 锌褉芯褎懈谢褜, 谐写械 褍泻邪蟹邪薪褘 胁邪褕懈:\n"
            "  - 袧懈泻薪械泄屑\n"
            "  - 小褌褉邪薪邪\n"
            "  - 袣芯谢懈褔械褋褌胁芯 褋屑械褉褌械泄/褍斜懈泄褋褌胁\n"
            "  - 袣芯谢懈褔械褋褌胁芯 褋褘谐褉邪薪薪褘褏 屑邪褌褔械泄\n"
            "  - 袙懈薪褉械泄褌 薪邪 褉邪蟹薪褘褏 泻邪褉褌邪褏.\n"
            "- <b>Friends</b> 鈥�> 袙邪褕懈 写褉褍蟹褜褟, 写芯斜邪胁谢械薪薪褘械 胁邪屑懈 胁 Faceit 褉械卸懈屑械 写谢褟 褋芯胁屑械褋褌薪芯泄 懈谐褉褘 胁 屑邪褌褔邪褏.\n"
            "- <b>Premium</b> 鈥�> 袩褉械屑懈褍屑 锌芯写锌懈褋泻邪 Faceit, 泻芯褌芯褉邪褟 写邪褢褌 胁芯蟹屑芯卸薪芯褋褌褜 蟹邪斜谢芯泻懈褉芯胁邪褌褜 1 泻邪褉褌褍 锌械褉械写 锌芯懈褋泻芯屑 屑邪褌褔邪. "
            "袛谢褟 斜芯谢械械 锌芯写褉芯斜薪芯谐芯 芯蟹薪邪泻芯屑谢械薪懈褟: <a href='https://t.me/clanwarsarchive/4245'>薪邪卸邪褌褜 蟹写械褋褜</a>.\n"
            "- <b>袨褌蟹褘胁</b> 鈥�> 袩芯蟹胁芯谢褟械褌 芯褋褌邪胁懈褌褜 褋胁芯懈 胁锌械褔邪褌谢械薪懈褟 芯 Faceit 褉械卸懈屑械: 泻邪泻 锌芯谢芯卸懈褌械谢褜薪褘械, 褌邪泻 懈 芯褌褉懈褑邪褌械谢褜薪褘械.\n"
            "- <b>袞邪谢芯斜邪</b> 鈥�> 袩芯蟹胁芯谢褟械褌 锌芯卸邪谢芯胁邪褌褜褋褟 薪邪 芯锌褉械写械谢褢薪薪芯谐芯 懈谐褉芯泻邪 懈谢懈 褋褘谐褉邪薪薪褘泄 胁邪屑懈 屑邪褌褔 胁 褋谢褍褔邪械 薪械锌芯谢邪写芯泻.\n"
            "- <b>Search</b> 鈥�> 袟邪锌褍褋泻邪械褌 锌芯懈褋泻 屑邪褌褔邪 Faceit 褉械卸懈屑邪.\n"
            "- <b>袙褋械 懈谐褉芯泻懈</b> 鈥�> 袩芯泻邪蟹褘胁邪械褌 褋锌懈褋芯泻 胁褋械褏 蟹邪褉械谐懈褋褌褉懈褉芯胁邪薪薪褘褏 懈谐褉芯泻芯胁 Faceit 褉械卸懈屑邪.\n\n"
            "馃専 袧邪褔薪懈褌械 懈谐褉邪褌褜 褍卸械 褋械泄褔邪褋 懈 褉邪褋泻褉芯泄褌械 褋胁芯泄 锌芯褌械薪褑懈邪谢 薪邪 Faceit ClientMod!",
            parse_mode="HTML"
        )
    except Exception as e:
        handle_error(e, call.message)


def generate_referral_code():
    return str(uuid.uuid4().hex[:8])


@bot.message_handler(commands=['register'])
def register(message):
    try:
        user_id = str(message.from_user.id)

        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        if cursor.fetchone():
            bot.send_message(message.chat.id, "鉂� 袙褘 褍卸械 蟹邪褉械谐懈褋褌褉懈褉芯胁邪薪褘!")
            return

        bot.send_message(
            message.chat.id,
            "袙胁械写懈褌械 胁邪褕 薪懈泻薪械泄屑 (写芯 10 褋懈屑胁芯谢芯胁), 懈褋锌芯谢褜蟹褍褟 褌芯谢褜泻芯 邪薪谐谢懈泄褋泻懈械 斜褍泻胁褘, 褑懈褎褉褘 懈 褋锌械褑. 褋懈屑胁芯谢褘:"
        )
        bot.register_next_step_handler(message, save_nickname, user_id)
    except Exception as e:
        handle_error(e, message)

def save_nickname(message, user_id):
    nickname = message.text.strip()
    if not re.match(r'^[a-zA-Z0-9!@#$%^&*]{1,10}$', nickname):
        bot.send_message(
            message.chat.id,
            "鉂� 袧懈泻薪械泄屑 写芯谢卸械薪 褋芯写械褉卸邪褌褜 褌芯谢褜泻芯 邪薪谐谢懈泄褋泻懈械 斜褍泻胁褘, 褑懈褎褉褘 懈谢懈 褋锌械褑. 褋懈屑胁芯谢褘 懈 斜褘褌褜 写谢懈薪芯泄 写芯 10 褋懈屑胁芯谢芯胁."
        )
        bot.register_next_step_handler(message, save_nickname, user_id)
        return

    cursor.execute("SELECT user_id FROM users WHERE user_name = ?", (nickname,))
    if cursor.fetchone():
        bot.send_message(message.chat.id, "鉂� 协褌芯褌 薪懈泻薪械泄屑 褍卸械 蟹邪薪褟褌. 袩芯卸邪谢褍泄褋褌邪, 胁褘斜械褉懈褌械 写褉褍谐芯泄.")
        bot.register_next_step_handler(message, save_nickname, user_id)
        return

    bot.send_message(message.chat.id, "馃實 袙胁械写懈褌械 胁邪褕褍 褋褌褉邪薪褍 胁 胁懈写械 褝屑芯写蟹懈 (薪邪锌褉懈屑械褉, 馃嚪馃嚭 写谢褟 袪芯褋褋懈懈):")
    bot.register_next_step_handler(message, save_country, user_id, nickname)

def save_country(message, user_id, user_name):
    country = message.text.strip()

    # 袪械谐褍谢褟褉薪芯械 胁褘褉邪卸械薪懈械 写谢褟 锌褉芯胁械褉泻懈 褝屑芯写蟹懈 褋褌褉邪薪
    if not re.match(r'^[馃嚘-馃嚳]{2}$', country):
        bot.send_message(
            message.chat.id,
            "鉂� 校泻邪卸懈褌械 褋褌褉邪薪褍 褌芯谢褜泻芯 褋 锌芯屑芯褖褜褞 褝屑芯写蟹懈 (薪邪锌褉懈屑械褉, 馃嚪馃嚭 写谢褟 袪芯褋褋懈懈). 袩芯锌褉芯斜褍泄褌械 褋薪芯胁邪:"
        )
        bot.register_next_step_handler(message, save_country, user_id, user_name)
        return

    registration_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    random_id = generate_random_id()
    referral_code = generate_referral_code()  # 袚械薪械褉邪褑懈褟 褉械褎械褉邪谢褜薪芯谐芯 泻芯写邪

    # 袙褋褌邪胁谢褟械屑 写邪薪薪褘械 胁 斜邪蟹褍 写邪薪薪褘褏
    cursor.execute("""
        INSERT INTO users 
        (user_id, random_id, user_name, registration_date, country, premium, 
        kills, deaths, match_count, adr, avg, wins, losses, hidden, referral_code)
        VALUES (?, ?, ?, ?, ?, ?, 0, 0, 0, 0.0, 0.0, 0, 0, 0, ?)
    """, (user_id, random_id, user_name, registration_date, country, '薪械褌', referral_code))
    conn.commit()

    bot.send_message(message.chat.id, f"馃帀 袩芯谢褜蟹芯胁邪褌械谢褜 {user_name} 蟹邪褉械谐懈褋褌褉懈褉芯胁邪薪 褍褋锌械褕薪芯!")
    markup = create_main_menu()
    bot.send_message(
        message.chat.id,
        "馃憫 袛芯斜褉芯 锌芯卸邪谢芯胁邪褌褜 胁 斜械褌邪 褌械褋褌! 袙褘斜械褉懈褌械 写械泄褋褌胁懈械 薪懈卸械.",
        reply_markup=markup
    )
def handle_error(e, message):
    logging.error(f"Error occurred: {str(e)}")
    bot.reply_to(message, "鉂� 袩褉芯懈蟹芯褕谢邪 芯褕懈斜泻邪. 袩芯卸邪谢褍泄褋褌邪, 锌芯锌褉芯斜褍泄褌械 械褖械 褉邪蟹.")


# 袧邪褋褌褉芯泄泻懈 锌褉械屑懈褍屑-锌芯写锌懈褋泻懈
PRICING = {
    "1 屑械褋褟褑": 149,
    "3 屑械褋褟褑邪": 399,
    "1 谐芯写": 1299
}

PAYMENT_DETAILS = {
    "袣邪褉褌邪 (OZON Bank)": "2204 3203 9586 7460",
    "袣褉懈锌褌芯胁邪谢褞褌邪 (TRC20)": "TWvSQvNe7erMeYo218sQDebdzQwqkjWVHo",
    "袣褉懈锌褌芯胁邪谢褞褌邪 (TON)": "EQDD8dqOzaj4zUK6ziJOo_G2lx6qf1TEktTRkFJ7T1c_fPQb",
    "挟Money": "4100118827695775"
}


@bot.message_handler(func=lambda message: message.text == "馃憫 袩褉芯褎懈谢褜")
def show_profile(message):
    try:
        user_id = str(message.from_user.id)
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()

        if user:
            premium_status = user[5] == '写邪'
            kills = user[6] or 0
            deaths = user[7] or 0
            matches = user[8] or 0
            adr = user[9] or 0.0
            avg_rating = user[10] or 0.0
            wins = user[11] or 0
            losses = user[12] or 0

            if deaths == 0:
                kd_ratio = kills  # 袝褋谢懈 褋屑械褉褌械泄 薪械褌, 褋褌邪胁懈屑 K/D 褉邪胁薪褘屑 泻芯谢懈褔械褋褌胁褍 泻懈谢谢芯胁
            else:
                kd_ratio = kills / deaths

            # 袟邪锌褉邪褕懈胁邪械屑 褉械褎械褉邪谢褜薪褘泄 泻芯写 懈 泻芯谢懈褔械褋褌胁芯 褉械褎械褉邪谢芯胁
            cursor.execute('SELECT referral_code, referral_count FROM users WHERE user_id = ?', (user_id,))
            referral_data = cursor.fetchone()
            if referral_data:
                random_id, referral_count = referral_data
            else:
                random_id, referral_count = "袧械 褍褋褌邪薪芯胁谢械薪", 0  # 袝褋谢懈 写邪薪薪褘褏 薪械褌, 锌芯泻邪蟹褘胁邪械屑, 褔褌芯 泻芯写 薪械 褍褋褌邪薪芯胁谢械薪

            profile_text = (
                f"馃幃 袩褉芯褎懈谢褜 懈谐褉芯泻邪: {user[2]}\n"
                f"馃啍 校薪懈泻邪谢褜薪褘泄 ID: {user[1]}\n"
                f"馃搮 袛邪褌邪 褉械谐懈褋褌褉邪褑懈懈: {user[3]}\n"
                f"馃實 袪械谐懈芯薪: {user[4]}\n\n"
                f"馃敆 袪械褎械褉邪谢褜薪褘泄 泻芯写: {random_id}\n"
                f"馃懃 袩褉懈谐谢邪褕械薪芯 写褉褍蟹械泄: {referral_count}\n"
            )

            if premium_status:
                profile_text += (
                    f"\n馃専 袩褉械屑懈褍屑-邪泻泻邪褍薪褌 邪泻褌懈胁懈褉芯胁邪薪!\n"
                    f"馃敟 袛芯锌芯谢薪懈褌械谢褜薪褘械 褎褍薪泻褑懈懈 写芯褋褌褍锌薪褘.\n"
                )

            bot.send_message(message.chat.id, profile_text)
        else:
            bot.send_message(message.chat.id, "鉂� 袙邪褕 锌褉芯褎懈谢褜 薪械 薪邪泄写械薪. 袩芯卸邪谢褍泄褋褌邪, 蟹邪褉械谐懈褋褌褉懈褉褍泄褌械褋褜 /register.")
    except Exception as e:
        handle_error(e, message)


@bot.message_handler(func=lambda message: message.text == "馃挸 袩褉械屑懈褍屑")
def start_handler(message):
    if user_data.get(message.chat.id, {}).get("in_progress"):
        bot.send_message(
            message.chat.id,
            "袙褘 褍卸械 芯褎芯褉屑谢褟械褌械 蟹邪泻邪蟹. 袟邪胁械褉褕懈褌械 褌械泻褍褖懈泄 锌褉芯褑械褋褋 懈谢懈 薪邪卸屑懈褌械 '袨褌屑械薪邪', 褔褌芯斜褘 薪邪褔邪褌褜 薪芯胁褘泄."
        )
        return

    user_data[message.chat.id] = {"in_progress": True}
    bot.send_message(
        message.chat.id,
        "袛芯斜褉芯 锌芯卸邪谢芯胁邪褌褜 胁 褉邪蟹写械谢 芯褎芯褉屑谢械薪懈褟 锌褉械屑懈褍屑-锌芯写锌懈褋泻懈!\n\n"
        "袙褘斜械褉懈褌械 褋褉芯泻 锌芯写锌懈褋泻懈, 懈 锌芯谢褍褔懈褌械 写芯褋褌褍锌 泻 褝泻褋泻谢褞蟹懈胁薪褘屑 褎褍薪泻褑懈褟屑.",
        reply_markup=duration_keyboard()
    )


# 袣谢邪胁懈邪褌褍褉邪 写谢褟 胁褘斜芯褉邪 褋褉芯泻邪 锌芯写锌懈褋泻懈
def duration_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    for duration, price in PRICING.items():
        keyboard.add(types.InlineKeyboardButton(text=f"{duration} - {price}鈧�", callback_data=f"duration:{duration}"))
    keyboard.add(types.InlineKeyboardButton(text="鉂� 袨褌屑械薪邪", callback_data="cancel"))
    return keyboard



def create_premium_menu():
    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    change_nickname_button = types.KeyboardButton("袠蟹屑械薪懈褌褜 薪懈泻薪械泄屑")
    change_id_button = types.KeyboardButton("袠蟹屑械薪懈褌褜 ID")
    hide_profile_button = types.KeyboardButton("小泻褉褘褌褜 锌褉芯褎懈谢褜")
    back_button = types.KeyboardButton("袙械褉薪褍褌褜褋褟 胁 谐谢邪胁薪芯械 屑械薪褞")

    markup.add(change_nickname_button, change_id_button, hide_profile_button, back_button)
    return markup


# 袣谢邪胁懈邪褌褍褉邪 写谢褟 胁褘斜芯褉邪 褋锌芯褋芯斜邪 芯锌谢邪褌褘
def payment_method_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    for method in PAYMENT_DETAILS.keys():
        keyboard.add(types.InlineKeyboardButton(text=f"{method}", callback_data=f"payment:{method}"))
    keyboard.add(types.InlineKeyboardButton(text="鉂� 袨褌屑械薪邪", callback_data="cancel"))
    return keyboard


# 袣谢邪胁懈邪褌褍褉邪 写谢褟 邪写屑懈薪懈褋褌褉邪褌芯褉邪 (锌芯写褌胁械褉卸写械薪懈械 懈谢懈 芯褌泻谢芯薪械薪懈械)
def admin_keyboard(user_id):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="鉁� 袩芯写褌胁械褉写懈褌褜", callback_data=f"confirm:{user_id}"))
    keyboard.add(types.InlineKeyboardButton(text="鉂� 袨褌泻谢芯薪懈褌褜", callback_data=f"reject:{user_id}"))
    return keyboard


# 袨斜褉邪斜芯褌泻邪 胁褘斜芯褉邪 褋褉芯泻邪 锌芯写锌懈褋泻懈
@bot.callback_query_handler(func=lambda call: call.data.startswith("duration:"))
def select_duration(call):
    duration = call.data.split(":")[1]
    user_data[call.message.chat.id]['duration'] = duration
    bot.edit_message_text(
        f"袙褘 胁褘斜褉邪谢懈 褋褉芯泻: {duration}. 孝械锌械褉褜 胁褘斜械褉懈褌械 褋锌芯褋芯斜 芯锌谢邪褌褘.",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=payment_method_keyboard()
    )


# 袨斜褉邪斜芯褌泻邪 胁褘斜芯褉邪 褋锌芯褋芯斜邪 芯锌谢邪褌褘
@bot.callback_query_handler(func=lambda call: call.data.startswith("payment:"))
def select_payment_method(call):
    method = call.data.split(":")[1]
    user_data[call.message.chat.id]['payment_method'] = method

    details = PAYMENT_DETAILS.get(method, "袠薪褎芯褉屑邪褑懈褟 薪械写芯褋褌褍锌薪邪.")
    duration = user_data[call.message.chat.id].get('duration', '薪械 褍泻邪蟹邪薪')

    # 小芯蟹写邪械屑 泻谢邪胁懈邪褌褍褉褍 褋 泻薪芯锌泻芯泄 "袨褌屑械薪邪"
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="鉂� 袨褌屑械薪邪", callback_data="cancel"))

    bot.edit_message_text(
        f"袙褘 胁褘斜褉邪谢懈 褋锌芯褋芯斜 芯锌谢邪褌褘: {method}.\n\n"
        f"小褉芯泻 锌芯写锌懈褋泻懈: {duration}\n"
        f"袪械泻胁懈蟹懈褌褘 写谢褟 芯锌谢邪褌褘:\n{details}\n\n"
        f"鈿狅笍 袨斜褉邪褌懈褌械 胁薪懈屑邪薪懈械: 泻芯屑懈褋褋懈褟 蟹邪 锌械褉械胁芯写 谢械卸懈褌 薪邪 胁邪褋.\n"
        f"袩芯褋谢械 芯锌谢邪褌褘 芯褌锌褉邪胁褜褌械 褋泻褉懈薪褕芯褌 写谢褟 锌芯写褌胁械褉卸写械薪懈褟.",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=keyboard
    )


# 袨斜褉邪斜芯褌泻邪 芯褌屑械薪褘 (褍薪懈胁械褉褋邪谢褜薪邪褟)
@bot.callback_query_handler(func=lambda call: call.data == "cancel")
def cancel_process(call):
    user_data[call.message.chat.id] = {"in_progress": False}
    bot.edit_message_text(
        "袩褉芯褑械褋褋 芯褎芯褉屑谢械薪懈褟 蟹邪泻邪蟹邪 芯褌屑械薪械薪. 袝褋谢懈 胁褘 褏芯褌懈褌械 薪邪褔邪褌褜 蟹邪薪芯胁芯, 懈褋锌芯谢褜蟹褍泄褌械 /start.",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id
    )


# 袨斜褉邪斜芯褌泻邪 褋泻褉懈薪褕芯褌芯胁
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    # 袩褉芯胁械褉褟械屑, 蟹邪褉械谐懈褋褌褉懈褉芯胁邪薪 谢懈 锌芯谢褜蟹芯胁邪褌械谢褜
    cursor.execute("SELECT user_name FROM users WHERE user_id = ?", (message.from_user.id,))
    player = cursor.fetchone()

    if not player:
        bot.send_message(message.chat.id, "袙褘 薪械 蟹邪褉械谐懈褋褌褉懈褉芯胁邪薪褘. 袩芯卸邪谢褍泄褋褌邪, 蟹邪褉械谐懈褋褌褉懈褉褍泄褌械褋褜 写谢褟 锌褉芯写芯谢卸械薪懈褟.")
        return

    # 袩褉芯胁械褉褟械屑, 械褋褌褜 谢懈 褍 锌芯谢褜蟹芯胁邪褌械谢褟 邪泻褌懈胁薪褘泄 蟹邪泻邪蟹
    if not user_data.get(message.chat.id, {}).get("in_progress"):
        bot.send_message(message.chat.id, "校 胁邪褋 薪械褌 邪泻褌懈胁薪芯谐芯 蟹邪泻邪蟹邪. 袠褋锌芯谢褜蟹褍泄褌械 /start, 褔褌芯斜褘 薪邪褔邪褌褜.")
        return

    duration = user_data[message.chat.id].get('duration', '薪械 褍泻邪蟹邪薪')
    payment_method = user_data[message.chat.id].get('payment_method', '薪械 褍泻邪蟹邪薪')

    # 袨褌锌褉邪胁谢褟械屑 邪写屑懈薪褍 褋泻褉懈薪褕芯褌
    bot.send_message(
        ADMIN_PREM,
        f"小泻褉懈薪褕芯褌 芯锌谢邪褌褘 芯褌 @{message.from_user.username}.\n"
        f"小褉芯泻 锌芯写锌懈褋泻懈: {duration}\n"
        f"小锌芯褋芯斜 芯锌谢邪褌褘: {payment_method}.",
        reply_markup=admin_keyboard(message.chat.id)
    )
    bot.forward_message(ADMIN_PREM, message.chat.id, message.message_id)
    bot.send_message(message.chat.id, "小泻褉懈薪褕芯褌 芯褌锌褉邪胁谢械薪 邪写屑懈薪懈褋褌褉邪褌芯褉褍. 袨卸懈写邪泄褌械 锌芯写褌胁械褉卸写械薪懈褟.")
    user_data[message.chat.id]["in_progress"] = False


# 袨斜褉邪斜芯褌泻邪 锌芯写褌胁械褉卸写械薪懈褟 邪写屑懈薪懈褋褌褉邪褌芯褉邪
@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm:"))
def confirm_payment(call):
    user_id = int(call.data.split(":")[1])

    try:
        cursor.execute("UPDATE users SET premium = '写邪' WHERE user_id = ?", (user_id,))
        conn.commit()
    except Exception as e:
        bot.send_message(call.message.chat.id, "袩褉芯懈蟹芯褕谢邪 芯褕懈斜泻邪 锌褉懈 芯斜薪芯胁谢械薪懈懈 斜邪蟹褘 写邪薪薪褘褏.")
        return

    bot.send_message(user_id, "袙邪褕 锌谢邪褌械卸 锌芯写褌胁械褉卸写械薪! 袩褉芯锌懈褕懈褌械 /start, 褔褌芯斜褘 芯斜薪芯胁懈褌褜 屑械薪褞. 小锌邪褋懈斜芯 蟹邪 锌芯泻褍锌泻褍 锌褉械屑懈褍屑-锌芯写锌懈褋泻懈!")
    bot.edit_message_text("袩谢邪褌械卸 褍褋锌械褕薪芯 锌芯写褌胁械褉卸写械薪!", chat_id=call.message.chat.id, message_id=call.message.message_id)


# 袨斜褉邪斜芯褌泻邪 芯褌泻谢芯薪械薪懈褟 邪写屑懈薪懈褋褌褉邪褌芯褉邪
@bot.callback_query_handler(func=lambda call: call.data.startswith("reject:"))
def reject_payment(call):
    user_id = int(call.data.split(":")[1])
    bot.send_message(user_id, "袙邪褕 锌谢邪褌械卸 芯褌泻谢芯薪械薪. 袩芯卸邪谢褍泄褋褌邪, 褋胁褟卸懈褌械褋褜 褋 邪写屑懈薪懈褋褌褉邪褌芯褉芯屑 写谢褟 褍褌芯褔薪械薪懈褟.")
    bot.edit_message_text("袩谢邪褌械卸 芯褌泻谢芯薪械薪. 小胁褟卸懈褌械褋褜 褋 邪写屑懈薪懈褋褌褉邪褌芯褉芯屑.", chat_id=call.message.chat.id, message_id=call.message.message_id)



@bot.message_handler(func=lambda message: message.text == "猸� 袩褉械屑懈褍屑 屑械薪褞")
def premium_menu_handler(message):
    try:
        user_id = str(message.from_user.id)
        cursor.execute("SELECT premium FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()

        if user and user[0] == '写邪':
            markup = create_premium_menu()
            bot.send_message(
                message.chat.id,
                "猸� 袛芯斜褉芯 锌芯卸邪谢芯胁邪褌褜 胁 锌褉械屑懈褍屑-屑械薪褞!",
                reply_markup=markup
            )
        else:
            bot.send_message(
                message.chat.id,
                "鉂� 袛谢褟 写芯褋褌褍锌邪 泻 锌褉械屑懈褍屑-屑械薪褞 薪械芯斜褏芯写懈屑邪 锌褉械屑懈褍屑-锌芯写锌懈褋泻邪."
            )
    except Exception as e:
        handle_error(e, message)

#袨斜褉邪斜芯褌褔懈泻懈 锌褉械屑 屑械薪褞 褋薪懈蟹褍
@bot.message_handler(func=lambda message: message.text == "袙械褉薪褍褌褜褋褟 胁 谐谢邪胁薪芯械 屑械薪褞")
def back_to_main_menu(message):
    # 袧邪锌褉褟屑褍褞 胁褘蟹褘胁邪械屑 褎褍薪泻褑懈褞 `start`, 褔褌芯斜褘 芯斜褉邪斜芯褌邪褌褜 胁芯蟹胁褉邪褖械薪懈械 胁 谐谢邪胁薪芯械 屑械薪褞
    start(message)

@bot.message_handler(func=lambda message: message.text == "袠蟹屑械薪懈褌褜 薪懈泻薪械泄屑")
def change_nickname(message):
        bot.send_message(message.chat.id, "袙胁械写懈褌械 薪芯胁褘泄 薪懈泻薪械泄屑:")

        # 小芯褏褉邪薪褟械屑 褋芯褋褌芯褟薪懈械, 褔褌芯斜褘 卸写邪褌褜 薪芯胁褘泄 薪懈泻薪械泄屑
        bot.register_next_step_handler(message, process_new_nickname)

    # 袨斜褉邪斜芯褌褔懈泻 写谢褟 锌芯谢褍褔械薪懈褟 薪芯胁芯谐芯 薪懈泻薪械泄屑邪 懈 芯斜薪芯胁谢械薪懈褟 胁 斜邪蟹械 写邪薪薪褘褏
def process_new_nickname(message):
        new_nickname = message.text.strip()

        # 袩褉芯胁械褉懈屑, 褔褌芯 薪芯胁褘泄 薪懈泻薪械泄屑 褍薪懈泻邪谢械薪
        cursor.execute("SELECT * FROM users WHERE user_name=?", (new_nickname,))
        existing_user = cursor.fetchone()

        if existing_user:
            bot.send_message(message.chat.id, "协褌芯褌 薪懈泻薪械泄屑 褍卸械 蟹邪薪褟褌. 袩芯卸邪谢褍泄褋褌邪, 胁褘斜械褉懈褌械 写褉褍谐芯泄.")
        else:
            # 袨斜薪芯胁谢褟械屑 薪懈泻薪械泄屑 胁 斜邪蟹械 写邪薪薪褘褏
            cursor.execute("UPDATE users SET user_name=? WHERE user_id=?", (new_nickname, message.chat.id))
            conn.commit()
            bot.send_message(message.chat.id, f"袧懈泻薪械泄屑 褍褋锌械褕薪芯 懈蟹屑械薪械薪 薪邪 {new_nickname}.")


@bot.message_handler(func=lambda message: message.text == "袠蟹屑械薪懈褌褜 ID")
def change_id(message):
    bot.send_message(message.chat.id, "袙胁械写懈褌械 薪芯胁褘泄 ID:")

    # 小芯褏褉邪薪褟械屑 褋芯褋褌芯褟薪懈械, 褔褌芯斜褘 卸写邪褌褜 薪芯胁褘泄 ID
    bot.register_next_step_handler(message, process_new_id)


# 袨斜褉邪斜芯褌褔懈泻 写谢褟 锌芯谢褍褔械薪懈褟 薪芯胁芯谐芯 ID 懈 芯斜薪芯胁谢械薪懈褟 胁 斜邪蟹械 写邪薪薪褘褏
def process_new_id(message):
    new_random_id = message.text.strip()

    # 小锌懈褋芯泻 蟹邪锌褉械褖褢薪薪褘褏 ID
    forbidden_ids = ["admin", "00000000"]

  # 袟邪屑械薪懈褌械 薪邪 褉械邪谢褜薪褘械 ID 邪写屑懈薪懈褋褌褉邪褌芯褉芯胁

    # 袩褉芯胁械褉泻邪, 褟胁谢褟械褌褋褟 谢懈 锌芯谢褜蟹芯胁邪褌械谢褜 邪写屑懈薪懈褋褌褉邪褌芯褉芯屑
    if new_random_id in forbidden_ids:
        if message.from_user.id not in ADMIN_IDS2:
            bot.send_message(message.chat.id, "协褌芯褌 ID 薪械写芯锌褍褋褌懈屑. 袩芯卸邪谢褍泄褋褌邪, 胁褘斜械褉懈褌械 写褉褍谐芯泄.")
            return
        else:
            bot.send_message(message.chat.id, f"袙褘 鈥� 邪写屑懈薪懈褋褌褉邪褌芯褉, 锌芯褝褌芯屑褍 屑芯卸械褌械 懈褋锌芯谢褜蟹芯胁邪褌褜 褝褌芯褌 ID.")

    # 袩褉芯胁械褉褟械屑, 褔褌芯 薪芯胁褘泄 random_id 褍薪懈泻邪谢械薪
    cursor.execute("SELECT * FROM users WHERE random_id=?", (new_random_id,))
    existing_user = cursor.fetchone()

    if existing_user:
        bot.send_message(message.chat.id, "协褌芯褌 ID 褍卸械 蟹邪薪褟褌. 袩芯卸邪谢褍泄褋褌邪, 胁褘斜械褉懈褌械 写褉褍谐芯泄.")
    else:
        # 袨斜薪芯胁谢褟械屑 ID 胁 斜邪蟹械 写邪薪薪褘褏
        cursor.execute("UPDATE users SET random_id=? WHERE user_id=?", (new_random_id, message.chat.id))
        conn.commit()
        bot.send_message(message.chat.id, f"ID 褍褋锌械褕薪芯 懈蟹屑械薪褢薪 薪邪 {new_random_id}.")


@bot.message_handler(func=lambda message: message.text == "馃摑 袨褌锌褉邪胁懈褌褜 芯褌蟹褘胁")
def ask_for_review(message):
    bot.send_message(message.chat.id, "袩芯卸邪谢褍泄褋褌邪, 薪邪锌懈褕懈褌械 胁邪褕 芯褌蟹褘胁, 褔褌芯斜褘 屑褘 屑芯谐谢懈 褍谢褍褔褕懈褌褜 懈薪褋褌褉褍屑械薪褌.")
    bot.register_next_step_handler(message, handle_review)

# 袨斜褉邪斜芯褌泻邪 褌械泻褋褌邪 芯褌蟹褘胁邪
def handle_review(message):
    try:
        user_id = str(message.from_user.id)
        cursor.execute("SELECT user_name FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()

        if not user:
            bot.send_message(message.chat.id, "袨褕懈斜泻邪: 袦褘 薪械 薪邪褕谢懈 胁邪褋 胁 斜邪蟹械 写邪薪薪褘褏. 袩芯卸邪谢褍泄褋褌邪, 蟹邪褉械谐懈褋褌褉懈褉褍泄褌械褋褜 懈 锌芯锌褉芯斜褍泄褌械 褋薪芯胁邪.")
            return

        user_name = user[0]  # 袠屑褟 锌芯谢褜蟹芯胁邪褌械谢褟 懈蟹 斜邪蟹褘 写邪薪薪褘褏
        review_text = message.text

        bot.send_message(
            ADMIN_PREM,
            f"袧芯胁褘泄 芯褌蟹褘胁 芯褌 懈谐褉芯泻邪 {user_name} ({user_id}):\n\n{review_text}"
        )

        # 袩芯写褌胁械褉卸写械薪懈械 写谢褟 锌芯谢褜蟹芯胁邪褌械谢褟
        bot.send_message(message.chat.id, "小锌邪褋懈斜芯 蟹邪 胁邪褕 芯褌蟹褘胁! 袦褘 芯斜褟蟹邪褌械谢褜薪芯 褍褔褌械屑 胁邪褕械 屑薪械薪懈械.")
    except Exception as e:
        print(f"Error: {e}")
        bot.send_message(message.chat.id, "袩褉芯懈蟹芯褕谢邪 芯褕懈斜泻邪. 袩芯卸邪谢褍泄褋褌邪, 锌芯锌褉芯斜褍泄褌械 褋薪芯胁邪.")


@bot.message_handler(commands=['take_premium'])
def take_premium(message):
    # 袩褉芯胁械褉褟械屑, 褟胁谢褟械褌褋褟 谢懈 锌芯谢褜蟹芯胁邪褌械谢褜 邪写屑懈薪懈褋褌褉邪褌芯褉芯屑 (锌芯 user_id)
    if str(message.from_user.id) not in ADMIN_IDS:  # 袩褉械芯斜褉邪蟹褍械屑 胁 褋褌褉芯泻褍 写谢褟 褋褉邪胁薪械薪懈褟
        bot.send_message(message.chat.id, "校 胁邪褋 薪械褌 锌褉邪胁 薪邪 胁褘锌芯谢薪械薪懈械 褝褌芯泄 泻芯屑邪薪写褘.")
        return

    # 小锌褉邪褕懈胁邪械屑 褍 邪写屑懈薪懈褋褌褉邪褌芯褉邪 ID 懈谐褉芯泻邪, 褍 泻芯褌芯褉芯谐芯 薪褍卸薪芯 蟹邪斜褉邪褌褜 锌褉械屑懈褍屑
    bot.send_message(message.chat.id, "袙胁械写懈褌械 ID 懈谐褉芯泻邪, 褍 泻芯褌芯褉芯谐芯 胁褘 褏芯褌懈褌械 蟹邪斜褉邪褌褜 锌褉械屑懈褍屑-褋褌邪褌褍褋:")
    bot.register_next_step_handler(message, process_take_premium_id)

# 袨斜褉邪斜芯褌泻邪 胁胁械写械薪薪芯谐芯 ID 懈谐褉芯泻邪
def process_take_premium_id(message):
    player_id = message.text.strip()

    if not player_id.isdigit():
        bot.send_message(message.chat.id, "袨褕懈斜泻邪: 袙胁械写械薪薪褘泄 ID 薪械 褟胁谢褟械褌褋褟 褔懈褋谢芯屑.")
        return

    # 袩褉芯胁械褉泻邪 薪邪 薪邪谢懈褔懈械 懈谐褉芯泻邪 胁 斜邪蟹械 写邪薪薪褘褏
    cursor.execute("SELECT user_name, premium FROM users WHERE random_id = ?", (player_id,))
    player = cursor.fetchone()

    if player:
        try:
            # 袝褋谢懈 褍 懈谐褉芯泻邪 褍卸械 薪械褌 锌褉械屑懈褍屑-褋褌邪褌褍褋邪, 褍胁械写芯屑谢褟械屑 邪写屑懈薪懈褋褌褉邪褌芯褉邪
            if player[1] == '薪械褌':
                bot.send_message(message.chat.id, "袨褕懈斜泻邪: 校 褝褌芯谐芯 懈谐褉芯泻邪 薪械褌 锌褉械屑懈褍屑-褋褌邪褌褍褋邪.")
                return

            # 袨斜薪芯胁谢褟械屑 褋褌邪褌褍褋 薪邪 "薪械褌" (褍写邪谢褟械屑 锌褉械屑懈褍屑)
            cursor.execute("UPDATE users SET premium = '薪械褌' WHERE random_id = ?", (player_id,))
            conn.commit()

            # 袩芯写褌胁械褉卸写邪械屑 邪写屑懈薪懈褋褌褉邪褌芯褉褍
            bot.send_message(message.chat.id, f"袩褉械屑懈褍屑-褋褌邪褌褍褋 斜褘谢 褍褋锌械褕薪芯 褍斜褉邪薪 褍 懈谐褉芯泻邪 褋 ID {player_id}.")

            # 袨褌锌褉邪胁谢褟械屑 褋芯芯斜褖械薪懈械 懈谐褉芯泻褍
            player_name = player[0]
            cursor.execute("SELECT user_id FROM users WHERE random_id = ?", (player_id,))
            player_user_id = cursor.fetchone()[0]
            bot.send_message(player_user_id,
                             f"袙邪褕 锌褉械屑懈褍屑-褋褌邪褌褍褋 斜褘谢 褍斜褉邪薪. 孝械锌械褉褜 褍 胁邪褋 斜芯谢褜褕械 薪械褌 写芯褋褌褍锌邪 泻 褝泻褋泻谢褞蟹懈胁薪褘屑 褎褍薪泻褑懈褟屑.")

            # 袨斜薪芯胁谢褟械屑 屑械薪褞 斜械蟹 锌褉械屑懈褍屑-褋褌邪褌褍褋邪
            premium_status = False  # 袩褉械屑懈褍屑 褋薪褟褌
            markup = create_main_menu(premium=premium_status)
            bot.send_message(player_user_id, "袦械薪褞 芯斜薪芯胁谢械薪芯!", reply_markup=markup)

        except Exception as e:
            # 袨褕懈斜泻邪 锌褉懈 芯斜薪芯胁谢械薪懈懈 斜邪蟹褘 写邪薪薪褘褏
            conn.rollback()  # 袨褌泻邪褌褘胁邪械屑 懈蟹屑械薪械薪懈褟 胁 褋谢褍褔邪械 芯褕懈斜泻懈
            bot.send_message(message.chat.id, f"袨褕懈斜泻邪 锌褉懈 芯斜薪芯胁谢械薪懈懈 斜邪蟹褘 写邪薪薪褘褏: {str(e)}")
    else:
        bot.send_message(message.chat.id, "袨褕懈斜泻邪: 袠谐褉芯泻 褋 褌邪泻懈屑 ID 薪械 薪邪泄写械薪.")



@bot.message_handler(commands=['give_premium'])
def give_premium(message):
    # 袩褉芯胁械褉褟械屑, 褟胁谢褟械褌褋褟 谢懈 锌芯谢褜蟹芯胁邪褌械谢褜 邪写屑懈薪懈褋褌褉邪褌芯褉芯屑 (锌芯 user_id)
    if str(message.from_user.id) not in ADMIN_IDS:  # 袩褉械芯斜褉邪蟹褍械屑 胁 褋褌褉芯泻褍 写谢褟 褋褉邪胁薪械薪懈褟
        bot.send_message(message.chat.id, "校 胁邪褋 薪械褌 锌褉邪胁 薪邪 胁褘锌芯谢薪械薪懈械 褝褌芯泄 泻芯屑邪薪写褘.")
        return

    # 小锌褉邪褕懈胁邪械屑 褍 邪写屑懈薪懈褋褌褉邪褌芯褉邪 ID 懈谐褉芯泻邪, 泻芯褌芯褉芯屑褍 薪褍卸薪芯 胁褘写邪褌褜 锌褉械屑懈褍屑
    bot.send_message(message.chat.id, "袙胁械写懈褌械 ID 懈谐褉芯泻邪, 泻芯褌芯褉芯屑褍 胁褘 褏芯褌懈褌械 胁褘写邪褌褜 锌褉械屑懈褍屑-褋褌邪褌褍褋:")
    bot.register_next_step_handler(message, process_premium_id)

# 袨斜褉邪斜芯褌泻邪 胁胁械写械薪薪芯谐芯 ID 懈谐褉芯泻邪
def process_premium_id(message):
    player_id = message.text.strip()

    if not player_id.isdigit():
        bot.send_message(message.chat.id, "袨褕懈斜泻邪: 袙胁械写械薪薪褘泄 ID 薪械 褟胁谢褟械褌褋褟 褔懈褋谢芯屑.")
        return

    cursor.execute("SELECT user_name, premium FROM users WHERE random_id = ?", (player_id,))
    player = cursor.fetchone()

    if player:
        try:
            # 袩褉芯胁械褉褟械屑, 斜褘谢 谢懈 褍卸械 胁褘写邪薪 锌褉械屑懈褍屑 褋褌邪褌褍褋
            if player[1] == '写邪':
                bot.send_message(message.chat.id, "袨褕懈斜泻邪: 校 褝褌芯谐芯 懈谐褉芯泻邪 褍卸械 械褋褌褜 锌褉械屑懈褍屑-褋褌邪褌褍褋.")
                return

            # 袨斜薪芯胁谢褟械屑 褋褌邪褌褍褋 薪邪 "锌褉械屑懈褍屑"
            cursor.execute("UPDATE users SET premium = '写邪' WHERE random_id = ?", (player_id,))
            conn.commit()

            # 袩芯写褌胁械褉卸写邪械屑 邪写屑懈薪懈褋褌褉邪褌芯褉褍
            bot.send_message(message.chat.id, f"袩褉械屑懈褍屑-褋褌邪褌褍褋 斜褘谢 褍褋锌械褕薪芯 胁褘写邪薪 懈谐褉芯泻褍 褋 ID {player_id}.")

            # 袨褌锌褉邪胁谢褟械屑 褋芯芯斜褖械薪懈械 懈谐褉芯泻褍
            player_name = player[0]
            cursor.execute("SELECT user_id FROM users WHERE random_id = ?", (player_id,))
            player_user_id = cursor.fetchone()[0]
            bot.send_message(player_user_id,
                             f"袩芯蟹写褉邪胁谢褟械屑, {player_name}! 袙褘 锌芯谢褍褔懈谢懈 锌褉械屑懈褍屑-褋褌邪褌褍褋. 孝械锌械褉褜 褍 胁邪褋 写芯褋褌褍锌 泻 褝泻褋泻谢褞蟹懈胁薪褘屑 褎褍薪泻褑懈褟屑.")

            # 袨斜薪芯胁谢褟械屑 泻谢邪胁懈邪褌褍褉褍 懈谐褉芯泻邪 褋 锌褉械屑懈褍屑-屑械薪褞
            premium_status = True  # 袩褉械屑懈褍屑 邪泻褌懈胁懈褉芯胁邪薪
            markup = create_main_menu(premium=premium_status)
            bot.send_message(player_user_id, "袦械薪褞 芯斜薪芯胁谢械薪芯!", reply_markup=markup)

        except Exception as e:
            conn.rollback()  # 袨褌泻邪褌 懈蟹屑械薪械薪懈泄 胁 褋谢褍褔邪械 芯褕懈斜泻懈
            bot.send_message(message.chat.id, f"袨褕懈斜泻邪 锌褉懈 芯斜薪芯胁谢械薪懈懈 斜邪蟹褘 写邪薪薪褘褏: {str(e)}")
    else:
        bot.send_message(message.chat.id, "袨褕懈斜泻邪: 袠谐褉芯泻 褋 褌邪泻懈屑 ID 薪械 薪邪泄写械薪.")


# 袟邪锌褍褋泻 斜芯褌邪

@bot.message_handler(func=lambda message: message.text == "馃懃 袛褉褍蟹褜褟")
def show_friends(message):
    try:
        user_id = str(message.from_user.id)

        # 袩芯谢褍褔邪械屑 褋锌懈褋芯泻 写褉褍蟹械泄 写谢褟 褌械泻褍褖械谐芯 锌芯谢褜蟹芯胁邪褌械谢褟
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

        # 袝褋谢懈 褋锌懈褋芯泻 写褉褍蟹械泄 锌褍褋褌
        if not friends:
            image_path = 'friends.png'  # 袟邪屑械薪懈褌械 薪邪 锌褍褌褜 泻 褋胁芯械屑褍 懈蟹芯斜褉邪卸械薪懈褞
            try:
                with open(image_path, 'rb') as photo:
                    bot.send_photo(message.chat.id, photo, caption="馃懃 袙邪褕 褋锌懈褋芯泻 写褉褍蟹械泄 锌褍褋褌.")
            except Exception as e:
                logger.error(f"袨褕懈斜泻邪 锌褉懈 芯褌锌褉邪胁泻械 褎芯褌芯: {e}")
                bot.reply_to(message, "鉂� 袨褕懈斜泻邪 锌褉懈 芯褌锌褉邪胁泻械 褎芯褌芯.")
            return

        # 袝褋谢懈 写褉褍蟹褜褟 械褋褌褜, 褎芯褉屑懈褉褍械屑 褋锌懈褋芯泻 写褉褍蟹械泄
        response = "馃懃 袙邪褕懈 写褉褍蟹褜褟:\n\n"
        for friend in friends:
            if friend[3] == 0:  # 袝褋谢懈 锌褉芯褎懈谢褜 写褉褍谐邪 薪械 褋泻褉褘褌
                status = "馃幃 袙 懈谐褉械" if friend[4] else "馃煝 袨薪谢邪泄薪"
                response += f"馃懁 {friend[0]} | {friend[1]} | ID: {friend[2]} | {status}\n"

        # 袩褍褌褜 泻 懈蟹芯斜褉邪卸械薪懈褞 (屑芯卸薪芯 蟹邪屑械薪懈褌褜 薪邪 锌褍褌褜 泻 薪褍卸薪芯屑褍 懈蟹芯斜褉邪卸械薪懈褞)
        image_path = 'friends.png'  # 袟邪屑械薪懈褌械 薪邪 锌褍褌褜 泻 褋胁芯械屑褍 懈蟹芯斜褉邪卸械薪懈褞

        try:
            # 袨褌锌褉邪胁泻邪 褋芯芯斜褖械薪懈褟 褋 锌褉懈胁褟蟹邪薪薪褘屑 褎芯褌芯
            with open(image_path, 'rb') as photo:
                bot.send_photo(message.chat.id, photo, caption=response)
        except Exception as e:
            logger.error(f"袨褕懈斜泻邪 锌褉懈 芯褌锌褉邪胁泻械 褎芯褌芯: {e}")
            bot.reply_to(message, "鉂� 袨褕懈斜泻邪 锌褉懈 芯褌锌褉邪胁泻械 褎芯褌芯.")

    except Exception as e:
        logger.error(f"袨褕懈斜泻邪 锌褉懈 芯斜褉邪斜芯褌泻械 泻芯屑邪薪写褘 /friends: {e}")
        bot.reply_to(message, "鉂� 袩褉芯懈蟹芯褕谢邪 芯褕懈斜泻邪 锌褉懈 锌芯谢褍褔械薪懈懈 褋锌懈褋泻邪 写褉褍蟹械泄.")

@bot.message_handler(func=lambda message: message.text == "鈿欙笍 袛芯斜邪胁懈褌褜 写褉褍谐邪")
def add_friend_handler(message):
    try:
        user_id = str(message.from_user.id)
        bot.reply_to(message, "袙胁械写懈褌械 ID 懈谢懈 薪懈泻薪械泄屑 胁邪褕械谐芯 写褉褍谐邪:")
        bot.register_next_step_handler(message, process_friend_request, user_id)
    except Exception as e:
        handle_error(e, message)

def process_friend_request(message, user_id):
    try:
        target = message.text.strip()

        if not target:
            bot.reply_to(message, "鉂� 袙褘 薪械 胁胁械谢懈 ID 懈谢懈 薪懈泻薪械泄屑. 袩芯锌褉芯斜褍泄褌械 褋薪芯胁邪.")
            return

        # 袠褖械屑 锌芯谢褜蟹芯胁邪褌械谢褟 锌芯 ID 懈谢懈 薪懈泻薪械泄屑褍
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
            bot.reply_to(message, "鉂� 袩芯谢褜蟹芯胁邪褌械谢褜 褋 褌邪泻懈屑 ID 懈谢懈 薪懈泻薪械泄屑芯屑 薪械 薪邪泄写械薪.")
            return

        friend_id, friend_name, is_hidden, is_friend = result

        # 袩褉芯胁械褉褟械屑 褉邪蟹谢懈褔薪褘械 褍褋谢芯胁懈褟
        if user_id == friend_id:
            bot.reply_to(message, "鉂� 袙褘 薪械 屑芯卸械褌械 写芯斜邪胁懈褌褜 褋械斜褟 胁 写褉褍蟹褜褟.")
            return

        if is_hidden == 1:
            bot.reply_to(message, f"鉂� 袩褉芯褎懈谢褜 {friend_name} 褋泻褉褘褌.")
            return

        if is_friend > 0:
            bot.reply_to(message, "鉂� 协褌芯褌 锌芯谢褜蟹芯胁邪褌械谢褜 褍卸械 胁 胁邪褕械屑 褋锌懈褋泻械 写褉褍蟹械泄.")
            return

        # 小芯蟹写邪械屑 蟹邪锌褉芯褋 薪邪 写芯斜邪胁谢械薪懈械 胁 写褉褍蟹褜褟
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("鉁� 袩褉懈薪褟褌褜", callback_data=f"accept_friend_{user_id}"),
            types.InlineKeyboardButton("鉂� 袨褌泻谢芯薪懈褌褜", callback_data=f"decline_friend_{user_id}")
        )

        # 袩芯谢褍褔邪械屑 懈屑褟 芯褌锌褉邪胁懈褌械谢褟 蟹邪锌褉芯褋邪
        cursor.execute("SELECT user_name FROM users WHERE user_id = ?", (user_id,))
        sender_name = cursor.fetchone()[0]

        bot.send_message(
            friend_id,
            f"馃摠 袩芯谢褜蟹芯胁邪褌械谢褜 {sender_name} 褏芯褔械褌 写芯斜邪胁懈褌褜 胁邪褋 胁 写褉褍蟹褜褟!",
            reply_markup=markup
        )
        bot.reply_to(message, f"鉁� 袟邪锌褉芯褋 薪邪 写芯斜邪胁谢械薪懈械 芯褌锌褉邪胁谢械薪 {friend_name}!")

    except Exception as e:
        handle_error(e, message)

@bot.callback_query_handler(func=lambda call: call.data.startswith(("accept_friend_", "decline_friend_")))
def handle_friend_request(call):
    try:
        action, sender_id = call.data.split("_")[0], call.data.split("_")[2]
        receiver_id = str(call.from_user.id)

        if action == "accept":
            # 袛芯斜邪胁谢褟械屑 蟹邪锌懈褋褜 芯 写褉褍卸斜械
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("""
                INSERT INTO friends (user_id, friend_id, added_date)
                VALUES (?, ?, ?)
            """, (sender_id, receiver_id, current_time))
            conn.commit()

            # 袩芯谢褍褔邪械屑 懈屑械薪邪 锌芯谢褜蟹芯胁邪褌械谢械泄
            cursor.execute("SELECT user_name FROM users WHERE user_id = ?", (receiver_id,))
            receiver_name = cursor.fetchone()[0]
            cursor.execute("SELECT user_name FROM users WHERE user_id = ?", (sender_id,))
            sender_name = cursor.fetchone()[0]

            # 袨褌锌褉邪胁谢褟械屑 褍胁械写芯屑谢械薪懈褟 芯斜芯懈屑 锌芯谢褜蟹芯胁邪褌械谢褟屑
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"鉁� 袙褘 锌褉懈薪褟谢懈 蟹邪锌褉芯褋 薪邪 写褉褍卸斜褍 芯褌 {sender_name}!",
                reply_markup=None
            )
            bot.send_message(
                sender_id,
                f"馃帀 {receiver_name} 锌褉懈薪褟谢(邪) 胁邪褕 蟹邪锌褉芯褋 薪邪 写褉褍卸斜褍!"
            )

        else:  # decline
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="鉂� 袙褘 芯褌泻谢芯薪懈谢懈 蟹邪锌褉芯褋 薪邪 写褉褍卸斜褍.",
                reply_markup=None
            )
            cursor.execute("SELECT user_name FROM users WHERE user_id = ?", (receiver_id,))
            receiver_name = cursor.fetchone()[0]
            bot.send_message(
                sender_id,
                f"鉂� {receiver_name} 芯褌泻谢芯薪懈谢(邪) 胁邪褕 蟹邪锌褉芯褋 薪邪 写褉褍卸斜褍."
            )

    except Exception as e:
        handle_error(e, call.message)


@bot.message_handler(func=lambda message: message.text == "馃幃 袙褋械 懈谐褉芯泻懈")
def show_all_players(message):
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
            bot.reply_to(message, "馃懃 小锌懈褋芯泻 懈谐褉芯泻芯胁 锌褍褋褌")
            return

        response = "馃懃 小锌懈褋芯泻 胁褋械褏 懈谐褉芯泻芯胁:\n\n"
        for player in players:
            name, country, player_id, _, active_game, kills, deaths, matches, premium = player
            kd_ratio = kills / max(deaths, 1)
            status = "馃幃 袙 懈谐褉械" if active_game else "馃煝 袨薪谢邪泄薪"
            premium_status = "猸�" if premium == '写邪' else ""

            response += (
                f"{premium_status}馃懁 {name} | {country}\n"
                f"馃搳 K/D: {kd_ratio:.2f} | 袦邪褌褔懈: {matches}\n"
                f"馃啍 ID: {player_id} | {status}\n"
                f"鈹�鈹�鈹�鈹�鈹�鈹�鈹�鈹�鈹�鈹�鈹�鈹�鈹�鈹�鈹�\n"
            )

        # 袪邪蟹写械谢褟械屑 褋芯芯斜褖械薪懈械 薪邪 褔邪褋褌懈, 械褋谢懈 芯薪芯 褋谢懈褕泻芯屑 写谢懈薪薪芯械
        if len(response) > 4096:
            for x in range(0, len(response), 4096):
                bot.send_message(message.chat.id, response[x:x+4096])
        else:
            bot.send_message(message.chat.id, response)

    except Exception as e:
        handle_error(e, message)


class SearchManager:
    def __init__(self):
        self.player_searches = {}  # 啸褉邪薪懈褌 邪泻褌懈胁薪褘械 锌芯懈褋泻懈 懈谐褉芯泻芯胁
        self.active_searches = {}  # 啸褉邪薪懈褌 写邪薪薪褘械 芯 锌芯懈褋泻邪褏
        self.active_servers = {}  # 啸褉邪薪懈褌 邪泻褌懈胁薪褘械 褋械褉胁械褉褘

    def create_new_search(self):
        search_id = len(self.active_searches) + 1  # 袩褉芯褋褌芯 谐械薪械褉懈褉褍械屑 薪芯胁褘泄 ID
        self.active_searches[search_id] = {'players': []}  # 袠薪懈褑懈邪谢懈蟹懈褉褍械屑 锌芯懈褋泻
        return search_id


# 袠薪懈褑懈邪谢懈蟹邪褑懈褟 屑械薪械写卸械褉邪
search_manager = SearchManager()


@bot.message_handler(func=lambda message: message.text == "馃搳 小褌邪褌懈褋褌懈泻邪")
def show_statistics(message):
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
            bot.reply_to(message, "鉂� 小褌邪褌懈褋褌懈泻邪 薪械 薪邪泄写械薪邪.")
            return

        kills, deaths, matches, wins, losses, adr, avg, premium, elo = stats
        kd_ratio = kills / max(deaths, 1)
        win_rate = wins / max(matches, 1) * 100

        # 袪邪褋褔械褌 褍褉芯胁薪褟 锌芯 ELO
        if elo <= 500:
            level = 1
        elif elo <= 750:
            level = 2
        elif elo <= 900:
            level = 3
        elif elo <= 1050:
            level = 4
        elif elo <= 1200:
            level = 5
        elif elo <= 1350:
            level = 6
        elif elo <= 1530:
            level = 7
        elif elo <= 1750:
            level = 8
        elif elo <= 2000:
            level = 9
        elif elo <= 2001:
            level = 10

        stats_message = (
            "馃殌 袙 褉邪蟹褉邪斜芯褌泻械 馃殌\n\n"
            "馃搳 袙邪褕邪 褋褌邪褌懈褋褌懈泻邪:\n"
            f"馃幆 K/D: {kd_ratio:.2f}\n"
            f"馃幃 袦邪褌褔械泄 褋褘谐褉邪薪芯: {matches}\n"
            f"馃敨 校斜懈泄褋褌胁: {kills}\n"
            f"馃拃 小屑械褉褌械泄: {deaths}\n"
            f"馃弳 袩芯斜械写: {wins}\n"
            f"鉂� 袩芯褉邪卸械薪懈泄: {losses}\n"
            f"馃搱 袩褉芯褑械薪褌 锌芯斜械写: {win_rate:.1f}%\n"
            f"猸愶笍 校褉芯胁械薪褜: {level} ({elo} ELO)\n"
        )

        if premium == '写邪':
            stats_message += (
                "\n猸� 袩褉械屑懈褍屑 褋褌邪褌懈褋褌懈泻邪:\n"
                f"馃挗 ADR: {adr:.1f}\n"
                f"馃搳 小褉械写薪懈泄 褉械泄褌懈薪谐: {avg:.1f}\n"
            )

        bot.reply_to(message, stats_message)
    except Exception as e:
        handle_error(e, message)
@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_"))
def handle_admin_actions(call):
    try:
        user_id = str(call.from_user.id)
        if user_id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "鉂� 袧械写芯褋褌邪褌芯褔薪芯 锌褉邪胁.")
            return

        action = call.data.split("_")[1]

        if action == "restart_servers":
            cleanup_servers()
            bot.answer_callback_query(call.id, "鉁� 小械褉胁械褉褘 锌械褉械蟹邪锌褍褖械薪褘.")
            bot.edit_message_text(
                "鉁� 小械褉胁械褉褘 褍褋锌械褕薪芯 锌械褉械蟹邪锌褍褖械薪褘.",
                call.message.chat.id,
                call.message.message_id
            )

        elif action == "system_stats":
            stats = get_system_stats()
            bot.edit_message_text(
                stats,
                call.message.chat.id,
                call.message.message_id
            )

        elif action == "manage_bans":
            show_banned_users(call.message)

    except Exception as e:
        handle_error(e, call.message)

def get_system_stats():
    try:
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM users WHERE premium = '写邪'")
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
            "馃搳 小褌邪褌懈褋褌懈泻邪 褋懈褋褌械屑褘:\n\n"
            f"馃懃 袙褋械谐芯 锌芯谢褜蟹芯胁邪褌械谢械泄: {total_users}\n"
            f"猸� 袩褉械屑懈褍屑 锌芯谢褜蟹芯胁邪褌械谢械泄: {premium_users}\n"
            f"馃毇 袗泻褌懈胁薪褘褏 斜邪薪芯胁: {active_bans}\n"
            f"馃幃 袙褋械谐芯 屑邪褌褔械泄: {stats[1] or 0}\n"
            f"馃挜 袙褋械谐芯 褍斜懈泄褋褌胁: {stats[2] or 0}\n"
            f"馃拃 袙褋械谐芯 褋屑械褉褌械泄: {stats[3] or 0}\n"
            f"馃幉 袗泻褌懈胁薪褘褏 褋械褉胁械褉芯胁: {len(active_servers)}\n"
            f"馃攳 袠谐褉芯泻芯胁 胁 锌芯懈褋泻械: {len(search_players)}"
        )
    except Exception as e:
        logging.error(f"Error getting system stats: {e}")
        return "鉂� 袨褕懈斜泻邪 锌芯谢褍褔械薪懈褟 褋褌邪褌懈褋褌懈泻懈"

def show_banned_users(message):
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
            bot.edit_message_text(
                "馃毇 袧械褌 邪泻褌懈胁薪褘褏 斜邪薪芯胁",
                message.chat.id,
                message.message_id
            )
            return

        ban_list = "馃毇 小锌懈褋芯泻 蟹邪斜邪薪械薪薪褘褏 锌芯谢褜蟹芯胁邪褌械谢械泄:\n\n"
        for ban in bans:
            ban_list += (
                f"馃懁 {ban[0]}\n"
                f"馃摑 袩褉懈褔懈薪邪: {ban[1]}\n"
                f"馃搮 袛邪褌邪 斜邪薪邪: {ban[2]}\n"
                f"馃搮 袪邪蟹斜邪薪: {ban[3]}\n"
                "鈹�鈹�鈹�鈹�鈹�鈹�鈹�鈹�鈹�鈹�鈹�鈹�鈹�鈹�鈹�\n"
            )

        bot.edit_message_text(
            ban_list,
            message.chat.id,
            message.message_id
        )
    except Exception as e:
        handle_error(e, message)

user_states = {}
WAITING_FOR_REPORT = "waiting_for_report"


@bot.message_handler(func=lambda message: message.text == "馃摑袞邪谢芯斜邪 薪邪 懈谐褉芯泻邪")
def start_report(message):
    user_id = message.from_user.id
    user_states[user_id] = WAITING_FOR_REPORT

    # 袩褍褌褜 泻 胁邪褕械屑褍 懈蟹芯斜褉邪卸械薪懈褞
    image_path = 'report.png'  # 袟邪屑械薪懈褌械 薪邪 邪泻褌褍邪谢褜薪褘泄 锌褍褌褜

    try:
        with open(image_path, 'rb') as photo:
            # 袨褌锌褉邪胁谢褟械屑 褎芯褌芯 懈 褌械泻褋褌
            bot.send_photo(
                user_id,
                photo,
                caption="袩芯卸邪谢褍泄褋褌邪, 薪邪锌懈褕懈褌械 褌械泻褋褌 胁邪褕械泄 卸邪谢芯斜褘."
            )
    except Exception as e:
        bot.send_message(user_id, "鉂� 袨褕懈斜泻邪 锌褉懈 芯褌锌褉邪胁泻械 懈蟹芯斜褉邪卸械薪懈褟.")
        logger.error(f"袨褕懈斜泻邪 锌褉懈 芯褌锌褉邪胁泻械 懈蟹芯斜褉邪卸械薪懈褟: {e}")


# Handle text messages from users
@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == WAITING_FOR_REPORT)
def process_report(message):
    user_id = message.from_user.id
    # Send the complaint to admin
    bot.send_message(ADMIN_IDS, f"袞邪谢芯斜邪 芯褌 {message.from_user.full_name} (ID: {user_id}): {message.text}")

    # Inform the user
    bot.send_message(user_id, "袙邪褕邪 卸邪谢芯斜邪 芯褌锌褉邪胁谢械薪邪 邪写屑懈薪懈褋褌褉邪褌芯褉褍.")

    # Reset the state for the user
    user_states[user_id] = None

user_ids = set()


@bot.message_handler(commands=['send_news'])
def send_news(message):
    if str(message.from_user.id) in ADMIN_IDS:  # 袩褉芯胁械褉泻邪, 械褋谢懈 ID 锌芯谢褜蟹芯胁邪褌械谢褟 胁 褋锌懈褋泻械 邪写屑懈薪懈褋褌褉邪褌芯褉芯胁
        # 袟邪锌褉邪褕懈胁邪械屑 褌械泻褋褌 薪芯胁芯褋褌懈
        bot.send_message(message.chat.id, "袩芯卸邪谢褍泄褋褌邪, 胁胁械写懈褌械 褌械泻褋褌 薪芯胁芯褋褌懈.")
        # 袩械褉械褏芯写 泻 褋谢械写褍褞褖械屑褍 褕邪谐褍, 褔褌芯斜褘 芯卸懈写邪褌褜 褌械泻褋褌 薪芯胁芯褋褌懈
        bot.register_next_step_handler(message, send_news_to_all)
    else:
        bot.send_message(message.chat.id, "校 胁邪褋 薪械褌 锌褉邪胁 写谢褟 芯褌锌褉邪胁泻懈 薪芯胁芯褋褌械泄.")


def send_news_to_all(message):
    news_text = message.text  # 袩芯谢褍褔邪械屑 褌械泻褋褌 薪芯胁芯褋褌懈 芯褌 邪写屑懈薪懈褋褌褉邪褌芯褉邪

    try:
        # 袠蟹胁谢械泻邪械屑 胁褋械褏 锌芯谢褜蟹芯胁邪褌械谢械泄 懈蟹 斜邪蟹褘 写邪薪薪褘褏
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()

        # 袩褉芯胁械褉褟械屑, 械褋褌褜 谢懈 锌芯谢褜蟹芯胁邪褌械谢懈 胁 斜邪蟹械
        if users:
            for user in users:
                try:
                    user_id = user[0]
                    # 袨褌锌褉邪胁谢褟械屑 薪芯胁芯褋褌褜 泻邪卸写芯屑褍 锌芯谢褜蟹芯胁邪褌械谢褞
                    bot.send_message(user_id, f"馃摪 袧芯胁芯褋褌褜: {news_text}")
                except Exception as e:
                    print(f"袧械 褍写邪谢芯褋褜 芯褌锌褉邪胁懈褌褜 薪芯胁芯褋褌褜 锌芯谢褜蟹芯胁邪褌械谢褞 {user_id}: {e}")

            bot.send_message(message.chat.id, "袧芯胁芯褋褌褜 褍褋锌械褕薪芯 芯褌锌褉邪胁谢械薪邪 胁褋械屑 锌芯谢褜蟹芯胁邪褌械谢褟屑!")
        else:
            bot.send_message(message.chat.id, "袙 斜邪蟹械 写邪薪薪褘褏 薪械褌 锌芯谢褜蟹芯胁邪褌械谢械泄 写谢褟 褉邪褋褋褘谢泻懈.")
    except Exception as e:
        bot.send_message(message.chat.id, f"袩褉芯懈蟹芯褕谢邪 芯褕懈斜泻邪 锌褉懈 芯褌锌褉邪胁泻械 薪芯胁芯褋褌懈: {e}")

# 肖褍薪泻褑懈褟 写谢褟 邪泻褌懈胁邪褑懈懈 锌褉械屑懈褍屑-褋褌邪褌褍褋邪
def activate_premium(user_id, inviter_id):
    # 袗泻褌懈胁懈褉褍械屑 锌褉械屑懈褍屑-褋褌邪褌褍褋 写谢褟 锌芯谢褜蟹芯胁邪褌械谢褟, 泻芯褌芯褉褘泄 邪泻褌懈胁懈褉芯胁邪谢 泻芯写
    cursor.execute('UPDATE users SET premium = "写邪" WHERE user_id = ?', (user_id,))
    conn.commit()

    # 袗泻褌懈胁懈褉褍械屑 锌褉械屑懈褍屑-褋褌邪褌褍褋 写谢褟 锌褉懈谐谢邪褋懈胁褕械谐芯 锌芯谢褜蟹芯胁邪褌械谢褟, 械褋谢懈 芯薪 械褖械 薪械 锌褉械屑懈褍屑
    cursor.execute('SELECT premium FROM users WHERE user_id = ?', (inviter_id,))
    inviter = cursor.fetchone()

    if inviter and inviter[0] != '写邪':  # 袩褉芯胁械褉褟械屑, 褔褌芯 锌褉懈谐谢邪褋懈胁褕懈泄 薪械 锌褉械屑懈褍屑
        cursor.execute('UPDATE users SET premium = "写邪" WHERE user_id = ?', (inviter_id,))
        conn.commit()

    # 校胁械谢懈褔懈胁邪械屑 泻芯谢懈褔械褋褌胁芯 褉械褎械褉邪谢芯胁 褍 锌褉懈谐谢邪褋懈胁褕械谐芯
    cursor.execute('UPDATE users SET referral_count = referral_count + 1 WHERE user_id = ?', (inviter_id,))
    conn.commit()

    # 袨褌锌褉邪胁谢褟械屑 褋芯芯斜褖械薪懈械 锌芯谢褜蟹芯胁邪褌械谢褞, 泻芯褌芯褉褘泄 邪泻褌懈胁懈褉芯胁邪谢 泻芯写
    bot.send_message(user_id, "袙褘 褍褋锌械褕薪芯 蟹邪褉械谐懈褋褌褉懈褉芯胁邪谢懈褋褜 锌芯 褉械褎械褉邪谢褜薪芯屑褍 泻芯写褍! 袙褘 褌械锌械褉褜 锌褉械屑懈褍屑-锌芯谢褜蟹芯胁邪褌械谢褜!")

    # 袨褌锌褉邪胁谢褟械屑 褋芯芯斜褖械薪懈械 锌褉懈谐谢邪褋懈胁褕械屑褍
    bot.send_message(inviter_id, f"袙邪褕 褉械褎械褉邪谢褜薪褘泄 泻芯写 斜褘谢 懈褋锌芯谢褜蟹芯胁邪薪! {user_id} 褋褌邪谢 锌褉械屑懈褍屑-锌芯谢褜蟹芯胁邪褌械谢械屑.")
    markup_user = create_main_menu(premium=premium_status_user)  # 小芯蟹写邪械屑 屑械薪褞 写谢褟 锌芯谢褜蟹芯胁邪褌械谢褟
    markup_inviter = create_main_menu(premium=premium_status_inviter)  # 小芯蟹写邪械屑 屑械薪褞 写谢褟 锌褉懈谐谢邪褋懈胁褕械谐芯
    bot.send_message(user_id, "袦械薪褞 芯斜薪芯胁谢械薪芯!", reply_markup=markup_user)

    # 孝邪泄屑械褉 薪邪 写械邪泻褌懈胁邪褑懈褞 锌褉械屑懈褍屑-褋褌邪褌褍褋邪 褔械褉械蟹 100 褋械泻褍薪写 (锌褉懈屑械褉)
    threading.Timer(100, deactivate_premium, [user_id]).start()

# 肖褍薪泻褑懈褟 写谢褟 写械邪泻褌懈胁邪褑懈懈 锌褉械屑懈褍屑-褋褌邪褌褍褋邪
def deactivate_premium(user_id):
    cursor.execute('UPDATE users SET premium = "薪械褌" WHERE user_id = ?', (user_id,))
    conn.commit()

#

# 袨斜褉邪斜芯褌褔懈泻 泻芯屑邪薪写褘 /referalcode
@bot.message_handler(commands=['referalcode'])
def referalcode(message):
    user_id = message.from_user.id
    # 校褋褌邪薪邪胁谢懈胁邪械屑 褎谢邪谐, 褔褌芯 斜芯褌 芯卸懈写邪械褌 胁胁芯写 褉械褎械褉邪谢褜薪芯谐芯 泻芯写邪
    waiting_for_referral_code[user_id] = True
    bot.send_message(user_id, "袙胁械写懈褌械 褉械褎械褉邪谢褜薪褘泄 泻芯写:")

# 袨斜褉邪斜芯褌褔懈泻 胁胁芯写邪 褌械泻褋褌邪 (褉械褎械褉邪谢褜薪芯谐芯 泻芯写邪)
@bot.message_handler(func=lambda message: message.text.strip() != "" and message.text[0] != "/")
def handle_referral_code(message):
    user_id = message.from_user.id

    # 袩褉芯胁械褉褟械屑, 芯卸懈写邪械屑 谢懈 屑褘 芯褌 褝褌芯谐芯 锌芯谢褜蟹芯胁邪褌械谢褟 胁胁芯写 褉械褎械褉邪谢褜薪芯谐芯 泻芯写邪
    if user_id in waiting_for_referral_code and waiting_for_referral_code[user_id]:
        referral_code = message.text.strip()

        try:
            # 袩褉芯胁械褉泻邪 薪邪 写械泄褋褌胁懈褌械谢褜薪芯褋褌褜 褉械褎械褉邪谢褜薪芯谐芯 泻芯写邪 胁 锌芯谢械 referral_code
            cursor.execute('SELECT user_id, premium, used FROM users WHERE referral_code = ?', (referral_code,))
            result = cursor.fetchone()

            if result:
                inviter_id, inviter_premium, used = result
                print(f"Debug: inviter_id = {inviter_id}, user_id = {user_id}, used = {used}")  # 袛谢褟 芯褌谢邪写泻懈

                # 袩褉芯胁械褉泻邪, 懈褋锌芯谢褜蟹芯胁邪谢 谢懈 锌芯谢褜蟹芯胁邪褌械谢褜 褍卸械 褝褌芯褌 泻芯写
                cursor.execute('SELECT used FROM users WHERE user_id = ?', (user_id,))
                user_data = cursor.fetchone()

                if user_data and user_data[0] == 1:
                    bot.send_message(user_id, "袙褘 褍卸械 懈褋锌芯谢褜蟹芯胁邪谢懈 褝褌芯褌 褉械褎械褉邪谢褜薪褘泄 泻芯写.")
                else:
                    # 袩褉芯胁械褉泻邪, 褔褌芯斜褘 锌芯谢褜蟹芯胁邪褌械谢褜 薪械 懈褋锌芯谢褜蟹芯胁邪谢 褋胁芯泄 褋芯斜褋褌胁械薪薪褘泄 泻芯写
                    if str(inviter_id) != str(user_id):  # 袩褉械芯斜褉邪蟹褍械屑 胁 褋褌褉芯泻褍
                        # 袗泻褌懈胁懈褉褍械屑 锌褉械屑懈褍屑-褋褌邪褌褍褋
                        activate_premium(user_id, inviter_id)

                        # 袨褌屑械褌懈屑, 褔褌芯 泻芯写 懈褋锌芯谢褜蟹芯胁邪薪 写谢褟 褝褌芯谐芯 锌芯谢褜蟹芯胁邪褌械谢褟
                        cursor.execute('UPDATE users SET used = 1 WHERE user_id = ?', (user_id,))
                        conn.commit()

                        bot.send_message(user_id, "袙褘 褍褋锌械褕薪芯 蟹邪褉械谐懈褋褌褉懈褉芯胁邪谢懈褋褜 锌芯 褉械褎械褉邪谢褜薪芯屑褍 泻芯写褍! 袙褘 褌械锌械褉褜 锌褉械屑懈褍屑-锌芯谢褜蟹芯胁邪褌械谢褜!")

                        # 袩芯褋谢械 邪泻褌懈胁邪褑懈懈 锌褉械屑懈褍屑-褋褌邪褌褍褋邪, 芯斜薪芯胁谢褟械屑 屑械薪褞
                        premium_status_user = True  # 袩褉械屑懈褍屑 邪泻褌懈胁懈褉芯胁邪薪 写谢褟 锌芯谢褜蟹芯胁邪褌械谢褟
                        premium_status_inviter = True  # 袩褉械屑懈褍屑 邪泻褌懈胁懈褉芯胁邪薪 写谢褟 锌褉懈谐谢邪褋懈胁褕械谐芯
                        markup_user = create_main_menu(premium=premium_status_user)  # 小芯蟹写邪械屑 屑械薪褞 写谢褟 锌芯谢褜蟹芯胁邪褌械谢褟
                        markup_inviter = create_main_menu(premium=premium_status_inviter)  # 小芯蟹写邪械屑 屑械薪褞 写谢褟 锌褉懈谐谢邪褋懈胁褕械谐芯
                        bot.send_message(user_id, "袦械薪褞 芯斜薪芯胁谢械薪芯!", reply_markup=markup_user)

                    else:
                        bot.send_message(user_id, "袧械胁芯蟹屑芯卸薪芯 懈褋锌芯谢褜蟹芯胁邪褌褜 褋胁芯泄 褋芯斜褋褌胁械薪薪褘泄 泻芯写.")
            else:
                bot.send_message(user_id, "袧械写械泄褋褌胁懈褌械谢褜薪褘泄 褉械褎械褉邪谢褜薪褘泄 泻芯写.")
        except Exception as e:
            bot.send_message(user_id, f"袩褉芯懈蟹芯褕谢邪 芯褕懈斜泻邪 锌褉懈 芯斜褉邪斜芯褌泻械 泻芯写邪: {str(e)}")

        # 小斜褉邪褋褘胁邪械屑 褎谢邪谐, 斜芯谢褜褕械 薪械 卸写械屑 胁胁芯写邪
        del waiting_for_referral_code[user_id]


@bot.message_handler(commands=['ban'])
def ban_user(message):
    if message.from_user.id not in ADMIN_IDS2:
        bot.send_message(message.chat.id, "校 胁邪褋 薪械褌 锌褉邪胁 写谢褟 胁褘锌芯谢薪械薪懈褟 褝褌芯泄 泻芯屑邪薪写褘.")
        return

    bot.send_message(message.chat.id, "袙胁械写懈褌械 懈屑褟 锌芯谢褜蟹芯胁邪褌械谢褟, 泻芯褌芯褉芯谐芯 薪褍卸薪芯 蟹邪斜邪薪懈褌褜:")
    bot.register_next_step_handler(message, process_ban_by_name)


def process_ban_by_name(message):
    user_name_to_ban = message.text.strip()

    # 袠褖械屑 锌芯谢褜蟹芯胁邪褌械谢褟 胁 斜邪蟹械 写邪薪薪褘褏 锌芯 懈屑械薪懈
    cursor.execute("SELECT user_id, user_name, ban_end_time FROM users WHERE user_name=?", (user_name_to_ban,))
    user = cursor.fetchone()

    if not user:
        bot.send_message(message.chat.id, "袩芯谢褜蟹芯胁邪褌械谢褜 褋 褌邪泻懈屑 懈屑械薪械屑 薪械 薪邪泄写械薪.")
        return

    user_id_to_ban, user_name, ban_end_time = user
    bot.send_message(message.chat.id, f"袩芯谢褜蟹芯胁邪褌械谢褜 {user_name} 薪邪泄写械薪 (ID: {user_id_to_ban}). 校泻邪卸懈褌械 锌褉懈褔懈薪褍 斜邪薪邪:")

    # 袩褉芯胁械褉褟械屑, 薪械 懈褋褌械泻 谢懈 褋褉芯泻 斜邪薪邪
    from datetime import datetime

    if ban_end_time:
        ban_end_time = datetime.strptime(ban_end_time, '%Y-%m-%d %H:%M:%S')
        if ban_end_time < datetime.now():
            # 袝褋谢懈 斜邪薪 懈褋褌械泻, 褋薪懈屑邪械屑 械谐芯
            cursor.execute("UPDATE users SET ban_status=0, ban_reason=NULL,  user_id=?",
                           (user_id_to_ban,))
            conn.commit()
            bot.send_message(message.chat.id, f"袘邪薪 褍 锌芯谢褜蟹芯胁邪褌械谢褟 {user_name} 懈褋褌械泻. 小褌邪褌褍褋 褋薪褟褌.")
            return

    # 袩械褉械写邪械屑 user_id 胁 褋谢械写褍褞褖褍褞 褎褍薪泻褑懈褞
    bot.register_next_step_handler(message, lambda msg: ask_ban_duration(msg, user_id_to_ban))


def ask_ban_duration(message, user_id_to_ban):
    reason = message.text.strip()
    bot.send_message(message.chat.id,
                     f"孝械锌械褉褜 褍泻邪卸懈褌械, 薪邪 泻邪泻芯械 胁褉械屑褟 蟹邪斜邪薪懈褌褜 锌芯谢褜蟹芯胁邪褌械谢褟 (薪邪锌褉懈屑械褉, 1d - 1 写械薪褜, 2h - 2 褔邪褋邪, 1w - 1 薪械写械谢褟):")

    # 袩械褉械写邪械屑 胁 褋谢械写褍褞褖褍褞 褎褍薪泻褑懈褞 懈 reason
    bot.register_next_step_handler(message, lambda msg: apply_ban(msg, user_id_to_ban, reason))


def apply_ban(message, user_id_to_ban, reason):
    duration = message.text.strip()

    try:
        # 袩褉械芯斜褉邪蟹褍械屑 胁褉械屑褟, 懈褋锌芯谢褜蟹褍褟 褋芯泻褉邪褖械薪懈褟 h, d, w
        time_units = {'h': 'hours', 'd': 'days', 'w': 'weeks'}
        time_value = 0
        time_unit = None

        # 袧邪褏芯写懈屑 锌芯写褏芯写褟褖懈泄 褋褍褎褎懈泻褋 (h, d, w) 懈 懈蟹胁谢械泻邪械屑 蟹薪邪褔械薪懈械
        for unit, full_unit in time_units.items():
            if unit in duration:
                time_value = int(''.join(filter(str.isdigit, duration)))  # 懈蟹胁谢械泻邪械屑 褌芯谢褜泻芯 褑懈褎褉褘
                time_unit = full_unit
                break

        if time_value == 0 or not time_unit:
            bot.send_message(message.chat.id, "袧械胁械褉薪褘泄 褎芯褉屑邪褌 胁褉械屑械薪懈. 校泻邪卸懈褌械 胁褉械屑褟 胁 褎芯褉屑邪褌械 1d, 2h, 1w 懈 褌.写.")
            return

        # 袩褉械芯斜褉邪蟹褍械屑 胁褉械屑褟 胁 写薪懈
        from datetime import datetime, timedelta

        if time_unit == 'hours':
            ban_end_time = datetime.now() + timedelta(hours=time_value)
        elif time_unit == 'days':
            ban_end_time = datetime.now() + timedelta(days=time_value)
        elif time_unit == 'weeks':
            ban_end_time = datetime.now() + timedelta(weeks=time_value)

        ban_end_time_str = ban_end_time.strftime('%Y-%m-%d %H:%M:%S')

        # 袨斜薪芯胁谢褟械屑 褋褌邪褌褍褋 斜邪薪邪 懈 胁褉械屑褟 芯泻芯薪褔邪薪懈褟 胁 斜邪蟹械 写邪薪薪褘褏
        cursor.execute(
            "UPDATE users SET ban_status=1, ban_reason=?, ban_end_time=? WHERE user_id=?",
            (reason, ban_end_time_str, user_id_to_ban)
        )
        conn.commit()

        bot.send_message(message.chat.id,
                         f"袩芯谢褜蟹芯胁邪褌械谢褜 褋 ID {user_id_to_ban} 蟹邪斜邪薪械薪. 袩褉懈褔懈薪邪: {reason}. 袙褉械屑褟 芯泻芯薪褔邪薪懈褟 斜邪薪邪: {ban_end_time_str}.")

        # 袥芯谐懈褉芯胁邪薪懈械
        logger.info(
            f"袩芯谢褜蟹芯胁邪褌械谢褜 {user_id_to_ban} 蟹邪斜邪薪械薪. 袩褉懈褔懈薪邪: {reason}. 袙褉械屑褟 芯泻芯薪褔邪薪懈褟 斜邪薪邪: {ban_end_time_str}.")

    except Exception as e:
        bot.send_message(message.chat.id, f"袩褉芯懈蟹芯褕谢邪 芯褕懈斜泻邪 锌褉懈 斜邪薪械 锌芯谢褜蟹芯胁邪褌械谢褟: {str(e)}")
        # 袥芯谐懈褉芯胁邪薪懈械 芯褕懈斜泻懈
        logger.error(f"袨褕懈斜泻邪 锌褉懈 锌芯锌褘褌泻械 蟹邪斜邪薪懈褌褜 锌芯谢褜蟹芯胁邪褌械谢褟 {user_id_to_ban}: {str(e)}")


@bot.message_handler(commands=['unban'])
def unban_user(message):
    if message.from_user.id not in ADMIN_IDS2:
        bot.send_message(message.chat.id, "校 胁邪褋 薪械褌 锌褉邪胁 写谢褟 胁褘锌芯谢薪械薪懈褟 褝褌芯泄 泻芯屑邪薪写褘.")
        return

    bot.send_message(message.chat.id, "袙胁械写懈褌械 懈屑褟 锌芯谢褜蟹芯胁邪褌械谢褟, 泻芯褌芯褉芯谐芯 薪褍卸薪芯 褉邪蟹斜邪薪懈褌褜:")
    bot.register_next_step_handler(message, process_unban_by_name)


def process_unban_by_name(message):
    user_name_to_unban = message.text.strip()

    # 袠褖械屑 锌芯谢褜蟹芯胁邪褌械谢褟 胁 斜邪蟹械 写邪薪薪褘褏 锌芯 懈屑械薪懈
    cursor.execute("SELECT user_id, user_name, ban_status FROM users WHERE user_name=?", (user_name_to_unban,))
    user = cursor.fetchone()

    if not user:
        bot.send_message(message.chat.id, "袩芯谢褜蟹芯胁邪褌械谢褜 褋 褌邪泻懈屑 懈屑械薪械屑 薪械 薪邪泄写械薪.")
        return

    user_id_to_unban, user_name, ban_status = user

    # 袝褋谢懈 锌芯谢褜蟹芯胁邪褌械谢褜 薪械 蟹邪斜邪薪械薪, 褋芯芯斜褖邪械屑 芯斜 褝褌芯屑
    if ban_status == 0:
        bot.send_message(message.chat.id, f"袩芯谢褜蟹芯胁邪褌械谢褜 {user_name} 褍卸械 薪械 蟹邪斜邪薪械薪.")
        return

    # 小薪懈屑邪械屑 斜邪薪 褋 锌芯谢褜蟹芯胁邪褌械谢褟
    try:
        cursor.execute("UPDATE users SET ban_status=0, ban_reason=NULL, ban_end_time=NULL WHERE user_id=?", (user_id_to_unban,))
        conn.commit()
        bot.send_message(message.chat.id, f"袩芯谢褜蟹芯胁邪褌械谢褜 {user_name} 褉邪蟹斜邪薪械薪.")
    except Exception as e:
        bot.send_message(message.chat.id, f"袩褉芯懈蟹芯褕谢邪 芯褕懈斜泻邪 锌褉懈 褋薪褟褌懈懈 斜邪薪邪: {str(e)}")


if not os.path.exists(config.LOG_DIRECTORY):
    os.makedirs(config.LOG_DIRECTORY)

# 袧邪褋褌褉芯泄泻邪 谢芯谐懈褉芯胁邪薪懈褟
logging.basicConfig(
    level=logging.INFO,
    format=config.LOG_FORMAT
)
logger = logging.getLogger(__name__)

class SSHManager:
    def __init__(self):
        self.ssh_client = None
        self.lock = threading.Lock()
        self.connect()

    def connect(self):
        """校褋褌邪薪邪胁谢懈胁邪械褌 SSH 褋芯械写懈薪械薪懈械"""
        try:
            if self.ssh_client:
                try:
                    self.ssh_client.close()
                except:
                    pass

            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            max_attempts = 3
            attempt = 0
            retry_delay = 2
            
            while attempt < max_attempts:
                try:
                    ssh.connect(
                        hostname=config.SSH_HOST,
                        port=int(config.SSH_PORT),
                        username=config.SSH_USER,
                        password=config.SSH_PASSWORD,
                        timeout=config.SSH_TIMEOUT,
                        banner_timeout=60,
                        auth_timeout=30
                    )
                    self.ssh_client = ssh
                    logger.info("SSH 褋芯械写懈薪械薪懈械 褍褋褌邪薪芯胁谢械薪芯 褍褋锌械褕薪芯")
                    return True
                except paramiko.AuthenticationException:
                    logger.error(f"袨褕懈斜泻邪 邪褍褌械薪褌懈褎懈泻邪褑懈懈 SSH (锌芯锌褘褌泻邪 {attempt + 1}/{max_attempts})")
                    attempt += 1
                except paramiko.SSHException as ssh_error:
                    logger.error(f"SSH 芯褕懈斜泻邪 (锌芯锌褘褌泻邪 {attempt + 1}/{max_attempts}): {str(ssh_error)}")
                    attempt += 1
                except (socket.timeout, socket.error) as sock_error:
                    logger.error(f"小械褌械胁邪褟 芯褕懈斜泻邪 (锌芯锌褘褌泻邪 {attempt + 1}/{max_attempts}): {str(sock_error)}")
                    attempt += 1
                except Exception as e:
                    logger.error(f"袧械芯卸懈写邪薪薪邪褟 芯褕懈斜泻邪 SSH: {str(e)}")
                    break
                    
                if attempt < max_attempts:
                    time.sleep(retry_delay)
                    retry_delay *= 2
            
            return False
        except Exception as e:
            logger.error(f"袣褉懈褌懈褔械褋泻邪褟 芯褕懈斜泻邪 SSH 锌芯写泻谢褞褔械薪懈褟: {str(e)}")
            return False

    def execute_command(self, command):
        """袙褘锌芯谢薪褟械褌 SSH 泻芯屑邪薪写褍 褋 邪胁褌芯屑邪褌懈褔械褋泻懈屑 锌械褉械锌芯写泻谢褞褔械薪懈械屑 锌褉懈 薪械芯斜褏芯写懈屑芯褋褌懈"""
        with self.lock:
            try:
                if not self.ssh_client:
                    if not self.connect():
                        return None, None, None
                
                stdin, stdout, stderr = self.ssh_client.exec_command(command)
                return stdin, stdout, stderr
            except (paramiko.SSHException, socket.error) as e:
                logger.error(f"袨褕懈斜泻邪 胁褘锌芯谢薪械薪懈褟 SSH 泻芯屑邪薪写褘: {str(e)}")
                if self.connect():
                    return self.ssh_client.exec_command(command)
                return None, None, None
            except Exception as e:
                logger.error(f"袧械芯卸懈写邪薪薪邪褟 芯褕懈斜泻邪 锌褉懈 胁褘锌芯谢薪械薪懈懈 泻芯屑邪薪写褘: {str(e)}")
                return None, None, None

    def close(self):
        """袟邪泻褉褘胁邪械褌 SSH 褋芯械写懈薪械薪懈械"""
        if self.ssh_client:
            try:
                self.ssh_client.close()
            except:
                pass
            self.ssh_client = None

# 小芯蟹写邪薪懈械 谐谢芯斜邪谢褜薪芯谐芯 SSH 屑械薪械写卸械褉邪
ssh_manager = SSHManager()

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
        logger.info(f"小芯蟹写邪薪 薪芯胁褘泄 锌芯懈褋泻 褋 ID {search_id}")
        return search_id

    def add_player(self, search_id, player_data):
        user_id = str(player_data['user_id'])
        
        if user_id in self.player_searches:
            old_search_id = self.player_searches[user_id]
            if old_search_id != search_id:
                self.remove_player(user_id)
        
        if search_id in self.active_searches:
            if len(self.active_searches[search_id]['players']) >= config.MAX_PLAYERS:
                logger.warning(f"袛芯褋褌懈谐薪褍褌 屑邪泻褋懈屑褍屑 懈谐褉芯泻芯胁 胁 锌芯懈褋泻械 {search_id}")
                return False
                
            self.active_searches[search_id]['players'].append(player_data)
            self.player_searches[user_id] = search_id
            logger.info(f"袠谐褉芯泻 {user_id} 写芯斜邪胁谢械薪 胁 锌芯懈褋泻 {search_id}")
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
            
            logger.info(f"袠谐褉芯泻 {user_id} 褍写邪谢械薪 懈蟹 锌芯懈褋泻邪 {search_id}")
            
            if not self.active_searches[search_id]['players']:
                self.active_searches.pop(search_id, None)
                logger.info(f"袩芯懈褋泻 {search_id} 褍写邪谢械薪, 褌邪泻 泻邪泻 薪械 芯褋褌邪谢芯褋褜 懈谐褉芯泻芯胁")

    def is_player_in_search(self, user_id):
        is_in_search = str(user_id) in self.player_searches
        logger.info(f"袩褉芯胁械褉泻邪 懈谐褉芯泻邪 {user_id} 薪邪 邪泻褌懈胁薪褘泄 锌芯懈褋泻: {is_in_search}")
        return is_in_search

    def is_player_in_match(self, user_id):
        is_in_match = str(user_id) in self.player_active_matches
        logger.info(f"袩褉芯胁械褉泻邪 懈谐褉芯泻邪 {user_id} 薪邪 邪泻褌懈胁薪褘泄 屑邪褌褔: {is_in_match}")
        return is_in_match

    def add_player_to_match(self, user_id, screen_name):
        self.player_active_matches[str(user_id)] = screen_name
        logger.info(f"袠谐褉芯泻 {user_id} 写芯斜邪胁谢械薪 胁 屑邪褌褔 {screen_name}")

    def remove_player_from_match(self, user_id):
        user_id = str(user_id)
        if user_id in self.player_active_matches:
            screen_name = self.player_active_matches.pop(user_id)
            logger.info(f"袠谐褉芯泻 {user_id} 褍写邪谢械薪 懈蟹 屑邪褌褔邪 {screen_name}")

    def get_player_search(self, user_id):
        search_id = self.player_searches.get(str(user_id))
        return self.active_searches.get(search_id)

    def cleanup_inactive_matches(self):
        inactive_players = []
        
        for user_id, screen_name in self.player_active_matches.items():
            stdin, stdout, stderr = ssh_manager.execute_command(f"screen -ls | grep {screen_name}")
            if stdout and not stdout.read():
                inactive_players.append(user_id)

        for user_id in inactive_players:
            self.remove_player_from_match(user_id)
            logger.info(f"袨褔懈褖械薪 薪械邪泻褌懈胁薪褘泄 屑邪褌褔 写谢褟 懈谐褉芯泻邪 {user_id}")

# 小芯蟹写邪薪懈械 褝泻蟹械屑锌谢褟褉邪 SearchManager
search_manager = SearchManager()

def check_port_availability():
    """袩褉芯胁械褉褟械褌 写芯褋褌褍锌薪芯褋褌褜 锌芯褉褌芯胁"""
    try:
        available_ports = []
        for port in range(config.SERVER_START_PORT, config.SERVER_END_PORT + 1):
            stdin, stdout, stderr = ssh_manager.execute_command(f"netstat -tuln | grep :{port}")
            if stdout and not stdout.read():
                available_ports.append(port)

        return available_ports[0] if available_ports else None
    except Exception as e:
        logger.error(f"袨褕懈斜泻邪 锌褉芯胁械褉泻懈 锌芯褉褌芯胁: {e}")
        return None

def check_server_status(screen_name):
    """袩褉芯胁械褉褟械褌 褋褌邪褌褍褋 褋械褉胁械褉邪"""
    try:
        match_logger = logging.getLogger(screen_name)

        stdin, stdout, stderr = ssh_manager.execute_command(f"screen -ls | grep {screen_name}")
        if stdout:
            screen_status = stdout.read().decode('utf-8', errors='ignore')
            match_logger.debug(f"小褌邪褌褍褋 screen 褋械褋褋懈懈: {screen_status}")

            if not screen_status:
                match_logger.error("Screen 褋械褋褋懈褟 薪械 薪邪泄写械薪邪")
                return None

            # 袨褔懈褖邪械屑 锌褉械写褘写褍褖懈泄 褋褌邪褌褍褋
            ssh_manager.execute_command(f"rm -f /tmp/status_{screen_name}.txt")
            time.sleep(1)

            # 袨褌锌褉邪胁谢褟械屑 泻芯屑邪薪写褍 status 懈 卸写械屑 褉械蟹褍谢褜褌邪褌
            ssh_manager.execute_command(f"screen -S {screen_name} -X stuff 'status\\n'")
            time.sleep(10)

            # 小芯褏褉邪薪褟械屑 胁褘胁芯写
            ssh_manager.execute_command(f"screen -S {screen_name} -X hardcopy /tmp/status_{screen_name}.txt")
            time.sleep(2)

            # 效懈褌邪械屑 褋褌邪褌褍褋
            stdin, stdout, stderr = ssh_manager.execute_command(f"cat /tmp/status_{screen_name}.txt")
            if stdout:
                status_output = stdout.read().decode('utf-8', errors='ignore')
                match_logger.debug(f"袩芯谢薪褘泄 胁褘胁芯写 褋褌邪褌褍褋邪:\n{status_output}")

                # 袗薪邪谢懈蟹懈褉褍械屑 胁褘胁芯写
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
                                    match_logger.error(f"袨褕懈斜泻邪 锌褉懈 芯斜褉邪斜芯褌泻械 褋褌褉芯泻懈 懈谐褉芯泻邪: {line}. 袨褕懈斜泻邪: {e}")

                    if 'CT' in line and 'score' in line.lower():
                        try:
                            ct_score = int(line.split()[-1])
                        except Exception as e:
                            match_logger.error(f"袨褕懈斜泻邪 锌邪褉褋懈薪谐邪 CT score: {e}")
                    if 'TERRORIST' in line and 'score' in line.lower():
                        try:
                            t_score = int(line.split()[-1])
                        except Exception as e:
                            match_logger.error(f"袨褕懈斜泻邪 锌邪褉褋懈薪谐邪 T score: {e}")

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
        match_logger.error(f"袨褕懈斜泻邪 锌褉芯胁械褉泻懈 褋褌邪褌褍褋邪 褋械褉胁械褉邪: {e}")
        return None

def start_server(selected_map, server_password):
    """袟邪锌褍褋泻邪械褌 懈谐褉芯胁芯泄 褋械褉胁械褉"""
    try:
        port = check_port_availability()
        if not port:
            logger.error("袧械褌 褋胁芯斜芯写薪褘褏 锌芯褉褌芯胁")
            return None

        screen_name = f"server_{selected_map}_{port}_{int(time.time())}"
        match_logger = setup_match_logger(screen_name)
        match_logger.info(f"袟邪锌褍褋泻 褋械褉胁械褉邪: {screen_name}")

        # 袩褉芯胁械褉褟械屑 锌芯褉褌
        stdin, stdout, stderr = ssh_manager.execute_command(f"netstat -tuln | grep :{port}")
        if stdout and stdout.read():
            match_logger.error(f"袩芯褉褌 {port} 褍卸械 蟹邪薪褟褌")
            return None

        # 小芯蟹写邪械屑 泻芯薪褎懈谐 褋 锌邪褉芯谢械屑
        config_command = f"echo 'sv_password {server_password}' > {config.BASE_SERVER_PATH}/cfg/server_password.cfg"
        ssh_manager.execute_command(config_command)
        time.sleep(2)

        # 袟邪锌褍褋泻邪械屑 褋械褉胁械褉
        launch_command = (
            f"cd {config.BASE_SERVER_PATH} && "
            f"screen -dmS {screen_name} bash -c '"
            f"export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:./bin && "
            f"./dedicated_launcher -console +map {selected_map} "
            f"-maxplayers {config.MAX_PLAYERS} -port {port} "
            f"+sv_lan 0 -game cm -tickrate 100'"
        )

        ssh_manager.execute_command(launch_command)
        time.sleep(15)

        # 袩褉芯胁械褉褟械屑 蟹邪锌褍褋泻
        stdin, stdout, stderr = ssh_manager.execute_command(f"screen -ls | grep {screen_name}")
        if stdout and not stdout.read():
            match_logger.error("小械褉胁械褉 薪械 蟹邪锌褍褋褌懈谢褋褟")
            return None

        # 袧邪褋褌褉邪懈胁邪械屑 褋械褉胁械褉
        server_commands = [
            f"sv_password {server_password}",
            "mp_warmuptime 900",
            "mp_autoteambalance 0",
            "mp_limitteams 0",
            "mp_warmup_start"
        ]

        for cmd in server_commands:
            ssh_manager.execute_command(f"screen -S {screen_name} -X stuff '{cmd}\\n'")
            time.sleep(2)

        match_logger.info(f"小械褉胁械褉 褍褋锌械褕薪芯 蟹邪锌褍褖械薪 薪邪 锌芯褉褌褍 {port}")
        return screen_name, port

    except Exception as e:
        logger.error(f"袨褕懈斜泻邪 蟹邪锌褍褋泻邪 褋械褉胁械褉邪: {e}")
        return None
def setup_match_logger(screen_name):
    """小芯蟹写邪械褌 谢芯谐谐械褉 写谢褟 屑邪褌褔邪"""
    log_file = os.path.join(config.LOG_DIRECTORY, f"match_{screen_name}.log")
    match_logger = logging.getLogger(screen_name)
    match_logger.setLevel(logging.INFO)

    if not match_logger.handlers:
        handler = logging.FileHandler(log_file)
        handler.setFormatter(logging.Formatter(config.LOG_FORMAT))
        match_logger.addHandler(handler)

    return match_logger

def start_match(screen_name):
    """袟邪锌褍褋泻邪械褌 屑邪褌褔"""
    try:
        ssh_manager.execute_command(f"screen -S {screen_name} -X stuff 'mp_warmup_end\\n'")
        return True
    except Exception as e:
        logger.error(f"袨褕懈斜泻邪 蟹邪锌褍褋泻邪 屑邪褌褔邪: {e}")
        return False

def stop_server(screen_name):
    """袨褋褌邪薪邪胁谢懈胁邪械褌 褋械褉胁械褉"""
    try:
        match_logger = logging.getLogger(screen_name)
        match_logger.info("袨褋褌邪薪芯胁泻邪 褋械褉胁械褉邪")

        stdin, stdout, stderr = ssh_manager.execute_command(f"screen -ls | grep {screen_name}")
        if stdout and not stdout.read():
            match_logger.warning("Screen 褋械褋褋懈褟 薪械 薪邪泄写械薪邪")
            return True

        # 袨褌锌褉邪胁谢褟械屑 泻芯屑邪薪写褍 quit
        ssh_manager.execute_command(f"screen -S {screen_name} -X stuff 'quit\\n'")
        time.sleep(2)

        # 校斜懈胁邪械屑 screen 褋械褋褋懈褞
        ssh_manager.execute_command(f"screen -S {screen_name} -X quit")
        time.sleep(1)

        # 袩褉芯胁械褉褟械屑 蟹邪胁械褉褕械薪懈械
        stdin, stdout, stderr = ssh_manager.execute_command(f"screen -ls | grep {screen_name}")
        if stdout and stdout.read():
            ssh_manager.execute_command(f"pkill -f {screen_name}")
            time.sleep(1)

        # 袨褔懈褖邪械屑 胁褉械屑械薪薪褘械 褎邪泄谢褘
        ssh_manager.execute_command(f"rm -f /tmp/status_{screen_name}.txt")
        ssh_manager.execute_command(f"rm -f /tmp/match_start_{screen_name}.txt")

        match_logger.info("小械褉胁械褉 褍褋锌械褕薪芯 芯褋褌邪薪芯胁谢械薪")
        return True

    except Exception as e:
        logger.error(f"袨褕懈斜泻邪 芯褋褌邪薪芯胁泻懈 褋械褉胁械褉邪 {screen_name}: {e}")
        return False

def monitor_server(screen_name, player_ids):
    """袦芯薪懈褌芯褉懈褌 褋芯褋褌芯褟薪懈械 褋械褉胁械褉邪"""
    match_logger = setup_match_logger(screen_name)
    match_logger.info(f"袧邪褔邪谢芯 屑芯薪懈褌芯褉懈薪谐邪 褋械褉胁械褉邪 {screen_name}")
    match_logger.info(f"袠谐褉芯泻懈: {player_ids}")

    start_time = time.time()
    empty_server_checks = 0
    warned_times = set()
    match_started = False

    # 袛芯斜邪胁谢褟械屑 懈谐褉芯泻芯胁 胁 褋锌懈褋芯泻 邪泻褌懈胁薪褘褏 屑邪褌褔械泄
    for user_id in player_ids:
        search_manager.add_player_to_match(str(user_id), screen_name)

    try:
        while True:
            current_time = time.time()
            elapsed_time = current_time - start_time

            # 袩褉芯胁械褉褟械屑 胁褉械屑褟 写谢褟 芯褌锌褉邪胁泻懈 锌褉械写褍锌褉械卸写械薪懈泄
            if not match_started:
                for warning_time in config.WARNING_TIMES:
                    time_left = config.TOTAL_WAIT_TIME - elapsed_time
                    if time_left <= warning_time and warning_time not in warned_times:
                        minutes_left = int(warning_time / 60)
                        notify_time_warning(player_ids, minutes_left)
                        warned_times.add(warning_time)
                        match_logger.info(f"袨褌锌褉邪胁谢械薪芯 锌褉械写褍锌褉械卸写械薪懈械: {minutes_left} 屑懈薪褍褌 写芯 芯褌泻谢褞褔械薪懈褟")

                if elapsed_time >= config.TOTAL_WAIT_TIME and not match_started:
                    match_logger.info("袩褉械胁褘褕械薪芯 芯斜褖械械 胁褉械屑褟 芯卸懈写邪薪懈褟")
                    notify_timeout(player_ids)
                    break

            # 袩褉芯胁械褉褟械屑 褋褌邪褌褍褋 褋械褉胁械褉邪
            status = check_server_status(screen_name)
            if not status:
                match_logger.error("袧械 褍写邪谢芯褋褜 锌芯谢褍褔懈褌褜 褋褌邪褌褍褋 褋械褉胁械褉邪")
                notify_players_error(player_ids)
                break

            match_logger.info(f"小褌邪褌褍褋 褋械褉胁械褉邪: {status}")

            # 袩褉芯胁械褉泻邪 薪邪 蟹邪胁械褉褕械薪懈械 屑邪褌褔邪
            if status['game_ended'] and match_started:
                match_logger.info("袦邪褌褔 蟹邪胁械褉褕械薪")
                notify_match_end(player_ids, status['ct_score'], status['t_score'])
                break

            # 袩褉芯胁械褉泻邪 薪邪 锌褍褋褌芯泄 褋械褉胁械褉
            if status['active_players'] == 0:
                empty_server_checks += 1
                match_logger.warning(f"小械褉胁械褉 锌褍褋褌. 袩褉芯胁械褉泻邪 {empty_server_checks}/{config.MAX_EMPTY_CHECKS}")
                if empty_server_checks >= config.MAX_EMPTY_CHECKS:
                    match_logger.info("小械褉胁械褉 锌褍褋褌 斜芯谢械械 褍褋褌邪薪芯胁谢械薪薪芯谐芯 泻芯谢懈褔械褋褌胁邪 锌褉芯胁械褉芯泻")
                    notify_server_empty(player_ids)
                    break
            else:
                empty_server_checks = 0

            # 袗胁褌芯屑邪褌懈褔械褋泻懈泄 蟹邪锌褍褋泻 屑邪褌褔邪 锌褉懈 锌芯写泻谢褞褔械薪懈懈 胁褋械褏 懈谐褉芯泻芯胁
            if not match_started and status['active_players'] >= len(player_ids):
                match_logger.info("袙褋械 懈谐褉芯泻懈 锌芯写泻谢褞褔懈谢懈褋褜, 蟹邪锌褍褋泻邪械屑 屑邪褌褔")
                match_started = start_match(screen_name)
                if match_started:
                    notify_match_start(player_ids)

            time.sleep(5)

    except Exception as e:
        match_logger.error(f"袨褕懈斜泻邪 屑芯薪懈褌芯褉懈薪谐邪: {e}", exc_info=True)
        notify_players_error(player_ids)

    finally:
        # 袨褔懈褖邪械屑 懈薪褎芯褉屑邪褑懈褞 芯斜 邪泻褌懈胁薪芯屑 屑邪褌褔械
        for user_id in player_ids:
            search_manager.remove_player_from_match(str(user_id))

        # 袨褋褌邪薪邪胁谢懈胁邪械屑 褋械褉胁械褉
        stop_server(screen_name)
        match_logger.info("袟邪胁械褉褕械薪懈械 屑芯薪懈褌芯褉懈薪谐邪 褋械褉胁械褉邪")

def generate_random_password(length=8):
    """袚械薪械褉懈褉褍械褌 褋谢褍褔邪泄薪褘泄 锌邪褉芯谢褜"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def generate_status_message(search_id):
    """袚械薪械褉懈褉褍械褌 褋芯芯斜褖械薪懈械 芯 褋褌邪褌褍褋械 锌芯懈褋泻邪"""
    search_data = search_manager.active_searches.get(search_id)
    if search_data:
        count = len(search_data['players'])
        return (
            f"馃懃 袠写褢褌 锌芯写斜芯褉 懈谐褉芯泻芯胁:\n"
            f"馃懆鈥嶐煈� 袧邪泄写械薪芯: {count} 懈蟹 {config.MIN_PLAYERS_FOR_START} 鉁�"
        )
    return "馃懃 袩芯懈褋泻 薪械 邪泻褌懈胁械薪"

def search_keyboard():
    """小芯蟹写邪械褌 泻谢邪胁懈邪褌褍褉褍 写谢褟 锌芯懈褋泻邪"""
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("馃攳 袩芯懈褋泻", callback_data="start_search"))
    keyboard.add(InlineKeyboardButton("鉂� 袨褌屑械薪邪", callback_data="cancel_search"))
    return keyboard

def notify_match_start(player_ids):
    """校胁械写芯屑谢褟械褌 懈谐褉芯泻芯胁 芯 薪邪褔邪谢械 屑邪褌褔邪"""
    message = "馃幃 袦邪褌褔 薪邪褔邪谢褋褟! 校写邪褔薪芯泄 懈谐褉褘!"
    for user_id in player_ids:
        try:
            bot.send_message(chat_id=user_id, text=message)
        except Exception as e:
            logger.error(f"袨褕懈斜泻邪 芯褌锌褉邪胁泻懈 褍胁械写芯屑谢械薪懈褟 芯 薪邪褔邪谢械 屑邪褌褔邪 懈谐褉芯泻褍 {user_id}: {e}")

def notify_match_end(player_ids, ct_score, t_score):
    """校胁械写芯屑谢褟械褌 懈谐褉芯泻芯胁 芯 蟹邪胁械褉褕械薪懈懈 屑邪褌褔邪"""
    message = (
        f"馃弳 袠谐褉邪 蟹邪胁械褉褕械薪邪!\n\n"
        f"馃搳 肖懈薪邪谢褜薪褘泄 褋褔械褌:\n"
        f"馃數 CT: {ct_score}\n"
        f"馃敶 T: {t_score}\n\n"
        f"袧邪卸屑懈褌械 /search, 褔褌芯斜褘 薪邪褔邪褌褜 薪芯胁褘泄 锌芯懈褋泻!"
    )
    for user_id in player_ids:
        try:
            bot.send_message(chat_id=user_id, text=message)
        except Exception as e:
            logger.error(f"袨褕懈斜泻邪 芯褌锌褉邪胁泻懈 褍胁械写芯屑谢械薪懈褟 芯 蟹邪胁械褉褕械薪懈懈 屑邪褌褔邪 懈谐褉芯泻褍 {user_id}: {e}")

def notify_time_warning(player_ids, minutes_left):
    """袨褌锌褉邪胁谢褟械褌 锌褉械写褍锌褉械卸写械薪懈械 芯 胁褉械屑械薪懈 写芯 芯褌泻谢褞褔械薪懈褟 褋械褉胁械褉邪"""
    message = (
        f"鈿狅笍 袙薪懈屑邪薪懈械! 袛芯 芯褌泻谢褞褔械薪懈褟 褋械褉胁械褉邪 芯褋褌邪谢芯褋褜 {minutes_left} 屑懈薪褍褌!\n"
        f"袩芯卸邪谢褍泄褋褌邪, 锌芯写泻谢褞褔懈褌械褋褜 泻 褋械褉胁械褉褍, 懈薪邪褔械 芯薪 斜褍写械褌 芯褋褌邪薪芯胁谢械薪."
    )
    for user_id in player_ids:
        try:
            bot.send_message(chat_id=user_id, text=message)
        except Exception as e:
            logger.error(f"袨褕懈斜泻邪 芯褌锌褉邪胁泻懈 锌褉械写褍锌褉械卸写械薪懈褟 懈谐褉芯泻褍 {user_id}: {e}")

def notify_timeout(player_ids):
    """校胁械写芯屑谢褟械褌 懈谐褉芯泻芯胁 芯 锌褉械胁褘褕械薪懈懈 胁褉械屑械薪懈 芯卸懈写邪薪懈褟"""
    message = (
        "鈴� 袙褉械屑褟 芯卸懈写邪薪懈褟 懈褋褌械泻谢芯!\n"
        "袧械写芯褋褌邪褌芯褔薪芯 懈谐褉芯泻芯胁 锌芯写泻谢褞褔懈谢芯褋褜 泻 褋械褉胁械褉褍.\n\n"
        "袧邪卸屑懈褌械 /search, 褔褌芯斜褘 薪邪褔邪褌褜 薪芯胁褘泄 锌芯懈褋泻."
    )
    for user_id in player_ids:
        try:
            bot.send_message(chat_id=user_id, text=message)
        except Exception as e:
            logger.error(f"袨褕懈斜泻邪 芯褌锌褉邪胁泻懈 褍胁械写芯屑谢械薪懈褟 芯 褌邪泄屑邪褍褌械 懈谐褉芯泻褍 {user_id}: {e}")

def notify_server_empty(player_ids):
    """校胁械写芯屑谢褟械褌 懈谐褉芯泻芯胁 芯 锌褍褋褌芯屑 褋械褉胁械褉械"""
    message = (
        "鈿狅笍 小械褉胁械褉 锌褍褋褌!\n"
        "小械褉胁械褉 斜褘谢 芯褋褌邪薪芯胁谢械薪 懈蟹-蟹邪 芯褌褋褍褌褋褌胁懈褟 懈谐褉芯泻芯胁.\n\n"
        "袧邪卸屑懈褌械 /search, 褔褌芯斜褘 薪邪褔邪褌褜 薪芯胁褘泄 锌芯懈褋泻."
    )
    for user_id in player_ids:
        try:
            bot.send_message(chat_id=user_id, text=message)
        except Exception as e:
            logger.error(f"袨褕懈斜泻邪 芯褌锌褉邪胁泻懈 褍胁械写芯屑谢械薪懈褟 芯 锌褍褋褌芯屑 褋械褉胁械褉械 懈谐褉芯泻褍 {user_id}: {e}")

def notify_players_error(player_ids):
    """校胁械写芯屑谢褟械褌 懈谐褉芯泻芯胁 芯斜 芯褕懈斜泻械"""
    message = (
        "鈿狅笍 袩褉芯懈蟹芯褕谢邪 芯褕懈斜泻邪 薪邪 褋械褉胁械褉械!\n"
        "小械褉胁械褉 斜褘谢 芯褋褌邪薪芯胁谢械薪.\n\n"
        "袧邪卸屑懈褌械 /search, 褔褌芯斜褘 薪邪褔邪褌褜 薪芯胁褘泄 锌芯懈褋泻 懈谐褉褘."
    )
    for user_id in player_ids:
        try:
            bot.send_message(chat_id=user_id, text=message)
        except Exception as e:
            logger.error(f"袨褕懈斜泻邪 芯褌锌褉邪胁泻懈 褍胁械写芯屑谢械薪懈褟 芯斜 芯褕懈斜泻械 懈谐褉芯泻褍 {user_id}: {e}")

@bot.message_handler(commands=['search'])
def handle_search(message):
    """袨斜褉邪斜芯褌泻邪 泻芯屑邪薪写褘 /search"""
    user_id = str(message.from_user.id)
    logger.info(f"袩芯谢褍褔械薪邪 泻芯屑邪薪写邪 /search 芯褌 锌芯谢褜蟹芯胁邪褌械谢褟 {user_id}")

    if search_manager.is_player_in_search(user_id):
        bot.send_message(
            message.chat.id,
            "馃懃 袙褘 褍卸械 胁 锌芯懈褋泻械. 袠褋锌芯谢褜蟹褍泄褌械 泻薪芯锌泻褍 芯褌屑械薪褘, 褔褌芯斜褘 胁褘泄褌懈 懈蟹 褌械泻褍褖械谐芯 锌芯懈褋泻邪."
        )
        return

    # 袩芯懈褋泻 邪泻褌懈胁薪芯谐芯 薪械蟹邪锌芯谢薪械薪薪芯谐芯 锌芯懈褋泻邪
    active_search_id = None
    for search_id, search_data in search_manager.active_searches.items():
        if len(search_data['players']) < config.MAX_PLAYERS:
            active_search_id = search_id
            break

    player_data = {
        'user_id': user_id,
        'name': message.from_user.first_name
    }

    if active_search_id is not None:
        if search_manager.add_player(active_search_id, player_data):
            msg = bot.send_message(
                message.chat.id,
                generate_status_message(active_search_id),
                reply_markup=search_keyboard()
            )
            search_manager.active_searches[active_search_id]['messages'][user_id] = msg
            update_all_players(active_search_id)
        else:
            bot.send_message(message.chat.id, "鈿狅笍 袧械 褍写邪谢芯褋褜 锌褉懈褋芯械写懈薪懈褌褜褋褟 泻 锌芯懈褋泻褍.")
        return

    # 小芯蟹写邪械屑 薪芯胁褘泄 锌芯懈褋泻
    new_search_id = search_manager.create_new_search()
    if search_manager.add_player(new_search_id, player_data):
        msg = bot.send_message(
            message.chat.id,
            generate_status_message(new_search_id),
            reply_markup=search_keyboard()
        )
        search_manager.active_searches[new_search_id]['messages'][user_id] = msg
    else:
        bot.send_message(message.chat.id, "鈿狅笍 袧械 褍写邪谢芯褋褜 褋芯蟹写邪褌褜 薪芯胁褘泄 锌芯懈褋泻.")

@bot.callback_query_handler(func=lambda call: call.data == "start_search")
def handle_start_search(call):
    user_id = str(call.from_user.id)
    search_id = search_manager.player_searches.get(user_id)
    
    if not search_id:
        bot.answer_callback_query(call.id, "鉂� 袩芯懈褋泻 薪械 薪邪泄写械薪.")
        return

    search_data = search_manager.active_searches.get(search_id)
    if not search_data or len(search_data['players']) < config.MIN_PLAYERS_FOR_START:
        bot.answer_callback_query(call.id, "鈿狅笍 袧械写芯褋褌邪褌芯褔薪芯 懈谐褉芯泻芯胁 写谢褟 褋褌邪褉褌邪!")
        return

    finish_search(search_id)
    bot.answer_callback_query(call.id, "鉁� 袟邪锌褍褋泻邪械屑 屑邪褌褔!")

@bot.callback_query_handler(func=lambda call: call.data == "cancel_search")
def handle_cancel_search(call):
    try:
        user_id = str(call.from_user.id)
        search_manager.remove_player(user_id)
        
        try:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="鉂� 袩芯懈褋泻 芯褌屑械薪械薪."
            )
        except apihelper.ApiException as api_error:
            if "query is too old" in str(api_error):
                bot.send_message(call.message.chat.id, "鉂� 袩芯懈褋泻 芯褌屑械薪械薪.")
            else:
                raise
                
        bot.answer_callback_query(call.id)
        
    except Exception as e:
        logger.error(f"袨褕懈斜泻邪 锌褉懈 芯褌屑械薪械 锌芯懈褋泻邪 写谢褟 懈谐褉芯泻邪 {user_id}: {e}")
        try:
            bot.send_message(call.message.chat.id, "鉂� 袩芯懈褋泻 芯褌屑械薪械薪.")
        except:
            pass

def update_all_players(search_id):
    """袨斜薪芯胁谢褟械褌 褋芯芯斜褖械薪懈褟 胁褋械褏 懈谐褉芯泻芯胁 胁 锌芯懈褋泻械 懈 锌褉芯胁械褉褟械褌 谐芯褌芯胁薪芯褋褌褜"""
    search_data = search_manager.active_searches.get(search_id)
    if not search_data:
        return

    messages_copy = dict(search_data['messages'])
    new_status_message = generate_status_message(search_id)
    
    for user_id, msg in messages_copy.items():
        try:
            if msg and msg.text != new_status_message:
                try:
                    bot.edit_message_text(
                        chat_id=msg.chat.id,
                        message_id=msg.message_id,
                        text=new_status_message,
                        reply_markup=search_keyboard()
                    )
                except apihelper.ApiException as e:
                    if "message is not modified" not in str(e):
                        logger.error(f"袨褕懈斜泻邪 API Telegram 写谢褟 懈谐褉芯泻邪 {user_id}: {e}")
        except Exception as e:
            logger.error(f"袨褕懈斜泻邪 芯斜薪芯胁谢械薪懈褟 褋芯芯斜褖械薪懈褟 懈谐褉芯泻邪 {user_id}: {e}")
            if search_id in search_manager.active_searches:
                search_manager.active_searches[search_id]['messages'].pop(user_id, None)

    # 袩褉芯胁械褉褟械屑 褍褋谢芯胁懈褟 写谢褟 蟹邪锌褍褋泻邪 屑邪褌褔邪
    if search_id in search_manager.active_searches:
        current_players = len(search_data['players'])
        if current_players >= config.MIN_PLAYERS_FOR_START:
            finish_search(search_id)

def finish_search(search_id):
    """袟邪胁械褉褕邪械褌 锌芯懈褋泻 懈 蟹邪锌褍褋泻邪械褌 褋械褉胁械褉"""
    search_data = search_manager.active_searches.get(search_id)
    if not search_data or len(search_data['players']) < config.MIN_PLAYERS_FOR_START:
        logger.error(f"袩芯懈褋泻 {search_id} 薪械 屑芯卸械褌 斜褘褌褜 蟹邪胁械褉褕械薪: 薪械写芯褋褌邪褌芯褔薪芯 懈谐褉芯泻芯胁")
        return

    messages_copy = dict(search_data['messages'])
    players_copy = list(search_data['players'])

    selected_map = random.choice(config.MAPS)
    server_password = generate_random_password()

    server_info = start_server(selected_map, server_password)
    if not server_info:
        for user_id, msg in messages_copy.items():
            try:
                bot.send_message(
                    msg.chat.id,
                    "鈿狅笍 袨褕懈斜泻邪 褋芯蟹写邪薪懈褟 褋械褉胁械褉邪. 袩芯锌褉芯斜褍泄褌械 锌芯蟹卸械."
                )
            except Exception as e:
                logger.error(f"袨褕懈斜泻邪 芯褌锌褉邪胁泻懈 褋芯芯斜褖械薪懈褟 芯斜 芯褕懈斜泻械 懈谐褉芯泻褍 {user_id}: {e}")
        return

    screen_name, port = server_info

    # 肖芯褉屑懈褉褍械屑 泻芯屑邪薪写褘
    random.shuffle(players_copy)
    ct_players = [p['name'] for i, p in enumerate(players_copy) if i % 2 == 0]
    t_players = [p['name'] for i, p in enumerate(players_copy) if i % 2 != 0]

    server_message = (
        f"馃幃 小械褉胁械褉 褋芯蟹写邪薪!\n\n"
        f"馃數 Counter-Terrorist:\n{chr(10).join(ct_players)}\n\n"
        f"馃敶 Terrorist:\n{chr(10).join(t_players)}\n\n"
        f"馃椇 袣邪褉褌邪: {selected_map}\n\n"
        f"馃攼 袩邪褉芯谢褜: {server_password}\n"
        f"馃寪 IP: {config.SERVER_IP}:{port}\n\n"
        f"馃摑 袣芯屑邪薪写邪 写谢褟 泻芯薪褋芯谢懈:\n"
        f"connect {config.SERVER_IP}:{port}; password {server_password}"
    )

    player_ids = [int(player['user_id']) for player in players_copy]

    # 袨褌锌褉邪胁谢褟械屑 褋芯芯斜褖械薪懈褟
    for user_id, msg in messages_copy.items():
        try:
            bot.send_message(msg.chat.id, server_message)
        except Exception as e:
            logger.error(f"袨褕懈斜泻邪 芯褌锌褉邪胁泻懈 褋芯芯斜褖械薪懈褟 懈谐褉芯泻褍 {user_id}: {e}")

    # 袟邪锌褍褋泻邪械屑 屑芯薪懈褌芯褉懈薪谐 褋械褉胁械褉邪
    threading.Thread(
        target=monitor_server,
        args=(screen_name, player_ids),
        daemon=True
    ).start()

    # 袨褔懈褖邪械屑 写邪薪薪褘械 锌芯懈褋泻邪
    if search_id in search_manager.active_searches:
        for player in players_copy:
            search_manager.player_searches.pop(str(player['user_id']), None)
        search_manager.active_searches.pop(search_id, None)

# 袟邪锌褍褋泻 斜芯褌邪
if __name__ == "__main__":
    logger.info("袘芯褌 蟹邪锌褍褖械薪")
    last_cleanup = time.time()
    
    while True:
        try:
            current_time = time.time()
            if current_time - last_cleanup > 300:  # 袣邪卸写褘械 5 屑懈薪褍褌
                search_manager.cleanup_inactive_matches()
                last_cleanup = current_time
                
            bot.polling(none_stop=True, interval=1, timeout=30)
            
        except apihelper.ApiException as api_error:
            logger.error(f"Telegram API 芯褕懈斜泻邪: {str(api_error)}")
            time.sleep(5)
            
        except requests.exceptions.RequestException as req_error:
            logger.error(f"袨褕懈斜泻邪 褋械褌懈: {str(req_error)}")
            time.sleep(15)
            
        except Exception as e:
            logger.error(f"袣褉懈褌懈褔械褋泻邪褟 芯褕懈斜泻邪 胁 褉邪斜芯褌械 斜芯褌邪: {str(e)}", exc_info=True)
            time.sleep(30)

if __name__ == "__main__":
    try:
        print("袘芯褌 蟹邪锌褍褖械薪...")
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"袨褕懈斜泻邪: {e}")
        logging.error(f"袣褉懈褌懈褔械褋泻邪褟 芯褕懈斜泻邪: {e}")
