import sqlite3
import random
import asyncio
import urllib.request
import json as json_lib
from flask import Flask, request, jsonify
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

# Твой токен бота
API_TOKEN = '8841461685:AAEq6sl4NFTJpgbEe-wlnOt_unotiZyo8YA'

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

app = Flask(__name__)

# Твой юзернейм, для которого разрешено много номеров
SPECIAL_USERNAME = "Vapito"

# Инициализация базы данных SQLite
def init_db():
    conn = sqlite3.connect('raidgram.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
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
        ],
        [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_menu")]
    ])

def back_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_menu")]
    ])

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    
    conn = sqlite3.connect('raidgram.db')
    cursor = conn.cursor()
    
    # Если пользователь не Vapito, проверяем есть ли у него уже номер
    if username != SPECIAL_USERNAME:
        cursor.execute("SELECT phone FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            conn.close()
            await message.reply(
                f"⚠️ **У вас уже есть привязанный номер!**\n\n📱 `{row[0]}`\n\nПовторная выдача ограничена.",
                reply_markup=back_keyboard(),
                parse_mode="Markdown"
            )
            return

    conn.close()
    await message.reply(
        "👋 **Добро пожаловать в бота авторизации RaidGram!**\n\nВыберите способ получения номера:",
        reply_markup=main_keyboard(),
        parse_mode="Markdown"
    )

@dp.callback_query(lambda c: c.data == 'back_to_menu')
async def process_back(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "👋 **Главное меню RaidGram:**\n\nВыберите способ получения номера:",
        reply_markup=main_keyboard(),
        parse_mode="Markdown"
    )

@dp.callback_query(lambda c: c.data in ['buy_888', 'get_free'])
async def process_menu(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    username = callback.from_user.username or "no_username"
    
    conn = sqlite3.connect('raidgram.db')
    cursor = conn.cursor()

    if username != SPECIAL_USERNAME:
        cursor.execute("SELECT phone FROM users WHERE user_id = ?", (user_id,))
        if cursor.fetchone():
            conn.close()
            await callback.answer("У вас уже есть номер!", show_alert=True)
            return

    if callback.data == 'buy_888':
        phone = f"+888 {random.randint(100, 999)} {random.randint(10, 99)} {random.randint(10, 99)}"
        cursor.execute("INSERT INTO users (user_id, username, phone) VALUES (?, ?, ?)", (user_id, username, phone))
        conn.commit()
        conn.close()
        await callback.message.edit_text(f"🎉 **Ваш анонимный номер (+888):**\n\n`{phone}`\n\nВведите его в приложении.", reply_markup=back_keyboard(), parse_mode="Markdown")
    else:
        conn.close()
        await callback.message.edit_text("Выберите страну:", reply_markup=country_keyboard())

@dp.callback_query(lambda c: c.data.startswith('country_'))
async def process_country(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    username = callback.from_user.username or "no_username"
    conn = sqlite3.connect('raidgram.db')
    cursor = conn.cursor()

    if username != SPECIAL_USERNAME:
        cursor.execute("SELECT phone FROM users WHERE user_id = ?", (user_id,))
        if cursor.fetchone():
            conn.close()
            await callback.answer("У вас уже есть номер!", show_alert=True)
            return

    if callback.data == 'country_380':
        phone = f"+380 {random.choice([67, 96, 50, 63, 73])} {random.randint(100,999)} {random.randint(10,99)} {random.randint(10,99)}"
    else:
        phone = f"+7 {random.choice([900, 911, 922, 999])} {random.randint(100,999)} {random.randint(10,99)} {random.randint(10,99)}"

    cursor.execute("INSERT INTO users (user_id, username, phone) VALUES (?, ?, ?)", (user_id, username, phone))
    conn.commit()
    conn.close()

    await callback.message.edit_text(f"✅ **Ваш номер:**\n\n`{phone}`\n\nВведите его в приложении для входа.", reply_markup=back_keyboard(), parse_mode="Markdown")


# --- API ДЛЯ СВЯЗИ С ВЕБ-ПРИЛОЖЕНИЕМ ---

@app.route('/api/send_code', methods=['POST'])
def api_send_code():
    data = request.json or {}
    phone = data.get('phone')

    if not phone:
        return jsonify({'success': False, 'error': 'Номер не указан!'})

    conn = sqlite3.connect('raidgram.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE phone = ?", (phone,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return jsonify({'success': False, 'error': 'Номер не найден в базе бота! Сначала получите его в Telegram.'})

    user_id = row[0]
    # Генерируем честный 5-значный код
    code = str(random.randint(10000, 99999))

    # Сохраняем код в базу для этого номера
    cursor.execute("UPDATE users SET auth_code = ? WHERE phone = ?", (code, phone))
    conn.commit()
    conn.close()

    # Отправляем сообщение в Telegram напрямую через HTTP API Telegram (без лагов asyncio)
    try:
        url = f"https://api.telegram.org/bot{API_TOKEN}/sendMessage"
        payload = {
            'chat_id': user_id,
            'text': f"🔑 Ваш код подтверждения для входа в RaidGram: *{code}*",
            'parse_mode': 'Markdown'
        }
        data_bytes = json_lib.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data_bytes, headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        return jsonify({'success': False, 'error': f'Ошибка отправки в Telegram: {str(e)}'})

    return jsonify({'success': True})

@app.route('/api/verify_code', methods=['POST'])
def api_verify_code():
    data = request.json or {}
    phone = data.get('phone')
    code = str(data.get('code', '')).strip()

    if not phone or not code:
        return jsonify({'success': False, 'error': 'Заполните все поля!'})

    conn = sqlite3.connect('raidgram.db')
    cursor = conn.cursor()
    cursor.execute("SELECT auth_code FROM users WHERE phone = ?", (phone,))
    row = cursor.fetchone()
    
    # Строго проверяем совпадение кода из базы
    if row and row[0] is not None and str(row[0]).strip() == code:
        # Очищаем код после успешного входа, чтобы повторно его использовать нельзя было
        cursor.execute("UPDATE users SET auth_code = NULL WHERE phone = ?", (phone,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    conn.close()
    return jsonify({'success': False, 'error': 'Неверный код подтверждения!'})


if __name__ == '__main__':
    import threading
    # Запускаем Flask в отдельном потоке
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5000), daemon=True).start()
    
    # Запуск бота на aiogram 3
    async def main():
        await dp.start_polling(bot)

    asyncio.run(main())
