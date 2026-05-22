import os
import re
import uuid
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
# =========================================
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
# CLEAN FILE NAME
# =========================================
def clean_filename(name):

    return re.sub(
        r'[\\/*?:"<>|]',
        "",
        name
    )

# =========================================
# START COMMAND
# =========================================
async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

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
def download_video(
    url,
    quality,
    progress_callback=None
):

    unique_id = str(uuid.uuid4())

    def hook(d):

        if d['status'] == 'downloading':

            downloaded = d.get(
                'downloaded_bytes',
                0
            )

            total = (
                d.get('total_bytes')
                or d.get(
                    'total_bytes_estimate'
                )
                or 0
            )

            if total > 0:

                percent = (
                    downloaded / total
                ) * 100

                if progress_callback:

                    progress_callback(
                        f"Downloading: "
                        f"{percent:.1f}%"
                    )

        elif d['status'] == 'finished':

            if progress_callback:

                progress_callback(
                    "Merging video and audio..."
                )

    ydl_opts = {

        'format': (
            f'bestvideo[height<={quality}]'
            f'+bestaudio/'
            f'/best[height<={quality}]'
        ),

        'outtmpl': os.path.join(
            DOWNLOAD_FOLDER,
            f'{unique_id}.%(ext)s'
        ),

        'merge_output_format': 'mp4',

        'restrictfilenames': True,

        'noplaylist': True,

        'quiet': True,

        'progress_hooks': [hook],

        'impersonate': 'chrome',

        'paths': {
            'home': DOWNLOAD_FOLDER
        },

        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }],
    }

    with YoutubeDL(ydl_opts) as ydl:

        ydl.extract_info(
            url,
            download=True
        )

    # =====================================
    # FIND FINAL MP4
    # =====================================
    for file in os.listdir(DOWNLOAD_FOLDER):

        if (
            file.startswith(unique_id)
            and file.endswith(".mp4")
        ):

            return os.path.join(
                DOWNLOAD_FOLDER,
                file
            )

    raise Exception(
        "Download failed."
    )

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
                "Episode numbers must "
                "be integers."
            )

            return

        urls = []

        for ep in range(
            start_ep,
            end_ep + 1
        ):

            urls.append(
                base_url.format(ep)
            )

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
        f"Starting downloads "
        f"in {quality}p..."
    )

    try:

        total = len(urls)

        for count, url in enumerate(
            urls,
            start=1
        ):

            loop = asyncio.get_event_loop()

            last_update = {
                "text":
                f"Downloading "
                f"{count}/{total}..."
            }

            # =================================
            # PROGRESS CALLBACK
            # =================================
            def progress(text):

                last_update["text"] = (
                    f"{count}/{total}\n{text}"
                )

            # =================================
            # TELEGRAM MESSAGE UPDATER
            # =================================
            async def updater():

                try:

                    while True:

                        try:

                            await status.edit_text(
                                last_update["text"]
                            )

                        except:
                            pass

                        await asyncio.sleep(2)

                except asyncio.CancelledError:
                    pass

            update_task = asyncio.create_task(
                updater()
            )

            # =================================
            # DOWNLOAD
            # =================================
            file_path = await loop.run_in_executor(
                None,
                download_video,
                url,
                quality,
                progress,
            )

            # =================================
            # CLEAN TASK
            # =================================
            update_task.cancel()

            try:
                await update_task

            except asyncio.CancelledError:
                pass

            await status.edit_text(
                f"Uploading "
                f"{count}/{total}..."
            )

            # =================================
            # CHECK FILE
            # =================================
            if not os.path.exists(
                file_path
            ):

                await status.edit_text(
                    "Downloaded file missing."
                )

                continue

            # =================================
            # UPLOAD VIDEO
            # =================================
            with open(
                file_path,
                "rb"
            ) as video:

                await query.message.reply_video(
                    video=video,
                    supports_streaming=True,
                    read_timeout=120,
                    write_timeout=120,
                    connect_timeout=120,
                    pool_timeout=120,
                )

            # =================================
            # DELETE FILE
            # =================================
            if os.path.exists(file_path):

                os.remove(file_path)

        await status.edit_text(
            "All downloads completed."
        )

    except Exception as e:

        await status.edit_text(
            f"Error:\n{str(e)}"
        )

# =========================================
# ERROR HANDLER
# =========================================
async def error_handler(
    update,
    context
):

    print(
        "ERROR:",
        context.error
    )

    try:

        if (
            update
            and update.effective_message
        ):

            await update.effective_message.reply_text(
                f"Error:\n{context.error}"
            )

    except Exception as e:

        print(
            "Error while sending "
            "error message:",
            e
        )

# =========================================
# MAIN
# =========================================
def main():

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .connect_timeout(120)
        .read_timeout(120)
        .write_timeout(120)
        .pool_timeout(120)
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
            filters.TEXT &
            ~filters.COMMAND,
            handle_message,
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            button_handler
        )
    )

    app.add_error_handler(
        error_handler
    )

    print("Bot is running...")

    app.run_polling()

# =========================================
# RUN
# =========================================
if __name__ == "__main__":

    main()
