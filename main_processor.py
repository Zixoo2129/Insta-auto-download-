import os
import asyncio
from dotenv import load_dotenv # Keep this import, it's used to load env vars
from telegram import Bot # Needed for type hinting if sending back messages

# Import your core processing modules
from caption_formatter import format_caption
from watermark_handler import process_media

# Load environment variables (will get from Render's config if .env not supported)
load_dotenv()

OWNER_ID = os.getenv("OWNER_ID")
CHANNEL_ID = os.getenv("CHANNEL_ID")


async def handle_processing(file_path, caption, is_reel=False, cover_path=None):
    """
    Handles the full processing workflow for a given file:
    - Caption formatting
    - Watermark blur/overlay
    - Sends to Telegram channel
    This function is called by instagram_monitor.py or telegram_bot.py commands.
    """
    print(f"[📦] Processing & Sending for {'Reel' if is_reel else 'Image'}: {file_path}")

    # Step 1: Format caption (removes old handles, adds hashtags)
    # Ensure new_username is always '@newswire.in'
    final_caption = format_caption(caption, old_username="@mewsinsta", new_username="@newswire.in")
    final_caption = format_caption(final_caption, old_username="@india.news.24x7", new_username="@newswire.in")


    # Step 2: Apply watermark blur/overlay
    processed_file_path = process_media(file_path)

    if processed_file_path: # Only proceed if processing was successful
        # Step 3: Send to Telegram Channel
        print("[💬] Sending processed media to Telegram channel...")
        # Dynamically import the Telegram sending function and bot instance
        # 'app' is the bot instance built in telegram_bot.py
        from telegram_bot import send_media_to_telegram_channel, app as telegram_app
        
        telegram_sent = await send_media_to_telegram_channel(telegram_app, processed_file_path, final_caption)
        
        if telegram_sent:
            print("✅ Successfully sent to Telegram.")
        else:
            print("❌ Failed to send to Telegram.")
        
        # Clean up downloaded/processed files after use
        try:
            os.remove(file_path) # Remove original downloaded file
            print(f"Cleaned up original downloaded file: {file_path}")
        except OSError as e:
            print(f"Error cleaning up original file {file_path}: {e}")
        try:
            os.remove(processed_file_path) # Remove processed file
            print(f"Cleaned up processed file: {processed_file_path}")
        except OSError as e:
            print(f"Error cleaning up processed file {processed_file_path}: {e}")

    else:
        print(f"[❌] Processing failed for {file_path}. Skipping Telegram send.")
        # Send error message to owner if processing failed
        from telegram_bot import app as telegram_app # Get app
        if telegram_app and OWNER_ID:
            try:
                await telegram_app.bot.send_message(chat_id=OWNER_ID, text=f"❌ Processing failed for '{os.path.basename(file_path)}'. Check logs.")
            except Exception as e:
                print(f"Error sending processing failed message to owner: {e}")

# No if __name__ == "__main__": block here. This file defines functions
# that are called by telegram_bot.py or instagram_monitor.py.
