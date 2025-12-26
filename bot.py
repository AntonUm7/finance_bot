import telebot
import os
import json
import time
from dotenv import load_dotenv
from telebot import types

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
print(f"DEBUG: BOT_TOKEN length = {len(BOT_TOKEN) if BOT_TOKEN else 0}")

if not BOT_TOKEN:
    print("❌ BOT_TOKEN not found!")
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN)
print("✅ Bot created!")

# Дані користувачів
USERS_FILE = "users.json"
user_states = {}
users_data = {}

def load_users():
    global users_data
    try:
        with open(USERS_FILE, 'r') as f:
            users_data = json.load(f)
    except:
        users_data = {}

def save_users():
    with open(USERS_FILE, 'w') as f:
        json.dump(users_data, f, indent=2)

load_users()

def get_user_data(user_id):
    if str(user_id) not in users_data:
        users_data[str(user_id)] = {"balance": 0, "history": [], "goals": {}}
        save_users()
    return users_data[str(user_id)]

@bot.message_handler(commands=['start', 'menu'])
def start_menu(message):
    show_main_menu(message)

def show_main_menu(message):
    user_id = message.from_user.id
    user = get_user_data(user_id)
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_balance = types.InlineKeyboardButton(f"💰 Баланс: {user['balance']} грн", callback_data="balance")
    btn_income = types.InlineKeyboardButton("➕ Дохід", callback_data="income")
    btn_expense = types.InlineKeyboardButton("➖ Витрата", callback_data="expense")
    btn_stats = types.InlineKeyboardButton("📊 Статистика", callback_data="stats")
    markup.add(btn_balance, btn_income, btn_expense, btn_stats)
    
    bot.send_message(message.chat.id, "🎛️ **Головне меню:**", parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    data = call.data
    
    if data == "balance":
        user = get_user_data(user_id)
        bot.answer_callback_query(call.id)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🏠 Головна", callback_data="back_menu"))
        bot.edit_message_text(f"💰 **Твій баланс:**\n`{user['balance']} грн`", 
                            call.message.chat.id, call.message.message_id, 
                            parse_mode='Markdown', reply_markup=markup)
        
    elif data == "income":
        bot.answer_callback_query(call.id)
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("💼 Зарплата", callback_data="income_salary"))
        markup.add(types.InlineKeyboardButton("💰 Фріланс", callback_data="income_freelance"))
        markup.add(types.InlineKeyboardButton("📈 Інвест", callback_data="income_invest"))
        markup.add(types.InlineKeyboardButton("🏠 Головна", callback_data="back_menu"))
        bot.edit_message_text("➕ **Вибери тип доходу:**", 
                            call.message.chat.id, call.message.message_id, 
                            parse_mode='Markdown', reply_markup=markup)
        user_states[str(user_id)] = "waiting_income"
        
    elif data == "expense":
        bot.answer_callback_query(call.id)
        show_expense_categories(call.message.chat.id, call.message.message_id)
        
    elif data == "stats":
        show_stats(call.message.chat.id, user_id, call.message.message_id)
        
    elif data.startswith("expense_"):
        category = data.replace("expense_", "")
        bot.answer_callback_query(call.id)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🏠 Головна", callback_data="back_menu"))
        bot.edit_message_text(f"➖ **{category}**\n\nВведи суму:\n`150` `500` `1200`", 
                            call.message.chat.id, call.message.message_id,
                            parse_mode='Markdown', reply_markup=markup)
        user_states[str(user_id)] = f"waiting_expense_{category}"
        
    elif data.startswith("income_"):
        category = data.replace("income_", "")
        bot.answer_callback_query(call.id)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🏠 Головна", callback_data="back_menu"))
        bot.edit_message_text(f"➕ **{category}**\n\nВведи суму:\n`5000` `2000` `3500`", 
                            call.message.chat.id, call.message.message_id,
                            parse_mode='Markdown', reply_markup=markup)
        user_states[str(user_id)] = f"waiting_income_{category}"
        
    elif data == "back_menu":
        bot.answer_callback_query(call.id)
        bot.delete_message(call.message.chat.id, call.message.message_id)
        show_main_menu(call.message)

