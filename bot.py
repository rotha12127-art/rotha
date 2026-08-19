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
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running smoothly!")

def run_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

threading.Thread(target=run_health_check_server, daemon=True).start()

# ==================== ការកំណត់ព័ត៌មាន (CONFIGURATION) ====================

BOT_TOKEN = "8469005375:AAHXmdGpdMOdPZJYIaIhd4dBq9ZkdUbp-YM"
ADMIN_GROUP_ID = "-1004401338807"
QR_CODE_FILE = "acleda_qr.png"

SONGS_DATABASE = {
    "song_1": {
        "title": "Track 1",
        "price": "FREE",
        "is_free": True,
        "file_path": "Project_2.mp3",
    },
    "song_2": {
        "title": "Track 2",
        "price": "9.99 USD",
        "is_free": False,
        "file_path": "一剪梅.mp3",
    },
    "song_3": {
        "title": "Track 3",
        "price": "9.99 USD",
        "is_free": False,
        "file_path": "r1.mp3",
    },
}

# =========================================================================

logging.basicConfig(level=logging.INFO)

# អនុគមន៍សម្រាប់បង្ហាញបញ្ជីចម្រៀងភ្លាមៗ
async def display_songs(message_or_query):
    keyboard = []
    for s_id, info in SONGS_DATABASE.items():
        label = f" {info['title']} - {info['price']}" if info.get("is_free") else f"🎧 {info['title']} - {info['price']}"
        keyboard.append([
            InlineKeyboardButton(label, callback_data=f"buy_{s_id}")
        ])
    
    text = "សូមជ្រើសរើសបទចម្រៀងដែលអ្នកចង់បាន៖"
    reply_markup = InlineKeyboardMarkup(keyboard)

    if hasattr(message_or_query, 'edit_message_text'):
        await message_or_query.edit_message_text(text, reply_markup=reply_markup)
    else:
        await message_or_query.reply_text(text, reply_markup=reply_markup)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # បង្ហាញបញ្ជីចម្រៀងភ្លាមៗដោយមិនមានសារស្វាគមន៍
    await display_songs(update.message)

async def show_songs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await display_songs(query)

