import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ==================== Web Server សម្រាប់ Render Health Check ====================
# ការពារកុំឱ្យ Render ជាប់ Timed Out ឬដួល (Failed)
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running smoothly!")

def run_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

# ដំណើរការ Web Server ក្នុង Thread ដាច់ដោយឡែក
threading.Thread(target=run_health_check_server, daemon=True).start()

# ==================== ការកំណត់ព័ត៌មាន (CONFIGURATION) ====================

BOT_TOKEN = "8469005375:AAHXmdGpdMOdPZJYIaIhd4dBq9ZkdUbp-YM"
ADMIN_GROUP_ID = "-1004401338807"
QR_CODE_FILE = "acleda_qr.png"

SONGS_DATABASE = {
    "song_1": {
        "title": "Track 1 (ROTHA Remix)",
        "price": "9.99 USD",
        "file_path": "Project_2.mp3",
    },
    "song_2": {
        "title": "Track 2 (ROTHA Remix)",
        "price": "9.99 USD",
        "file_path": "一剪梅.mp3",
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

    # រក្សាទុកបទចម្រៀងដែល User ជ្រើសរើស
    context.user_data["pending_song_id"] = song_id

    caption_text = (
        f"💳 **ព័ត៌មានបង់ប្រាក់**\n\n"
        f"🎵 **បទចម្រៀង៖** {song['title']}\n"
        f"💰 **តម្លៃ៖** {song['price']}\n\n"
        f"បន្ទាប់ពីបង់ប្រាក់រួច សូមផ្ញើរូបភាពវិក្កយបត្រចូលមកកាន់ Chat នេះ! RkunJren😘"
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

    if not song_id or song_id not in SONGS_DATABASE:
        await update.message.reply_text("❌ សូមជ្រើសរើសបទចម្រៀងជាមុនសិន ដោយវាយ /start")
        return

    song = SONGS_DATABASE.get(song_id)
    photo_file_id = update.message.photo[-1].file_id

    # រក្សាទុកទិន្នន័យបណ្តោះអាសន្ន
    order_key = f"{user.id}_{song_id}"
    context.bot_data[order_key] = {
        "user_id": user.id,
        "song_id": song_id
    }

    # ប៊ូតុង Confirm ប្រើ callback_data ខ្លី
    keyboard = [
        [InlineKeyboardButton("✅ Confirm & ផ្ញើចម្រៀង", callback_data=f"cfm_{order_key}")]
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
        await context.bot.send_photo(
            chat_id=ADMIN_GROUP_ID,
            photo=photo_file_id,
            caption=admin_caption,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        await update.message.reply_text(
            "✅សូមរង់ចាំ Admin ពិនិត្យផ្ទៀងផ្ទាត់បន្តិច!😊\n"
            "បទចម្រៀងនឹងផ្ញើជូនអ្នកស្វ័យប្រវត្តិ។ 🙏"
        )
    except Exception as e:
        logging.error(f"Error sending receipt to group: {e}")
        await update.message.reply_text("❌ មានបញ្ហាក្នុងការផ្ញើវិក្កយបត្រទៅកាន់ Admin!")

async def admin_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ជំហានទី៣៖ ពេល Admin ចុច Confirm វានឹងផ្ញើចម្រៀងទៅកាន់ Client"""
    query = update.callback_query
    await query.answer()

    order_key = query.data.replace("cfm_", "")
    order_data = context.bot_data.get(order_key)

    if not order_data:
        try:
            parts = order_key.split("_")
            client_user_id = int(parts[0])
            song_id = f"{parts[1]}_{parts[2]}" if len(parts) > 2 else parts[1]
        except Exception:
            await query.message.reply_text("❌ រកមិនឃើញទិន្នន័យ Order នេះទេ!")
            return
    else:
        client_user_id = order_data["user_id"]
        song_id = order_data["song_id"]

    song = SONGS_DATABASE.get(song_id)

    if not song:
        await query.message.reply_text("❌ រកមិនឃើញទិន្នន័យបទចម្រៀងនេះទេ!")
        return

    # 1. ផ្ញើចម្រៀងទៅឱ្យ Client
    try:
        await context.bot.send_message(
            chat_id=client_user_id,
            text="Thanks❤️🎉 ការបង់ប្រាក់ត្រូវបានអនុញ្ញាត នេះជា File ចម្រៀងរបស់អ្នក៖",
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
    app.add_handler(CallbackQueryHandler(admin_approve, pattern="^cfm_"))
    
    app.add_handler(MessageHandler(filters.PHOTO, handle_receipt_photo))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
