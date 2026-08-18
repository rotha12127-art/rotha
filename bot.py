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

# 1. BOT TOKEN របស់អ្នក
BOT_TOKEN = "8469005375:AAHXmdGpdMOdPZJYIaIhd4dBq9ZkdUbp-YM"

# 2. Group ID របស់អ្នក (សម្រាប់ទទួលបានការជូនដំណឹង)
ADMIN_GROUP_ID = "-1004401338807"

# 3. បញ្ជីបទចម្រៀង (DATABASE)
SONGS_DATABASE = {
    "song_1": {
        "title": "បទសម្រួល ១ (ROTHA Remix)",
        "price": "1.00 USD",
        "file_path": "11111.mp3",  # ឈ្មោះ File MP3 ដែលបាន Upload ចូល GitHub
    },
    "song_2": {
        "title": "បទសម្រួល ២ (ROTHA Remix)",
        "price": "2.00 USD",
        "file_url": "https://example.com/song2.mp3",  # ឬប្រើ Link MP3 Direct
    },
}

# =========================================================================

# Setup Logging
logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ប៊ូតុងបង្ហាញបញ្ជីចម្រៀងពេលចុច /start"""
    keyboard = [
        [InlineKeyboardButton("🎵 មើលបញ្ជីចម្រៀង", callback_data="view_songs")]
    ]
    await update.message.reply_text(
        "🎧 **សូមស្វាគមន៍មកកាន់ ROTHA Remix Store!** 🎧",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def show_songs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """បង្ហាញបញ្ជីចម្រៀងដែលមានទាំងអស់"""
    query = update.callback_query
    await query.answer()

    keyboard = []
    for s_id, info in SONGS_DATABASE.items():
        # កំណត់ callback_data ឱ្យត្រូវទម្រង់ byte_song_id
        keyboard.append([
            InlineKeyboardButton(
                f"🎧 {info['title']} - {info['price']}", 
                callback_data=f"buy_{s_id}"
            )
        ])

    await query.message.reply_text(
        "សូមជ្រើសរើសបទចម្រៀងដែលអ្នកចង់បាន៖",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def buy_song(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Function ផ្ញើចម្រៀងពេល Client ចុចលើបទចម្រៀងនីមួយៗ"""
    query = update.callback_query
    await query.answer()

    # ទាញយក song_id ចេញពី callback_data (ឧទាហរណ៍៖ "buy_song_1" -> "song_1")
    song_id = query.data.replace("buy_", "")
    
    # ស្វែងរកចម្រៀងក្នុង DATABASE
    song = SONGS_DATABASE.get(song_id)

    # ករណីរកមិនឃើញក្នុង DATABASE (ការពារ Error NoneType)
    if not song:
        await query.message.reply_text("❌ រកមិនឃើញទិន្នន័យបទចម្រៀងនេះទេ!")
        return

    # ករណីចម្រៀងប្រើ File MP3 នៅក្នុង GitHub
    if "file_path" in song:
        try:
            with open(song["file_path"], "rb") as audio_file:
                await query.message.reply_audio(
                    audio=audio_file,
                    title=song["title"],
                    caption=f"🎧 **{song['title']}**\n💰 **តម្លៃ៖ {song['price']}**\n\nសូមអរគុណសម្រាប់ការគាំទ្រ! ❤️",
                    parse_mode="Markdown"
                )
        except FileNotFoundError:
            await query.message.reply_text(
                f"❌ រកមិនឃើញ File `{song['file_path']}` នៅក្នុង GitHub Repository ទេ! "
                f"សូមពិនិត្យមើលឈ្មោះ File ឡើងវិញ។",
                parse_mode="Markdown"
            )

    # ករណីចម្រៀងប្រើ Direct URL MP3
    elif "file_url" in song:
        try:
            await query.message.reply_audio(
                audio=song["file_url"],
                title=song["title"],
                caption=f"🎧 **{song['title']}**\n💰 **តម្លៃ៖ {song['price']}**\n\nសូមអរគុណសម្រាប់ការគាំទ្រ! ❤️",
                parse_mode="Markdown"
            )
        except Exception as e:
            await query.message.reply_text("❌ មានបញ្ហាក្នុងការទាញយក File តាម Link!")

def main():
    """ចាប់ផ្តើមដំណើរការ Bot"""
    app = Application.builder().token(BOT_TOKEN).build()

    # Register Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(show_songs, pattern="^view_songs$"))
    app.add_handler(CallbackQueryHandler(buy_song, pattern="^buy_"))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
