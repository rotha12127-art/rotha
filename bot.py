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

BOT_TOKEN = "8469005375:AAHXmdGpdM0DPZJYIaIhd4dBq9ZkdUbp-YM"
ADMIN_GROUP_ID = "-1004401338807"
QR_CODE_FILE = "acleda_qr.png"

SONGS_DATABASE = {
    "song_1": {
        "title": "បទសម្រួល ១ (ROTHA Remix)",
        "price": "1.00 USD",
        "file_path": "R1_22.mp3",
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
    """ជំហានទី១៖ ផ្ញើ QR Code និងប្រាប់ឱ្យផ្ញើរូបវិក្កយបត្រ"""
    query = update.callback_query
    await query.answer()

    song_id = query.data.replace("buy_", "")
    song = SONGS_DATABASE.get(song_id)

    if not song:
        await query.message.reply_text("❌ រកមិនឃើញទិន្នន័យបទចម្រៀងនេះទេ!")
        return

    # ចាំទុកបទចម្រៀងដែល User ជ្រើសរើស
    context.user_data["pending_song_id"] = song_id

    caption_text = (
        f"💳 **ព័ត៌មានបង់ប្រាក់**\n\n"
        f"🎵 **បទចម្រៀង៖** {song['title']}\n"
        f"💰 **តម្លៃ៖** {song['price']}\n\n"
        f"សូមស្កែន QR Code ខាងលើដើម្បីបង់ប្រាក់។ "
        f"បន្ទាប់ពីបង់ប្រាក់រួច **សូមផ្ញើរូបភាពវិក្កយបត្រ (Slip)** ចូលមកកាន់ Chat នេះ! 📸"
    )

    try:
        with open(QR_CODE_FILE, "rb") as qr_img:
            await query.message.reply_photo(
                photo=qr_img,
                caption=caption_text,
                parse_mode="Markdown"
            )
    except FileNotFoundError:
        await query.message.reply_text(
            f"❌ រកមិនឃើញ File QR Code `{QR_CODE_FILE}` ក្នុង GitHub ទេ!\n\n" + caption_text,
            parse_mode="Markdown"
        )

async def handle_receipt_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ជំហានទី២៖ ទទួលរូបថតវិក្កយបត្រពី Client រួចផ្ញើទៅ Admin Group ដើម្បី Confirm"""
    user = update.message.from_user
    song_id = context.user_data.get("pending_song_id")

    if not song_id:
        await update.message.reply_text("❌ សូមជ្រើសរើសបទចម្រៀងជាមុនសិន ដោយចុច /start")
        return

    song = SONGS_DATABASE.get(song_id)
    photo_file_id = update.message.photo[-1].file_id

    # សារជូនដំណឹងទៅ Admin Group ជាមួយប៊ូតុង Confirm
    keyboard = [
        [InlineKeyboardButton("✅ Confirm & ផ្ញើចម្រៀង", callback_data=f"approve_{user.id}_{song_id}")]
    ]

    admin_caption = (
        f"🔔 **មានការបង់ប្រាក់ថ្មី!**\n\n"
        f"👤 **អតិថិជន៖** {user.full_name} (@{user.username if user.username else 'គ្មាន Username'})\n"
        f"🆔 **User ID:** `{user.id}`\n"
        f"🎵 **បទចម្រៀង៖** {song['title']}\n"
        f"💰 **តម្លៃ៖** {song['price']}\n\n"
        f"👇 សូមពិនិត្យរូបភាពវិក្កយបត្រ ខាងក្រោម រួចចុច Confirm៖"
    )

    try:
        # ផ្ញើរូបភាពវិក្កយបត្រទៅ Admin Group
        await context.bot.send_photo(
            chat_id=ADMIN_GROUP_ID,
            photo=photo_file_id,
            caption=admin_caption,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        await update.message.reply_text(
            "✅ **ទទួលបានរូបភាពវិក្កយបត្ររួចហើយ!**\n"
            "សូមរង់ចាំ Admin ពិនិត្យផ្ទៀងផ្ទាត់បន្តិច បទចម្រៀងនឹងផ្ញើជូនអ្នកស្វ័យប្រវត្តិ។ 🙏"
        )
    except Exception as e:
        logging.error(f"Error sending receipt to group: {e}")
        await update.message.reply_text("❌ មានបញ្ហាក្នុងការផ្ញើវិក្កយបត្រទៅកាន់ Admin!")

async def admin_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ជំហានទី៣៖ ពេល Admin ចុច Confirm វានឹងផ្ញើចម្រៀងទៅកាន់ Client"""
    query = update.callback_query
    await query.answer()

    # ទាញយក User ID និង Song ID ពី callback_data (approve_USERID_SONGID)
    data_parts = query.data.split("_")
    client_user_id = int(data_parts[1])
    song_id = data_parts[2]

    song = SONGS_DATABASE.get(song_id)

    if not song:
        await query.message.reply_text("❌ រកមិនឃើញទិន្នន័យបទចម្រៀងនេះទេ!")
        return

    # 1. ផ្ញើចម្រៀងទៅឱ្យ Client
    try:
        await context.bot.send_message(
            chat_id=client_user_id,
            text="🎉 **ការបង់ប្រាក់ត្រូវបានអនុញ្ញាត!** នេះជា File ចម្រៀងរបស់អ្នក៖",
            parse_mode="Markdown"
        )

        if "file_path" in song:
            with open(song["file_path"], "rb") as audio_file:
                await context.bot.send_audio(
                    chat_id=client_user_id,
                    audio=audio_file,
                    title=song["title"],
                    caption=f"🎧 **{song['title']}**\n❤️ សូមរីករាយក្នុងការស្តាប់!",
                    parse_mode="Markdown"
                )
        elif "file_url" in song:
            await context.bot.send_audio(
                chat_id=client_user_id,
                audio=song["file_url"],
                title=song["title"],
                caption=f"🎧 **{song['title']}**\n❤️ សូមរីករាយក្នុងការស្តាប់!",
                parse_mode="Markdown"
            )

        # 2. ប្តូរសារក្នុង Admin Group ថាបាន Confirm រួចហើយ
        await query.edit_message_caption(
            caption=f"{query.message.caption}\n\n✅ **[បាន Confirm និងផ្ញើចម្រៀងរួចរាល់]**",
            parse_mode="Markdown"
        )

    except Exception as e:
        logging.error(f"Error sending song to client: {e}")
        await query.message.reply_text(f"❌ មិនអាចផ្ញើចម្រៀងទៅកាន់ Client បានទេ៖ {e}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(show_songs, pattern="^view_songs$"))
    app.add_handler(CallbackQueryHandler(buy_song, pattern="^buy_"))
    app.add_handler(CallbackQueryHandler(admin_approve, pattern="^approve_"))
    
    # ទទួលរូបភាពវិក្កយបត្រពី Client
    app.add_handler(MessageHandler(filters.PHOTO, handle_receipt_photo))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
