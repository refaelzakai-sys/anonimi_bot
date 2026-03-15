import logging
from flask import Flask
from threading import Thread
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# --- מנגנון Keep Alive ל-Render ---
app = Flask('')

@app.route('/')
def home():
    return "Rafael Digital Bot is Online!"

def run():
    # Render משתמש בפורט 10000 כברירת מחדל
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()
# ---------------------------------

# הגדרות
TOKEN = "8799447400:AAEah-A0AUzq2h0bdAugdhVMJYt2MmP-yrg"
ADMIN_ID = 7622681013
INACTIVITY_TIMEOUT = 90
ADMIN_WAIT_TIME = 40

# ניהול מצב בזיכרון
waiting_users = {}
active_chats = {}
known_users = {}

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# ... (שאר הפונקציות שלך: start, find_chat, וכו' נשארות אותו דבר) ...

def main():
    # הפעלת השרת שימנע מהבוט להירדם
    keep_alive()
    
    app_telegram = Application.builder().token(TOKEN).build()
    
    app_telegram.add_handler(CommandHandler("start", start))
    app_telegram.add_handler(CommandHandler("chat", find_chat))
    app_telegram.add_handler(CommandHandler("exit", exit_chat))
    app_telegram.add_handler(CommandHandler("me", lambda u, c: u.message.reply_text(f"ID: {u.message.from_user.id}")))
    app_telegram.add_handler(CommandHandler("connect", connect_by_id))
    app_telegram.add_handler(CallbackQueryHandler(button_handler))
    app_telegram.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    
    print("Rafael Digital Bot is running...")
    app_telegram.run_polling()

if __name__ == "__main__":
    main()
