import asyncio
import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import httpx
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, BotCommand
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
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"Bot is running smoothly!")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def run_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

threading.Thread(target=run_health_check_server, daemon=True).start()

# ==================== Self-Ping Task (ការពារ Render Sleep) ====================
async def self_ping():
    url = "https://rotha.onrender.com"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    await asyncio.sleep(10)
    
    async with httpx.AsyncClient() as client:
        while True:
            try:
                response = await client.get(url, headers=headers, timeout=15)
                logging.info(f"Self-ping status code: {response.status_code}")
            except Exception as e:
                logging.error(f"Self-ping failed: {e}")
            await asyncio.sleep(300)

# =========================================================================
#                    CONFIGURATION (កន្លែងតំណភ្ជាប់ Website)
# =========================================================================
class Config:
    BOT_TOKEN = "8469005375:AAHXmdGpdMOdPZJYIaIhd4dBq9ZkdUbp-YM"
    ADMIN_GROUP_ID = "-1004401338807"
    
    # 🔗 Link ទៅកាន់ File JSON នៅលើ Netlify Website របស់អ្នក
    SONGS_JSON_URL = "https://rotharemix.netlify.app/songs.json"

# Function សម្រាប់ទាញយក Database ពី Website មកប្រើប្រាស់
async def fetch_songs_database():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(Config.SONGS_JSON_URL, timeout=10)
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        logging.error(f"Failed to fetch songs from website: {e}")
    return {}

# =========================================================================

logging.basicConfig(level=logging.INFO)

