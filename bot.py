import telebot
import os
from dotenv import load_dotenv
import time

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
print(f"DEBUG: BOT_TOKEN length = {len(BOT_TOKEN) if BOT_TOKEN else 0}")

if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN not found!")
    exit(1)

print("✅ Token OK, starting bot...")
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "✅ Фінансовий бот запущено!\nКоманди: /menu, баланс, +100, -50")

@bot.message_handler(commands=['menu'])
def menu(message):
    bot.reply_to(message, "📊 Меню:\n• баланс\n• +100 (дохід)\n• -50 (витрата)\n• /stats")

@bot.message_handler(func=lambda message: True)
def all_messages(message):
    bot.reply_to(message, f"📨 Отримано: {message.text}\nНапиши: баланс, +100, -50")

print("🚀 Бот запущений (повністю безкоштовний)")
if __name__ == '__main__':
    try:
        bot.polling(none_stop=True, interval=0, timeout=20)
    except Exception as e:
        print(f"❌ Polling error: {e}")
        time.sleep(5)

