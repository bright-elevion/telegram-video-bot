import os
import asyncio

from yt_dlp import YoutubeDL

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# =========================================
# BOT TOKEN
# =============================
BOT_TOKEN = "7764954344:AAECpipMlU6jK4rGW7b063ljsbi_RW-R4hI"
# =========================================
# DOWNLOAD FOLDER
# =========================================
DOWNLOAD_FOLDER = "downloads"

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# =========================================
# STORE USER LINKS
# =========================================
user_links = {}

# =========================================
# START COMMAND
# =========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = (
        "Send a video URL.\n\n"
        "Single video:\n"
        "https://example.com/video\n\n"
        "Multiple episodes:\n"
        "https://site.com/episode-{}-sub 221 224"
    )

    await update.message.reply_text(text)

# =========================================
# DOWNLOAD VIDEO
# =========================================
def download_video(url, quality):

    ydl_opts = {
        'format': (
            f'bestvideo[height<={quality}]'
            f'+bestaudio/'
            f'best[height<={quality}]'
        ),

        'outtmpl': os.path.join(
            DOWNLOAD_FOLDER,
            '%(title)s.%(ext)s'
        ),

        'merge_output_format': 'mp4',

        'noplaylist': True,

        'quiet': False,
    }

    with YoutubeDL(ydl_opts) as ydl:

        info = ydl.extract_info(
            url,
            download=True
        )

        filename = ydl.prepare_filename(info)

        base, ext = os.path.splitext(filename)

        mp4_file = base + ".mp4"

        if os.path.exists(mp4_file):
            return mp4_file

        return filename

# =========================================
# HANDLE MESSAGE
# =========================================
async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    text = update.message.text.strip()

    parts = text.split()

    # =====================================
    # MULTI EPISODE MODE
    # =====================================
    if "{}" in text and len(parts) == 3:

        base_url = parts[0]

        try:

            start_ep = int(parts[1])

            end_ep = int(parts[2])

        except:

            await update.message.reply_text(
                "Episode numbers must be integers."
            )

            return

        urls = []

        for ep in range(start_ep, end_ep + 1):

            episode_url = base_url.format(ep)

            urls.append(episode_url)

        user_links[
            update.effective_user.id
        ] = urls

    else:

        # =================================
        # SINGLE VIDEO MODE
        # =================================
        if not text.startswith("http"):

            await update.message.reply_text(
                "Please send a valid URL."
            )

            return

        user_links[
            update.effective_user.id
        ] = [text]

    # =====================================
    # QUALITY BUTTONS
    # =====================================
    keyboard = [
        [
            InlineKeyboardButton(
                "360p",
                callback_data="360"
            ),

            InlineKeyboardButton(
                "480p",
                callback_data="480"
            ),

            InlineKeyboardButton(
                "720p",
                callback_data="720"
            ),
        ]
    ]

    reply_markup = InlineKeyboardMarkup(
        keyboard
    )

    await update.message.reply_text(
        "Choose quality:",
        reply_markup=reply_markup,
    )

# =========================================
# BUTTON HANDLER
# =========================================
async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    quality = query.data

    user_id = query.from_user.id

    if user_id not in user_links:

        await query.message.reply_text(
            "URL expired. Send again."
        )

        return

    urls = user_links[user_id]

    status = await query.message.reply_text(
        f"Starting downloads in {quality}p..."
    )

    try:

        total = len(urls)

        for count, url in enumerate(urls, start=1):

            await status.edit_text(
                f"Downloading {count}/{total}..."
            )

            loop = asyncio.get_event_loop()

            file_path = await loop.run_in_executor(
                None,
                download_video,
                url,
                quality,
            )

            await status.edit_text(
                f"Uploading {count}/{total}..."
            )

            with open(file_path, "rb") as video:

                await query.message.reply_video(
                    video=video,
                    supports_streaming=True,
                )

            # DELETE FILE AFTER UPLOAD
            if os.path.exists(file_path):

                os.remove(file_path)

        await status.edit_text(
            "All downloads completed."
        )

    except Exception as e:

        await status.edit_text(
            f"Error:\n{e}"
        )

# =========================================
# MAIN
# =========================================
def main():

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .connect_timeout(60)
        .read_timeout(60)
        .write_timeout(60)
        .pool_timeout(60)
        .build()
    )

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message,
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            button_handler
        )
    )

    print("Bot is running...")

    app.run_polling()

# =========================================
# RUN BOT
# =========================================
if __name__ == "__main__":

    main()
    
