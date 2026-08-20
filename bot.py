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

# ==================== ការកំណត់ព័ត៌មាន (CONFIGURATION) ====================

BOT_TOKEN = "8469005375:AAHXmdGpdMOdPZJYIaIhd4dBq9ZkdUbp-YM"
ADMIN_GROUP_ID = "-1004401338807"

# បញ្ជីចម្រៀង updated
SONGS_DATABASE = {
    "song_1": {
        "title": "Track 1",
        "price": "FREE",
        "is_free": True,       # ដោនឡូតបានភ្លាមៗ
        "file_path": "Project_2.mp3",
    },
    "song_2": {
        "title": "下辈子还要和你成个家",
        "price": "FREE",
        "is_free": False,      # FREE តែត្រូវចាំ Request Confirm ពី Admin (គ្មាន QR)
        "file_path": "5_6332401890327798194.mp3",
    },
    "song_3": {
        "title": "一剪梅",
        "price": "0.99 USD",
        "strike_price": "9̶.̶9̶9̶ ̶U̶S̶D̶", # សម្រាប់បង្ហាញលើ Inline Button
        "original_price": "9.99 USD",
        "is_free": False,
        "file_path": "一剪梅.mp3",
        "qr_code": "一剪梅.png",
    },
    "song_4": {
        "title": "Track 4",
        "price": "9.99 USD",
        "is_free": False,
        "file_path": "5_6307483950365289011.mp3",
        "qr_code": "acleda_qr.png",
    },
    "song_5": {
        "title": "Track 5",
        "price": "19.99 USD",
        "is_free": False,
        "file_path": "r1.mp3",
        "qr_code": "19.99.png",
    },
    "song_6": {
        "title": "Track 6",
        "price": "29.99 USD",
        "is_free": False,
        "file_path": "track6.mp3",
        "qr_code": "29.99.png",
    },
}

# =========================================================================

logging.basicConfig(level=logging.INFO)

async def post_init(application):
    await application.bot.set_my_commands([
        BotCommand("start", "Start the bot")
    ])
    asyncio.create_task(self_ping())

async def display_songs(message_or_query, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    for s_id, info in SONGS_DATABASE.items():
        if info.get("price") == "FREE":
            label = f" {info['title']} - FREE"
        elif "strike_price" in info:
            label = f" {info['title']} - {info['strike_price']}  {info['price']}"
        else:
            label = f" {info['title']} - {info['price']}"
            
        keyboard.append([
            InlineKeyboardButton(label, callback_data=f"buy_{s_id}")
        ])
    
    text = "Please select the song you want:"
    reply_markup = InlineKeyboardMarkup(keyboard)

    if hasattr(message_or_query, 'edit_message_text'):
        await message_or_query.edit_message_text(text, reply_markup=reply_markup)
    else:
        await message_or_query.reply_text(text, reply_markup=reply_markup)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await display_songs(update.message, context)

async def show_songs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await display_songs(query, context)

async def buy_song(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    song_id = query.data.replace("buy_", "")
    song = SONGS_DATABASE.get(song_id)

    if not song:
        await query.message.reply_text("❌ Song data not found!")
        return

    # ------------------ បើជាបទ FREE ដែលដោនឡូតបានភ្លាមៗ (Track 1) ------------------
    if song.get("is_free"):
        loading_msg = await query.message.reply_text("Downloading and sending to you...", parse_mode="Markdown")
        try:
            if "file_path" in song:
                with open(song["file_path"], "rb") as audio_file:
                    await context.bot.send_audio(
                        chat_id=query.from_user.id,
                        audio=audio_file,
                        caption=f" **{song['title']}**",
                        parse_mode="Markdown"
                    )
            await loading_msg.delete()
        except Exception as e:
            logging.error(f"Error sending free song: {e}")
            await loading_msg.edit_text("❌ There was an error sending the song file! Please try again.")
        return

    # ------------------ បើជាបទដែលត្រូវរង់ចាំ Admin Confirm ------------------
    context.user_data["pending_song_id"] = song_id

    if song.get("price") == "FREE":
        caption_text = (
            f"ℹ️ <b>Request Information</b>\n\n"
        )
    else:
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

        user = query.from_user
        order_key = f"{user.id}_{song_id}"
        context.bot_data[order_key] = {
            "user_id": user.id,
            "song_id": song_id,
            "info_msg_id": info_msg.message_id if info_msg else None
        }

        keyboard = [
            [
                InlineKeyboardButton("✅ Confirm", callback_data=f"cfm_{order_key}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"rej_{order_key}")
            ]
        ]

        admin_caption = (
            f"🔔 <b>New Free Request Received!</b>\n\n"
            f"👤 <b>Customer:</b> {user.full_name} (@{user.username if user.username else 'No Username'})\n"
            f"🆔 <b>User ID:</b> <code>{user.id}</code>\n"
            f"🎵 <b>Song:</b> {song['title']}\n"
            f"💰 <b>Price:</b> {song['price']}\n\n"
        )

        try:
            await context.bot.send_message(
                chat_id=ADMIN_GROUP_ID,
                text=admin_caption,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML"
            )
        except Exception as e:
            logging.error(f"Error sending request to admin group: {e}")

    if info_msg:
        context.user_data["info_msg_id"] = info_msg.message_id

async def handle_receipt_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    song_id = context.user_data.get("pending_song_id")
    info_msg_id = context.user_data.get("info_msg_id")

    if not song_id or song_id not in SONGS_DATABASE:
        await update.message.reply_text("❌ Please select a song first by typing /start")
        return

    song = SONGS_DATABASE.get(song_id)
    photo_file_id = update.message.photo[-1].file_id

    # ផ្ញើសាររង់ចាំ ហើយរក្សាទុក wait_msg_id ដើម្បីលុបពេល Admin Approve
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
            chat_id=ADMIN_GROUP_ID,
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

    song = SONGS_DATABASE.get(song_id)

    if not song:
        await query.message.reply_text("❌ Song data not found!")
        return

    try:
        # លុបសារ Payment / Request Information
        if info_msg_id:
            try:
                await context.bot.delete_message(chat_id=client_user_id, message_id=info_msg_id)
            except Exception as del_err:
                logging.warning(f"Could not delete info message: {del_err}")

        # លុបសារ "Please wait for the Admin to verify!"
        if wait_msg_id:
            try:
                await context.bot.delete_message(chat_id=client_user_id, message_id=wait_msg_id)
            except Exception as del_err:
                logging.warning(f"Could not delete wait message: {del_err}")

        # ផ្ញើសារ Request approved សម្រាប់តែ song_3 ដល់ song_6 ប៉ុណ្ណោះ (song_2 មិនផ្ញើទេ)
        if song_id != "song_2":
            await context.bot.send_message(
                chat_id=client_user_id,
                text="🎉 Rkunjren Request approved! Here is your song file:",
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

    song = SONGS_DATABASE.get(song_id)
    song_title = song['title'] if song else "Song"

    try:
        # លុបសារ "Please wait for the Admin to verify!" ប្រសិនបើ Reject
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
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

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
            
