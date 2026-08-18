import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

# ==================== ការកំណត់ព័ត៌មាន (CONFIGURATION) ====================

BOT_TOKEN = "8469005375:AAHXmdGpdM0DPZJYIaIhd4dBq9ZkdUbp-YM"

# Group ID របស់អ្នកសម្រាប់ទទួលដំណឹង
ADMIN_GROUP_ID = "-1004401338807" 

QR_CODE_FILE = "acleda_qr.png" 

SONGS_DATABASE = {
    "song_1": {
        "title": "បទសម្រួល ១ (ROTHA Remix)",
        "price": "1.00 USD",
        "file_path": "Project_6.mp3",
    },
    "song_2": {
        "title": "បទសម្រួល ២ (ROTHA Remix)",
        "price": "2.00 USD",
        "file_url": "https://example.com/song2.mp3",
    },
}

# =========================================================================

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎵 មើលបញ្ជីចម្រៀង", callback_data="view_songs")]
    ]
    await update.message.reply_text(
        "🎧 **សូមស្វាគមន៍មកកាន់ ROTHA Remix Store!** 🎧",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def show_songs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = []
    for s_id, info in SONGS_DATABASE.items():
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
    query = update.callback_query
    await query.answer()

    song_id = query.data.replace("buy_", "")
    song = SONGS_DATABASE.get(song_id)

    if not song:
        await query.message.reply_text("❌ រកមិនឃើញទិន្នន័យបទចម្រៀងនេះទេ!")
        return

    keyboard = [
        [InlineKeyboardButton("✅ ខ្ញុំបានបង់ប្រាក់រួចហើយ (ទាញយកចម្រៀង)", callback_data=f"getsong_{song_id}")]
    ]

    caption_text = (
        f"💳 **ព័ត៌មានបង់ប្រាក់**\n\n"
        f"🎵 **បទចម្រៀង៖** {song['title']}\n"
        f"💰 **តម្លៃ៖** {song['price']}\n\n"
        f"សូមស្កែន QR Code អេស៊ីលីដាខាងលើដើម្បីបង់ប្រាក់។ "
        f"បន្ទាប់ពីបង់ប្រាក់រួច សូមចុចប៊ូតុង **«ខ្ញុំបានបង់ប្រាក់រួចហើយ»** ខាងក្រោមដើម្បីទទួលបានចម្រៀង! 🙏"
    )

    try:
        with open(QR_CODE_FILE, "rb") as qr_img:
            await query.message.reply_photo(
                photo=qr_img,
                caption=caption_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
    except FileNotFoundError:
        await query.message.reply_text(
            f"❌ រកមិនឃើញ File QR Code `{QR_CODE_FILE}` ក្នុង GitHub ទេ!\n\n" + caption_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

async def send_song_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    song_id = query.data.replace("getsong_", "")
    song = SONGS_DATABASE.get(song_id)
    user = query.from_user  # ព័ត៌មានរបស់ Client ដែលទិញ

    if not song:
        await query.message.reply_text("❌ រកមិនឃើញទិន្នន័យបទចម្រៀងនេះទេ!")
        return

    # 1. ផ្ញើសារជូនដំណឹងទៅ Admin Group 🔔
    admin_msg = (
        f"🔔 **មានអតិថិជនបានចុចទិញចម្រៀង!**\n\n"
        f"👤 **អតិថិជន៖** {user.full_name} (@{user.username if user.username else 'គ្មាន Username'})\n"
        f"🆔 **User ID:** `{user.id}`\n"
        f"🎵 **បទចម្រៀង៖** {song['title']}\n"
        f"💰 **តម្លៃ៖** {song['price']}"
    )
    try:
        await context.bot.send_message(
            chat_id=ADMIN_GROUP_ID,
            text=admin_msg,
            parse_mode="Markdown"
        )
    except Exception as e:
        logging.error(f"មិនអាចផ្ញើសារទៅ Admin Group បានទេ៖ {e}")

    # 2. ផ្ញើ File MP3 ទៅឱ្យ Client
    await query.message.reply_text("🎉 សូមអរគុណសម្រាប់ការបង់ប្រាក់! នេះជា File ចម្រៀងរបស់អ្នក៖")

    if "file_path" in song:
        try:
            with open(song["file_path"], "rb") as audio_file:
                await query.message.reply_audio(
                    audio=audio_file,
                    title=song["title"],
                    caption=f"🎧 **{song['title']}**\n❤️ សូមរីករាយក្នុងការស្តាប់!",
                    parse_mode="Markdown"
                )
        except FileNotFoundError:
            await query.message.reply_text(f"❌ រកមិនឃើញ File MP3 `{song['file_path']}` ទេ!")

    elif "file_url" in song:
        await query.message.reply_audio(
            audio=song["file_url"],
            title=song["title"],
            caption=f"🎧 **{song['title']}**\n❤️ សូមរីករាយក្នុងការស្តាប់!",
            parse_mode="Markdown"
        )

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(show_songs, pattern="^view_songs$"))
    app.add_handler(CallbackQueryHandler(buy_song, pattern="^buy_"))
    app.add_handler(CallbackQueryHandler(send_song_file, pattern="^getsong_"))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
