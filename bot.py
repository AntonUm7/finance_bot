import os
import sqlite3
from datetime import datetime
from io import BytesIO
import time

import telebot
from telebot import types
from dotenv import load_dotenv
import matplotlib.pyplot as plt

# ------------------------
# 1. Завантаження токена
# ------------------------
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
print(f"DEBUG: BOT_TOKEN length = {len(BOT_TOKEN) if BOT_TOKEN else 0}")

if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN not found! Check Railway Variables!")
    exit(1)

print("✅ Token OK, starting bot...")
bot = telebot.TeleBot(BOT_TOKEN)

# ------------------------
# 2. База даних SQLite
# ------------------------
conn = sqlite3.connect('finances.db', check_same_thread=False)
cur = conn.cursor()

cur.execute('''
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        date TEXT,
        amount REAL,
        category TEXT,
        description TEXT
    )
''')
conn.commit()


# ------------------------
# 3. Допоміжні функції
# ------------------------
def main_reply_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_add = types.KeyboardButton("➕ Додати витрату")
    btn_report = types.KeyboardButton("📊 Звіт")
    btn_last = types.KeyboardButton("🧾 Остання витрата")
    btn_chart = types.KeyboardButton("📈 Графік")
    keyboard.add(btn_add, btn_report, btn_last, btn_chart)
    return keyboard


def try_parse_quick_expense(text: str):
    parts = text.split()
    if len(parts) < 2:
        return None
    try:
        amount = float(parts[0].replace(",", "."))
    except ValueError:
        return None
    category = parts[1]
    description = " ".join(parts[2:]) if len(parts) > 2 else ""
    return amount, category, description


