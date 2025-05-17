
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
from datetime import datetime
from config import BOT_TOKEN, ADMIN_ID

# Инициализация бота для админ-панели
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Проверка на администратора
def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

# Команда для входа в админ-панель
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")],
        [InlineKeyboardButton(text="⚙️ Управление", callback_data="admin_manage")]
    ])
    
    await message.answer(
        "🔐 *Админ\\-панель*\n"
        "Выберите действие:",
        parse_mode="MarkdownV2",
        reply_markup=keyboard
    )

# Обработчики callback_query
@dp.callback_query(lambda c: c.data.startswith("admin_"))
async def process_admin_callback(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    action = callback.data.split("_")[1]
    
    if action == "stats":
        await show_stats(callback)
    elif action == "users":
        await show_users(callback)
    elif action == "manage":
        await show_management(callback)
    
    await callback.answer()

async def show_stats(callback: types.CallbackQuery):
    # Здесь будет логика отображения статистики
    pass

async def show_users(callback: types.CallbackQuery):
    # Здесь будет логика отображения пользователей
    pass

async def show_management(callback: types.CallbackQuery):
    # Здесь будет логика управления ботом
    pass

# Запуск админ-панели
async def start_admin_panel():
    await dp.start_polling(bot)

if __name__ == '__main__':
    import asyncio
    asyncio.run(start_admin_panel())