async def buy_song(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    song_id = query.data.replace("buy_", "")
    song = SONGS_DATABASE.get(song_id)

    if not song:
        await query.message.reply_text("❌ រកមិនឃើញទិន្នន័យបទចម្រៀងនេះទេ!")
        return

    # ------------------ បើជាបទ FREE ------------------
    if song.get("is_free"):
        await query.message.reply_text("🎉 កំពុងទាញយក និងផ្ញើជូនអ្នក...", parse_mode="Markdown")
        try:
            if "file_path" in song:
                with open(song["file_path"], "rb") as audio_file:
                    await context.bot.send_audio(
                        chat_id=query.from_user.id,
                        audio=audio_file,
                        caption=f" **{song['title']}** \n",
                        parse_mode="Markdown"
                    )
        except Exception as e:
            logging.error(f"Error sending free song: {e}")
            await query.message.reply_text("❌ មានបញ្ហាក្នុងការផ្ញើ File ចម្រៀង! សូមព្យាយាមម្តងទៀត។")
        return

    # ------------------ បើជាបទត្រូវបង់ប្រាក់ (Paid) ------------------
    context.user_data["pending_song_id"] = song_id

    caption_text = (
        f"💳 **ព័ត៌មានបង់ប្រាក់**\n\n"
        f"🎵 **បទចម្រៀង៖** {song['title']}\n"
        f"💰 **តម្លៃ៖** {song['price']}\n\n"
        f"ពេលដែលអ្នកបានបង់ប្រាក់រួចរាល់ សូមផ្ញើរូបភាពវិក្ក័យបត្រចូលមកកាន់ខ្ញុំ 📥"
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
    user = update.message.from_user
    song_id = context.user_data.get("pending_song_id")

    if not song_id or song_id not in SONGS_DATABASE:
        await update.message.reply_text("❌ សូមជ្រើសរើសបទចម្រៀងជាមុនសិន ដោយវាយ /start")
        return

    song = SONGS_DATABASE.get(song_id)
    photo_file_id = update.message.photo[-1].file_id

    order_key = f"{user.id}_{song_id}"
    context.bot_data[order_key] = {
        "user_id": user.id,
        "song_id": song_id
    }

    keyboard = [
        [
            InlineKeyboardButton("✅ Confirm & ផ្ញើចម្រៀង", callback_data=f"cfm_{order_key}"),
            InlineKeyboardButton("❌ Reject (បដិសេធ)", callback_data=f"rej_{order_key}")
        ]
    ]

    admin_caption = (
        f"🔔 **មានការបង់ប្រាក់ថ្មី!**\n\n"
        f"👤 **អតិថិជន៖** {user.full_name} (@{user.username if user.username else 'គ្មាន Username'})\n"
        f"🆔 **User ID:** `{user.id}`\n"
        f"🎵 **បទចម្រៀង៖** {song['title']}\n"
        f"💰 **តម្លៃ៖** {song['price']}\n\n"
        f"👇 សូមពិនិត្យរូបភាពវិក្កយបត្រ ខាងក្រោម រួចជ្រើសរើស៖"
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
            "✅សូមរង់ចាំ Admin ពិនិត្យផ្ទៀងផ្ទាត់បន្តិច!\n"
            "បទចម្រៀងនឹងផ្ញើជូនអ្នកស្វ័យប្រវត្តិ។ 🙏"
        )
    except Exception as e:
        logging.error(f"Error sending receipt to group: {e}")
        await update.message.reply_text("❌ មានបញ្ហាក្នុងការផ្ញើវិក្កយបត្រទៅកាន់ Admin!")

async def admin_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    try:
        await context.bot.send_message(
            chat_id=client_user_id,
            text="🎉 RkunJren ការបង់ប្រាក់ត្រូវបានអនុញ្ញាត នេះជា File ចម្រៀងរបស់អ្នក៖",
            parse_mode="Markdown"
        )

        if "file_path" in song:
            with open(song["file_path"], "rb") as audio_file:
                await context.bot.send_audio(
                    chat_id=client_user_id,
                    audio=audio_file,
                    caption=f"🎧 **{song['title']}**\n",
                    parse_mode="Markdown"
                )

        # កែប្រែ៖ ដកប៊ូតុងចេញដោយប្រើ reply_markup=None
        await query.edit_message_caption(
            caption=f"{query.message.caption}\n\n✅ **[បាន Confirm និងផ្ញើចម្រៀងរួចរាល់]**",
            reply_markup=None,
            parse_mode="Markdown"
        )

    except Exception as e:
        logging.error(f"Error sending song to client: {e}")
        await query.message.reply_text(f"❌ មិនអាចផ្ញើចម្រៀងទៅកាន់ Client បានទេ៖ {e}")

async def admin_reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    order_key = query.data.replace("rej_", "")
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
    song_title = song['title'] if song else "បទចម្រៀង"

    try:
        await context.bot.send_message(
            chat_id=client_user_id,
            text=f"❌ **សូមអភ័យទោស!** ព័ត៌មាន ឬរូបភាពវិក្កយបត្របង់ប្រាក់សម្រាប់បទ **{song_title}** មិនត្រឹមត្រូវទេ។ សូមពិនិត្យ និងផ្ញើរូបភាពឡើងវិញ។ 🙏",
            parse_mode="Markdown"
        )

        # កែប្រែ៖ ដកប៊ូតុងចេញដោយប្រើ reply_markup=None
        await query.edit_message_caption(
            caption=f"{query.message.caption}\n\n❌ **[បាន Reject/បដិសេធ រួចរាល់]**",
            reply_markup=None,
            parse_mode="Markdown"
        )

    except Exception as e:
        logging.error(f"Error rejecting order: {e}")
        await query.message.reply_text(f"❌ មិនអាចផ្ញើសារបដិសេធទៅ Client បានទេ៖ {e}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(show_songs, pattern="^view_songs$"))
    app.add_handler(CallbackQueryHandler(buy_song, pattern="^buy_"))
    app.add_handler(CallbackQueryHandler(admin_approve, pattern="^cfm_"))
    app.add_handler(CallbackQueryHandler(admin_reject, pattern="^rej_"))
    
    app.add_handler(MessageHandler(filters.PHOTO, handle_receipt_photo))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
    