async def post_init(application):
    await application.bot.set_my_commands([
        BotCommand("start", "Start the bot")
    ])
    asyncio.create_task(self_ping())

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("pending_song_id", None)
    
    welcome_text = (
        "🎵 **Welcome to Rotha Remix Bot!**\n\n"
        "🌐 **Website:** [Click here to visit website](https://rotharemix.netlify.app)\n\n"
        "👉 Please send the song code you want to buy:"
    )
    
    await update.message.reply_text(welcome_text, parse_mode="Markdown", disable_web_page_preview=True)

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    
    # ទាញទិន្នន័យថ្មីៗពី Website មកឆែក
    songs_db = await fetch_songs_database()
    
    if text in songs_db:
        song_id = text
        song = songs_db[song_id]
        context.user_data["temp_song_id"] = song_id
        
        if "original_price" in song:
            price_text = f"<s>{song['original_price']}</s> <b>{song['price']}</b>"
        else:
            price_text = f"<b>{song['price']}</b>"
            
        confirmation_text = (
            f"🎵 <b>Song Found!</b>\n\n"
            f"<b>Title:</b> {song['title']}\n"
            f"<b>Price:</b> {price_text}\n\n"
            f"Is this the song you want to buy?"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("Yes", callback_data=f"confirm_yes_{song_id}"),
                InlineKeyboardButton("No", callback_data="confirm_no")
            ]
        ]
        
        await update.message.reply_text(
            confirmation_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
    else:
        return

async def confirm_song_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    songs_db = await fetch_songs_database()
    
    if data.startswith("confirm_yes_"):
        song_id = data.replace("confirm_yes_", "")
        song = songs_db.get(song_id)
        
        if not song:
            await query.message.reply_text("❌ Song data not found on website!")
            return
            
        context.user_data["pending_song_id"] = song_id
        
        if "original_price" in song:
            price_text = f"<s>{song['original_price']}</s> <b>{song['price']}</b>"
        else:
            price_text = f"<b>{song['price']}</b>"

        caption_text = (
            f"💳 <b>Payment Information</b>\n\n"
            f"🎵 <b>Song:</b> {song['title']}\n"
            f"💰 <b>Price:</b> {price_text}\n\n"
            f"Once you have paid, please send the receipt image to me 📥"
        )

        info_msg = None
        if song.get("qr_code"):
            try:
                with open(song["qr_code"], "rb") as qr_img:
                    info_msg = await query.message.reply_photo(
                        photo=qr_img,
                        caption=caption_text,
                        parse_mode="HTML"
                    )
            except FileNotFoundError:
                info_msg = await query.message.reply_text(
                    f"❌ QR Code file `{song['qr_code']}` not found!\n\n" + caption_text,
                    parse_mode="HTML"
                )
        else:
            info_msg = await query.message.reply_text(caption_text, parse_mode="HTML")

        if info_msg:
            context.user_data["info_msg_id"] = info_msg.message_id
            
        try:
            await query.message.delete()
        except Exception:
            pass

    elif data == "confirm_no":
        context.user_data.pop("temp_song_id", None)
        try:
            await query.message.delete()
        except Exception:
            pass
            
        no_text = (
            "🌐 **Website:** [Click here to visit website](https://rotharemix.netlify.app)\n\n"
            "👉 Please send the song code you want to buy:"
        )
        await query.message.reply_text(no_text, parse_mode="Markdown", disable_web_page_preview=True)

async def handle_receipt_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    song_id = context.user_data.get("pending_song_id")
    info_msg_id = context.user_data.get("info_msg_id")

    songs_db = await fetch_songs_database()
    if not song_id or song_id not in songs_db:
        return

    song = songs_db.get(song_id)
    photo_file_id = update.message.photo[-1].file_id

    wait_msg = await update.message.reply_text(
        "Please wait for the Admin to verify!\n"
        "The song will be sent to you automatically. ⏳"
    )

    order_key = f"{user.id}_{song_id}"
    context.bot_data[order_key] = {
        "user_id": user.id,
        "song_id": song_id,
        "info_msg_id": info_msg_id,
        "wait_msg_id": wait_msg.message_id
    }

    keyboard = [
        [
            InlineKeyboardButton("✅ Confirm", callback_data=f"cfm_{order_key}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"rej_{order_key}")
        ]
    ]

    admin_caption = (
        f"🔔 <b>New Payment Received!</b>\n\n"
        f"👤 <b>Customer:</b> {user.full_name} (@{user.username if user.username else 'No Username'})\n"
        f"🆔 <b>User ID:</b> <code>{user.id}</code>\n"
        f"🎵 <b>Song:</b> {song['title']}\n"
        f"💰 <b>Price:</b> {song['price']}\n\n"
    )

    try:
        await context.bot.send_photo(
            chat_id=Config.ADMIN_GROUP_ID,
            photo=photo_file_id,
            caption=admin_caption,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Error sending receipt to group: {e}")
        await update.message.reply_text("❌ There was an error sending the receipt to the Admin!")

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
            info_msg_id = None
            wait_msg_id = None
        except Exception:
            await query.message.reply_text("❌ Order data not found!")
            return
    else:
        client_user_id = order_data["user_id"]
        song_id = order_data["song_id"]
        info_msg_id = order_data.get("info_msg_id")
        wait_msg_id = order_data.get("wait_msg_id")

    songs_db = await fetch_songs_database()
    song = songs_db.get(song_id)

    if not song:
        await query.message.reply_text("❌ Song data not found on website!")
        return

    try:
        if info_msg_id:
            try:
                await context.bot.delete_message(chat_id=client_user_id, message_id=info_msg_id)
            except Exception as del_err:
                logging.warning(f"Could not delete info message: {del_err}")

        if wait_msg_id:
            try:
                await context.bot.delete_message(chat_id=client_user_id, message_id=wait_msg_id)
            except Exception as del_err:
                logging.warning(f"Could not delete wait message: {del_err}")

        await context.bot.send_message(
            chat_id=client_user_id,
            text="🎉 Request approved! Here is your song file:",
            parse_mode="Markdown"
        )

        if "file_path" in song:
            with open(song["file_path"], "rb") as audio_file:
                await context.bot.send_audio(
                    chat_id=client_user_id,
                    audio=audio_file,
                    caption=f" **{song['title']}**\n",
                    parse_mode="Markdown"
                )

        if query.message.photo:
            await query.edit_message_caption(
                caption=f"{query.message.caption}\n\n✅ <b>[Confirmed and song sent]</b>",
                reply_markup=None,
                parse_mode="HTML"
            )
        else:
            await query.edit_message_text(
                text=f"{query.message.text}\n\n✅ <b>[Confirmed and song sent]</b>",
                reply_markup=None,
                parse_mode="HTML"
            )

    except Exception as e:
        logging.error(f"Error sending song to client: {e}")
        await query.message.reply_text(f"❌ Cannot send song to client: {e}")

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
            wait_msg_id = None
        except Exception:
            await query.message.reply_text("❌ Order data not found!")
            return
    else:
        client_user_id = order_data["user_id"]
        song_id = order_data["song_id"]
        wait_msg_id = order_data.get("wait_msg_id")

    songs_db = await fetch_songs_database()
    song = songs_db.get(song_id)
    song_title = song['title'] if song else "Song"

    try:
        if wait_msg_id:
            try:
                await context.bot.delete_message(chat_id=client_user_id, message_id=wait_msg_id)
            except Exception as del_err:
                logging.warning(f"Could not delete wait message on reject: {del_err}")

        await context.bot.send_message(
            chat_id=client_user_id,
            text=f"❌ **Sorry!** Your request for **{song_title}** was rejected. Please contact Admin for more details.",
            parse_mode="Markdown"
        )

        if query.message.photo:
            await query.edit_message_caption(
                caption=f"{query.message.caption}\n\n❌ <b>[Rejected]</b>",
                reply_markup=None,
                parse_mode="HTML"
            )
        else:
            await query.edit_message_text(
                text=f"{query.message.text}\n\n❌ <b>[Rejected]</b>",
                reply_markup=None,
                parse_mode="HTML"
            )

    except Exception as e:
        logging.error(f"Error rejecting order: {e}")
        await query.message.reply_text(f"❌ Cannot send rejection message to client: {e}")

def main():
    app = Application.builder().token(Config.BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    app.add_handler(CallbackQueryHandler(confirm_song_choice, pattern="^confirm_"))
    app.add_handler(CallbackQueryHandler(admin_approve, pattern="^cfm_"))
    app.add_handler(CallbackQueryHandler(admin_reject, pattern="^rej_"))
    app.add_handler(MessageHandler(filters.PHOTO, handle_receipt_photo))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
