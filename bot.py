import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ==================== ការកំណត់ព័ត៌មាន (CONFIGURATION) ====================

# 1. ជំនួសអក្សរ YOUR_BOT_TOKEN_HERE ដោយ Token របស់ Bot អ្នក
BOT_TOKEN = "8469005375:AAHXmdGpdMOdPZJYIaIhd4dBq9ZkdUbp-YM"  

# 2. Group ID របស់អ្នក (លេខដែលបានរកឃើញ)
ADMIN_GROUP_ID = "-1004401338807"  

# 3. បញ្ជីចម្រៀង
SONGS_DATABASE = {
    "song_1": {
        "title": "បទចម្រៀងទី ១ (ROTHA Remix)",
        "price": "1.00 USD",
        "file_path": "11111.mp3",
    },
    "song_2": {
        "title": "បទចម្រៀងទី ២ (ROTHA Remix)",
        "price": "2.00 USD",
        "file_url": "https://example.com/song2.mp3",
    },
}

# =========================================================================

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🎵 មើលបញ្ជីចម្រៀង", callback_data="view_songs")]]
    await update.message.reply_text("សូមស្វាគមន៍មកកាន់ ROTHA Remix Store! 🎧", reply_markup=InlineKeyboardMarkup(keyboard))

async def show_songs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton(f"{info['title']} - {info['price']}", callback_data=f"buy_{s_id}")] for s_id, info in SONGS_DATABASE.items()]
    await query.edit_message_text("សូមជ្រើសរើសចម្រៀងដែលអ្នកចង់ទិញ៖", reply_markup=InlineKeyboardMarkup(keyboard))

async def buy_song(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    song_id = query.data.split("_")[1]
    song = SONGS_DATABASE.get(song_id)
    context.user_data["pending_song"] = song_id
    caption = f"🎯 **អ្នកបានជ្រើសរើស៖** {song['title']}\n💰 **តម្លៃ៖** {song['price']}\n\nសូមស្កែន **ACLEDA KHQR** ខាងក្រោមដើម្បីបង់ប្រាក់ រួច **ផ្ញើរូបភាព Slip មកកាន់ Chat នេះ**"
    try:
        with open("acleda_qr.png", "rb") as qr_file:
            await context.bot.send_photo(chat_id=query.message.chat_id, photo=qr_file, caption=caption)
    except FileNotFoundError:
        await context.bot.send_message(chat_id=query.message.chat_id, text=f"{caption}\n\n⚠️ *(រកមិនឃើញរូប acleda_qr.png ក្នុង Folder)*")

async def handle_slip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    pending_song_id = context.user_data.get("pending_song")
    if not pending_song_id:
        await update.message.reply_text("សូមចុច /start ដើម្បីជ្រើសរើសចម្រៀងសិន")
        return
    song = SONGS_DATABASE[pending_song_id]
    photo_file_id = update.message.photo[-1].file_id
    keyboard = [
        [InlineKeyboardButton("✅ យល់ព្រម", callback_data=f"admin_approve_{user.id}_{pending_song_id}")],
        [InlineKeyboardButton("❌ បដិសេធ", callback_data=f"admin_reject_{user.id}_{pending_song_id}")]
    ]
    admin_caption = f"📥 មាន Slip ថ្មី!\n👤 អតិថិជន: {user.full_name}\n🎵 ទិញបទ: {song['title']}"
    await context.bot.send_photo(chat_id=ADMIN_GROUP_ID, photo=photo_file_id, caption=admin_caption, reply_markup=InlineKeyboardMarkup(keyboard))
    await update.message.reply_text("✅ ទទួលបាន Slip ហើយ! Admin កំពុងពិនិត្យ សូមរង់ចាំបន្តិច។")

async def handle_admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split("_")
    action, buyer_id, song_id = data[1], int(data[2]), data[3]
    song = SONGS_DATABASE[song_id]
    if action == "approve":
        await context.bot.send_message(chat_id=buyer_id, text=f"🎉 ការទូទាត់ត្រូវបានអនុម័ត!\nតំណភ្ជាប់ចម្រៀង៖\n{song['file_url']}")
        await query.edit_message_caption(caption=f"{query.message.caption}\n\n✅ បានអនុម័ត")
    else:
        await context.bot.send_message(chat_id=buyer_id, text="❌ ការទូទាត់ត្រូវបានបដិសេធ។")
        await query.edit_message_caption(caption=f"{query.message.caption}\n\n❌ បានបដិសេធ")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(show_songs, pattern="^view_songs$"))
    app.add_handler(CallbackQueryHandler(buy_song, pattern="^buy_"))
    app.add_handler(CallbackQueryHandler(handle_admin_action, pattern="^admin_"))
    app.add_handler(MessageHandler(filters.PHOTO, handle_slip))
    print("ROTHA Remix Bot កំពុងដំណើរការ...")
    app.run_polling()

if __name__ == "__main__":
    main()