def save_expense(user_id, amount, category, description=""):
    now = datetime.now()
    date_str = now.strftime('%Y-%m-%d')
    cur.execute('''
        INSERT INTO transactions (user_id, date, amount, category, description)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, date_str, amount, category, description))
    conn.commit()


# ------------------------
# 4. /start
# ------------------------
@bot.message_handler(commands=['start'])
def start(message):
    text = (
        "Привіт! Я твій фінансовий асистент 💸\n\n"
        "Я можу:\n"
        "• зберігати витрати\n"
        "• показувати звіти\n"
        "• будувати графіки\n\n"
        "Користуйся кнопками нижче!\n\n"
        "Швидке додавання: просто напиши\n"
        "`150 food супермаркет`"
    )
    bot.send_message(message.chat.id, text, reply_markup=main_reply_keyboard(), parse_mode='Markdown')


# ------------------------
# 5. Діалог додавання витрати (від кнопки ➕)
# ------------------------
@bot.message_handler(func=lambda m: m.text == "➕ Додати витрату")
def add_expense_wizard_start(message):
    msg = bot.send_message(message.chat.id, "💰 Введи суму (тільки число, напр. 150.5):")
    bot.register_next_step_handler(msg, add_expense_get_amount)


def add_expense_get_amount(message):
    try:
        amount = float(message.text.replace(",", "."))
    except ValueError:
        msg = bot.send_message(message.chat.id, "❌ Не число. Спробуй ще раз:")
        bot.register_next_step_handler(msg, add_expense_get_amount)
        return

    msg = bot.send_message(message.chat.id, "📂 Введи категорію (food, transport, fun):")
    bot.register_next_step_handler(msg, add_expense_get_category, amount)


def add_expense_get_category(message, amount):
    category = message.text.strip()
    msg = bot.send_message(message.chat.id, "📝 Опис (або '-' без опису):")
    bot.register_next_step_handler(msg, add_expense_finish, amount, category)


def add_expense_finish(message, amount, category):
    description = message.text.strip()
    if description == "-":
        description = ""

    save_expense(message.from_user.id, amount, category, description)
    bot.reply_to(
        message,
        f"✅ Додано: {amount} грн ({category})\n"
        f"Опис: {description or 'немає'}",
        reply_markup=main_reply_keyboard()
    )


# ------------------------
# 6. /add (команда)
# ------------------------
@bot.message_handler(commands=['add'])
def add_expense_command(message):
    parts = message.text.split()[1:]
    if len(parts) < 2:
        bot.reply_to(message, "Формат: /add 150 food супермаркет", reply_markup=main_reply_keyboard())
        return

    try:
        amount = float(parts[0].replace(",", "."))
        category = parts[1]
        description = " ".join(parts[2:]) if len(parts) > 2 else ""
        save_expense(message.from_user.id, amount, category, description)
        bot.reply_to(
            message,
            f"✅ Додано: {amount} грн ({category})\n"
            f"Опис: {description or 'немає'}",
            reply_markup=main_reply_keyboard()
        )
    except ValueError:
        bot.reply_to(message, "❌ Некоректна сума", reply_markup=main_reply_keyboard())


# ------------------------
# 7. /report
# ------------------------
@bot.message_handler(commands=['report'])
def report(message):
    user_id = message.from_user.id
    today = datetime.now().strftime('%Y-%m-%d')
    month_prefix = datetime.now().strftime('%Y-%m')

    cur.execute('SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE user_id = ? AND date = ?', (user_id, today))
    today_sum = cur.fetchone()[0]

    cur.execute('SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE user_id = ? AND date LIKE ?',
                (user_id, month_prefix + '%'))
    month_sum = cur.fetchone()[0]

    cur.execute('''
        SELECT category, SUM(amount) as total
        FROM transactions WHERE user_id = ? AND date LIKE ?
        GROUP BY category ORDER BY total DESC LIMIT 5
    ''', (user_id, month_prefix + '%'))
    rows = cur.fetchall()

    categories_text = "\n".join([f"• {cat}: {total:.0f} грн" for cat, total in rows]) if rows else "немає"

    text = (
        f"📊 Звіт\n\n"
        f"Сьогодні: {today_sum:.0f} грн\n"
        f"Місяць: {month_sum:.0f} грн\n\n"
        f"Топ категорій:\n{categories_text}"
    )
    bot.reply_to(message, text, reply_markup=main_reply_keyboard())


# ------------------------
# 8. Остання витрата
# ------------------------
@bot.message_handler(commands=['last'])
def last_transaction(message):
    user_id = message.from_user.id
    cur.execute('''
        SELECT id, date, amount, category, description
        FROM transactions WHERE user_id = ? ORDER BY id DESC LIMIT 1
    ''', (user_id,))
    row = cur.fetchone()

    if not row:
        bot.reply_to(message, "📭 Витрат ще немає", reply_markup=main_reply_keyboard())
        return

    tr_id, date, amount, category, desc = row
    text = f"🧾 Остання:\n{amount} грн • {category}\n{date}\n\n{desc or 'без опису'}"

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton("✏️ Змінити", callback_data=f"edit:{tr_id}"),
        types.InlineKeyboardButton("🗑 Видалити", callback_data=f"del:{tr_id}")
    )
    bot.send_message(message.chat.id, text, reply_markup=keyboard)


# ------------------------
# 9. Callback обробники
# ------------------------
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    data = call.data

    if data.startswith("del:"):
        tr_id = int(data.split(":")[1])
        cur.execute('DELETE FROM transactions WHERE id = ?', (tr_id,))
        conn.commit()
        bot.edit_message_text("✅ Видалено", call.message.chat.id, call.message.message_id)
        bot.answer_callback_query(call.id, "Видалено")

    elif data.startswith("edit:"):
        tr_id = int(data.split(":")[1])
        msg = bot.send_message(call.message.chat.id, "💰 Нова сума:")
        bot.register_next_step_handler(msg, lambda m, tid=tr_id: edit_amount(m, tid))
        bot.answer_callback_query(call.id)


def edit_amount(message, tr_id):
    try:
        new_amount = float(message.text.replace(",", "."))
        cur.execute('UPDATE transactions SET amount = ? WHERE id = ?', (new_amount, tr_id))
        conn.commit()
        bot.reply_to(message, f"✅ Оновлено на {new_amount} грн", reply_markup=main_reply_keyboard())
    except ValueError:
        bot.reply_to(message, "❌ Тільки число", reply_markup=main_reply_keyboard())


# ------------------------
# 10. Графік
# ------------------------
@bot.message_handler(commands=['chart'])
def chart(message):
    user_id = message.from_user.id
    cur.execute('''
        SELECT date, SUM(amount) FROM transactions 
        WHERE user_id = ? GROUP BY date ORDER BY date DESC LIMIT 7
    ''', (user_id,))
    rows = cur.fetchall()

    if not rows:
        bot.reply_to(message, "📊 Даних для графіка немає", reply_markup=main_reply_keyboard())
        return

    rows = list(reversed(rows))
    dates = [r[0] for r in rows]
    amounts = [r[1] for r in rows]

    plt.figure(figsize=(8, 4))
    plt.plot(dates, amounts, marker='o', linewidth=2)
    plt.title('Витрати за 7 днів')
    plt.ylabel('грн')
    plt.xticks(rotation=45)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    plt.close()

    bot.send_photo(message.chat.id, buf, caption="📈 Твої витрати")
    buf.close()


# ------------------------
# 11. Кнопки
# ------------------------
@bot.message_handler(func=lambda m: m.text in ["📊 Звіт", "🧾 Остання витрата", "📈 Графік"])
def handle_buttons(message):
    text = message.text
    if text == "📊 Звіт":
        report(message)
    elif text == "🧾 Остання витрата":
        last_transaction(message)
    elif text == "📈 Графік":
        chart(message)


# ------------------------
# 12. Швидке додавання (150 food супермаркет)
# ------------------------
@bot.message_handler(
    func=lambda m: not m.text.startswith('/') and m.text not in ["➕ Додати витрату", "📊 Звіт", "🧾 Остання витрата",
                                                                 "📈 Графік"])
def handle_quick_add(message):
    parsed = try_parse_quick_expense(message.text.strip())
    if parsed:
        amount, category, description = parsed
        save_expense(message.from_user.id, amount, category, description)
        bot.reply_to(
            message,
            f"✅ Додано: {amount} грн ({category})\n"
            f"{description or 'без опису'}",
            reply_markup=main_reply_keyboard()
        )
    else:
        bot.reply_to(
            message,
            "❓ Не зрозумів. Пиши:\n"
            "`150 food супермаркет`\n"
            "або використовуй кнопки",
            reply_markup=main_reply_keyboard(),
            parse_mode='Markdown'
        )


# ------------------------
# 13. Стабільний запуск
# ------------------------
print("🚀 Бот запущений (повністю безкоштовний)")
while True:
    try:
        bot.polling(none_stop=True, interval=2, timeout=20)
    except Exception as e:
        print(f"⚠️ Помилка: {e}. Перезапуск через 5 сек...")
        time.sleep(5)


# ------------------------
# 12. Відповіді ШІ на вільний текст
# ------------------------
@bot.message_handler(func=lambda m: not m.text.startswith('/'))
@bot.message_handler(func=lambda m: not m.text.startswith('/'))
def handle_text(message):
    user_text = message.text.strip()

    # 1) спочатку пробуємо, чи це «швидка витрата» типу "150 food супермаркет"
    parsed = try_parse_quick_expense(user_text)
    if parsed is not None:
        amount, category, description = parsed

        now = datetime.now()
        date_str = now.strftime('%Y-%m-%d')

        cur.execute(
            '''
            INSERT INTO transactions (user_id, date, amount, category, description)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (message.from_user.id, date_str, amount, category, description)
        )
        conn.commit()

        bot.reply_to(
            message,
            f"✅ Додано витрату: {amount} грн, категорія: {category}.\n"
            f"Опис: {description if description else 'немає'}",
            reply_markup=main_reply_keyboard()
        )
        return

    # 2) якщо це не витрата – відповідаємо як фінансовий ШІ
    prompt = (
        "Ти фінансовий асистент. Коротко і по суті відповідай українською.\n\n"
        f"Запит користувача: {user_text}"
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Ти дружній фінансовий асистент."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=300,
            temperature=0.7,
        )

        answer = response.choices[0].message.content.strip()
        bot.reply_to(message, answer, reply_markup=main_reply_keyboard())
    except Exception:
        bot.reply_to(
            message,
            "Не вдалося відповісти за допомогою ШІ. Спробуй ще раз трохи пізніше.",
            reply_markup=main_reply_keyboard()
        )


# ------------------------
# 13. Запуск бота
# ------------------------
if __name__ == '__main__':
    print("🚀 Бот запущений (повністю безкоштовний)")
    try:
        bot.polling(none_stop=True, interval=0, timeout=20)
    except Exception as e:
        print(f"❌ Polling error: {e}")
        time.sleep(5)
