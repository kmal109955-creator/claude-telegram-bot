import os
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import yt_dlp

logging.basicConfig(level=logging.INFO)

TOKEN = os.environ.get("BOT_TOKEN")

user_links = {}

# ---------- سيرفر وهمي بسيط حتى يقبل Render تشغيله كـ Web Service ----------
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is running.")

    def log_message(self, format, *args):
        pass  # لتجنب طباعة سجلات كثيرة غير مفيدة

def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()
# ----------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أرسل لي رابط فيديو يوتيوب وسأعطيك خيارات الجودة 🎬")

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if "youtube.com" not in url and "youtu.be" not in url:
        await update.message.reply_text("الرجاء إرسال رابط يوتيوب صالح.")
        return

    user_id = update.message.from_user.id
    user_links[user_id] = url

    msg = await update.message.reply_text("⏳ جاري جلب معلومات الفيديو...")

    try:
        ydl_opts = {"quiet": True, "noplaylist": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        await msg.edit_text(f"❌ تعذر جلب الفيديو: {e}")
        return

    formats = info.get("formats", [])
    seen = set()
    for f in formats:
        height = f.get("height")
        ext = f.get("ext")
        if height and ext == "mp4" and f.get("vcodec") != "none":
            seen.add(height)

    buttons = []
    for height in sorted(seen, reverse=True):
        buttons.append([InlineKeyboardButton(f"{height}p", callback_data=f"vid_{height}")])

    buttons.append([InlineKeyboardButton("🎵 صوت فقط MP3", callback_data="audio")])

    title = info.get("title", "بدون عنوان")
    await msg.edit_text(
        f"🎬 {title}\nاختر الجودة:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def handle_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    url = user_links.get(user_id)

    if not url:
        await query.message.reply_text("أرسل الرابط من جديد من فضلك.")
        return

    status_msg = await
