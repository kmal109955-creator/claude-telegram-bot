import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import yt_dlp

logging.basicConfig(level=logging.INFO)

TOKEN = os.environ.get("BOT_TOKEN")

user_links = {}

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
    buttons = []
    for f in formats:
        height = f.get("height")
        ext = f.get("ext")
        if height and ext == "mp4" and f.get("vcodec") != "none" and height not in seen:
            seen.add(height)
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

    status_msg = await query.message.reply_text("⏳ جاري التحميل، الرجاء الانتظار...")

    choice = query.data
    os.makedirs("downloads", exist_ok=True)

    if choice == "audio":
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": "downloads/%(id)s.%(ext)s",
            "noplaylist": True,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        }
    else:
        height = choice.replace("vid_", "")
        ydl_opts = {
            "format": f"bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/best[height<={height}]",
            "merge_output_format": "mp4",
            "outtmpl": "downloads/%(id)s.%(ext)s",
            "noplaylist": True,
        }

    filepath = None
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filepath = ydl.prepare_filename(info)
            if choice == "audio":
                filepath = os.path.splitext(filepath)[0] + ".mp3"

        await status_msg.edit_text("📤 جاري الإرسال...")

        with open(filepath, "rb") as f:
            if choice == "audio":
                await query.message.reply_audio(audio=f, title=info.get("title"))
            else:
                await query.message.reply_video(video=f, caption=info.get("title"))

        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(f"❌ خطأ: {e}\n\nملاحظة: تلكرام يمنع إرسال ملفات أكبر من 50 ميغا عبر البوتات العادية.")
    finally:
        if filepath and os.path.exists(filepath):
            os.remove(filepath)

def main():
    if not TOKEN:
        raise RuntimeError("لم يتم العثور على BOT_TOKEN في متغيرات البيئة!")

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    app.add_handler(CallbackQueryHandler(handle_choice))
    app.run_polling()

if __name__ == "__main__":
    main()