def show_expense_categories(chat_id, message_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_food = types.InlineKeyboardButton("🍕 Їжа", callback_data="expense_Їжа")
    btn_home = types.InlineKeyboardButton("🏠 Комуналка", callback_data="expense_Комуналка")
    btn_med = types.InlineKeyboardButton("💊 Ліки", callback_data="expense_Ліки")
    btn_other = types.InlineKeyboardButton("💳 Інше*", callback_data="expense_Інше")
    btn_back = types.InlineKeyboardButton("🏠 Головна", callback_data="back_menu")
    
    markup.add(btn_food, btn_home)
    markup.add(btn_med, btn_other)
    markup.add(btn_back)
    
    bot.edit_message_text("➖ **Вибери категорію:**", chat_id, message_id, 
                        parse_mode='Markdown', reply_markup=markup)

def show_stats(chat_id, user_id, message_id):
    user = get_user_data(user_id)
    total_income = sum(t['amount'] for t in user['history'] if t['type'] == 'income')
    total_expense = sum(t['amount'] for t in user['history'] if t['type'] == 'expense')
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🏠 Головна", callback_data="back_menu"))
    
    stats_text = f"""📊 **Статистика:**

💰 **Баланс:** `{user['balance']} грн`
📈 **Дохід:** `{total_income} грн`
📉 **Витрати:** `{total_expense} грн`
💹 **Результат:** `{user['balance']} грн`

**Історія операцій:** {len(user['history'])}"""
    
    bot.edit_message_text(stats_text, chat_id, message_id, 
                        parse_mode='Markdown', reply_markup=markup)

@bot.message_handler(func=lambda message: True)
def handle_states(message):
    user_id = str(message.from_user.id)
    
    if user_id in user_states:
        state = user_states[user_id]
        
        try:
            if state.startswith("waiting_income_"):
                category = state.replace("waiting_income_", "")
                amount = float(message.text)
                user = get_user_data(message.from_user.id)
                user['balance'] += amount
                user['history'].append({"type": "income", "category": category, "amount": amount, "date": time.strftime("%Y-%m-%d")})
                save_users()
                bot.reply_to(message, f"✅ **+{amount} грн** ({category})\n💰 **Баланс:** `{user['balance']} грн`", parse_mode='Markdown')
                del user_states[user_id]
                show_main_menu(message)
                
            elif state.startswith("waiting_expense_"):
                category = state.replace("waiting_expense_", "")
                
                if category == "Інше":
                    # Зберігаємо суму тимчасово
                    user_states[f"{user_id}_temp_amount"] = message.text
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton("🏠 Головна", callback_data="back_menu"))
                    bot.reply_to(message, f"💳 **Інше**\n\nОпиши покупку:\n`кава` `кіно` `подарунок`", 
                               parse_mode='Markdown', reply_markup=markup)
                    user_states[user_id] = "waiting_other_description"
                    return
                
                # Звичайні категорії
                amount = float(message.text)
                user = get_user_data(message.from_user.id)
                user['balance'] -= amount
                user['history'].append({"type": "expense", "category": category, "amount": amount, "date": time.strftime("%Y-%m-%d")})
                save_users()
                bot.reply_to(message, f"✅ **-{amount} грн** ({category})\n💰 **Баланс:** `{user['balance']} грн`", parse_mode='Markdown')
                del user_states[user_id]
                show_main_menu(message)
                
            elif state == "waiting_other_description":
                # Отримуємо збережену суму
                temp_amount = user_states.get(f"{user_id}_temp_amount", "0")
                amount = float(temp_amount)
                desc = message.text
                user = get_user_data(message.from_user.id)
                user['balance'] -= amount
                user['history'].append({"type": "expense", "category": "Інше", "description": desc, "amount": amount, "date": time.strftime("%Y-%m-%d")})
                save_users()
                bot.reply_to(message, f"✅ **-{amount} грн** (Інше: {desc})\n💰 **Баланс:** `{user['balance']} грн`", parse_mode='Markdown')
                # Очищуємо стани
                del user_states[user_id]
                if f"{user_id}_temp_amount" in user_states:
                    del user_states[f"{user_id}_temp_amount"]
                show_main_menu(message)
                
        except ValueError:
            bot.reply_to(message, "❌ **Введи число!**\n\nПриклади:\n`150` `500` `1200`", parse_mode='Markdown')
            return
        
        return
    
    bot.reply_to(message, "👆 **Використовуй кнопки у меню!**\n\n`/menu` - головне меню", parse_mode='Markdown')

print("🚀 Starting polling...")
bot.polling(none_stop=True, interval=0)



