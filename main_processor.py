import os
import asyncio
from dotenv import load_dotenv
from telegram import Bot

from caption_formatter import format_caption
from watermark_handler import process_media

load_dotenv()

OWNER_ID = os.getenv("OWNER_ID")
CHANNEL_ID = os.getenv("CHANNEL_ID")


async def handle_processing(file_path, caption, is_reel=False, cover_path=None):
    print(f"[📦] Processing & Sending for {'Reel' if is_reel else 'Image'}: {file_path}")

    final_caption = format_caption(caption, old_username="@mewsinsta", new_username="@newswire.in")
    final_caption = format_caption(final_caption, old_username="@india.news.24x7", new_username="@newswire.in")

    processed_file_path = process_media(file_path) # This uses OpenCV, not MoviePy

    if processed_file_path:
        print("[💬] Sending processed media to Telegram channel...")
        from telegram_bot import send_media_to_telegram_channel, app as telegram_app

        telegram_sent = await send_media_to_telegram_channel(telegram_app, processed_file_path, final_caption)

        if telegram_sent:
            print("✅ Successfully sent to Telegram.")
        else:
            print("❌ Failed to send to Telegram.")

        try:
            os.remove(file_path)
            print(f"Cleaned up original downloaded file: {file_path}")
        except OSError as e:
            print(f"Error cleaning up original file {file_path}: {e}")
        try:
            os.remove(processed_file_path)
            print(f"Cleaned up processed file: {processed_file_path}")
        except OSError as e:
            print(f"Error cleaning up processed file {processed_file_path}: {e}")

    else:
        print(f"[❌] Processing failed for {file_path}. Skipping Telegram send.")
        from telegram_bot import app as telegram_app
        if telegram_app and OWNER_ID:
            try:
                await telegram_app.bot.send_message(chat_id=OWNER_ID, text=f"❌ Processing failed for '{os.path.basename(file_path)}'. Check logs.")
            except Exception as e:
                print(f"Error sending processing failed message to owner: {e}")
