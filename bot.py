import sqlite3
import random
import asyncio
from flask import Flask, request, jsonify
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

API_TOKEN = '8841461685:AAEq6sl4NFTJpgbEe-wlnOt_unotiZyo8YA'
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

app = Flask(__name__)

# Инициализация базы данных SQLite
def init_db():
    conn = sqlite3.connect('raidgram.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            phone TEXT UNIQUE,
            auth_code TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- КЛАВИАТУРЫ БОТА ---
def main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Купить номер (+888)", callback_data="buy_888")],
        [InlineKeyboardButton(text="🆓 Получить бесплатный номер", callback_data="get_free")]
    ])

def country_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇺🇦 +380", callback_data="country_380"),
            InlineKeyboardButton(text="🏳️ +7", callback_data="country_7")
        ]
    ])

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    conn = sqlite3.connect('raidgram.db')
    cursor = conn.cursor()
    cursor.execute("SELECT phone FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        await message.reply(
            f"⚠️ **У вас уже есть привязанный номер!**\n\n📱 `{row[0]}`\n\nПовторная выдача номеров запрещена.",
            parse_mode="Markdown"
        )
    else:
        await message.reply(
            "👋 **Добро пожаловать в бота авторизации RaidGram!**\n\nВыберите способ получения номера:",
            reply_markup=main_keyboard(),
            parse_mode="Markdown"
        )

@dp.callback_query(lambda c: c.data in ['buy_888', 'get_free'])
async def process_menu(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    conn = sqlite3.connect('raidgram.db')
    cursor = conn.cursor()
    cursor.execute("SELECT phone FROM users WHERE user_id = ?", (user_id,))
    if cursor.fetchone():
        conn.close()
        await callback.answer("У вас уже есть номер!", show_alert=True)
        return

    if callback.data == 'buy_888':
        phone = f"+888 {random.randint(100, 999)} {random.randint(10, 99)} {random.randint(10, 99)}"
        cursor.execute("INSERT INTO users (user_id, phone) VALUES (?, ?)", (user_id, phone))
        conn.commit()
        conn.close()
        await callback.message.edit_text(f"🎉 **Ваш анонимный номер (+888):**\n\n`{phone}`\n\nВведите его в приложении.", parse_mode="Markdown")
    else:
        conn.close()
        await callback.message.edit_text("Выберите страну:", reply_markup=country_keyboard())

@dp.callback_query(lambda c: c.data.startswith('country_'))
async def process_country(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    conn = sqlite3.connect('raidgram.db')
    cursor = conn.cursor()
    cursor.execute("SELECT phone FROM users WHERE user_id = ?", (user_id,))
    if cursor.fetchone():
        conn.close()
        await callback.answer("У вас уже есть номер!", show_alert=True)
        return

    if callback.data == 'country_380':
        phone = f"+380 {random.choice([67, 96, 50, 63, 73])} {random.randint(100,999)} {random.randint(10,99)} {random.randint(10,99)}"
    else:
        phone = f"+7 {random.choice([900, 911, 922, 999])} {random.randint(100,999)} {random.randint(10,99)} {random.randint(10,99)}"

    cursor.execute("INSERT INTO users (user_id, phone) VALUES (?, ?)", (user_id, phone))
    conn.commit()
    conn.close()

    await callback.message.edit_text(f"✅ **Ваш номер:**\n\n`{phone}`\n\nВведите его в приложении для входа.", parse_mode="Markdown")


# --- API ДЛЯ СВЯЗИ С ВЕБ-ПРИЛОЖЕНИЕМ ---

@app.route('/api/send_code', methods=['POST'])
def api_send_code():
    data = request.json
    phone = data.get('phone')

    conn = sqlite3.connect('raidgram.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE phone = ?", (phone,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return jsonify({'success': False, 'error': 'Номер не найден в базе бота! Сначала получите его в Telegram.'})

    user_id = row[0]
    code = str(random.randint(10000, 99999))

    cursor.execute("UPDATE users SET auth_code = ? WHERE user_id = ?", (code, user_id))
    conn.commit()
    conn.close()

    # Отправляем код пользователю в Telegram асинхронно
    asyncio.run(bot.send_message(user_id, f"🔑 Ваш код подтверждения для входа в RaidGram: *{code}*", parse_mode="Markdown"))

    return jsonify({'success': True})

@app.route('/api/verify_code', methods=['POST'])
def api_verify_code():
    data = request.json
    phone = data.get('phone')
    code = data.get('code')

    conn = sqlite3.connect('raidgram.db')
    cursor = conn.cursor()
    cursor.execute("SELECT auth_code FROM users WHERE phone = ?", (phone,))
    row = cursor.fetchone()
    conn.close()

    if row and row[0] == code:
        return jsonify({'success': True})
    
    return jsonify({'success': False})


if __name__ == '__main__':
    import threading
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5000)).start()
    
    # Запуск бота на aiogram 3
    async def main():
        await dp.start_polling(bot)

    asyncio.run(main())
