import telebot
import os
from dotenv import load_dotenv
import time

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
print(f"DEBUG: BOT_TOKEN length = {len(BOT_TOKEN) if BOT_TOKEN else 0}")

if not BOT_TOKEN:
    print("❌ BOT_TOKEN not found!")
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN)
print("✅ Bot created!")

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "✅ Бот працює! Напиши 'меню'")

@bot.message_handler(commands=['menu'])
def menu(message):
    bot.reply_to(message, "📋 Меню:\nбаланс\n+100\n-50")

@bot.message_handler(func=lambda m: True)
def echo(message):
    bot.reply_to(message, f"📨 {message.text}")

print("🚀 Starting polling...")
bot.polling(none_stop=True, interval=0)


