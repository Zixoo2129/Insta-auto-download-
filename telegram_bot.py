import logging
from telegram import Update, InputFile, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import os
from dotenv import load_dotenv
import asyncio
from functools import partial

# Import InstagramMonitor class
from instagram_monitor import InstagramMonitor

# Import processing function from main_processor.py
# This is a dynamic import used within commands to avoid circular dependencies
# from main_processor import handle_processing 

load_dotenv() # This will attempt to load .env, but will use Render's env vars if set

# --- Configuration from your provided details ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = os.getenv("OWNER_ID")
CHANNEL_ID = os.getenv("CHANNEL_ID")
INSTAGRAM_PROFILES_TO_MONITOR_STR = os.getenv("INSTAGRAM_PROFILES_TO_MONITOR")
INSTAGRAM_PROFILES_TO_MONITOR = [u.strip() for u in INSTAGRAM_PROFILES_TO_MONITOR_STR.split(',')] if INSTAGRAM_PROFILES_TO_MONITOR_STR else []

# --- Global State ---
auto_post_enabled = False # Bot starts with auto-posting OFF

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Helper Function to send media to Telegram ---
async def send_media_to_telegram_channel(bot_instance: Bot, media_path, caption):
    if not CHANNEL_ID:
        logger.error("CHANNEL_ID environment variable not set. Cannot send to Telegram channel.")
        return False
    
    try:
        with open(media_path, 'rb') as media_file:
            if media_path.lower().endswith(('.jpg', '.jpeg', '.png')):
                await bot_instance.send_photo(chat_id=CHANNEL_ID, photo=InputFile(media_file), caption=caption)
            elif media_path.lower().endswith(('.mp4', '.mov')):
                await bot_instance.send_video(chat_id=CHANNEL_ID, video=InputFile(media_file), caption=caption)
            else:
                logger.warning(f"Unsupported media type for sending to Telegram: {media_path}")
                return False
        logger.info(f"Successfully sent {media_path} to Telegram channel {CHANNEL_ID}")
        return True
    except FileNotFoundError:
        logger.error(f"Media file not found at {media_path} for Telegram send.")
        return False
    except Exception as e:
        logger.error(f"Error sending media to Telegram channel: {e}", exc_info=True)
        return False

# --- Instagram Monitoring Task ---
async def instagram_monitoring_task(bot_instance: Bot, monitor_interval_minutes: int = 5):
    """Periodically checks Instagram for new posts."""
    monitor = InstagramMonitor(INSTAGRAM_PROFILES_TO_MONITOR, bot_instance, OWNER_ID)
    
    while True:
        try:
            if auto_post_enabled: # Only check if auto-post is enabled
                await monitor.check_for_new_posts()
            else:
                logger.info("Auto-post is disabled. Skipping Instagram check.")
        except Exception as e:
            logger.error(f"Error in Instagram monitoring task: {e}", exc_info=True)
            await bot_instance.send_message(chat_id=OWNER_ID, text=f"❌ Critical error in Instagram monitor: {e}")
        
        await asyncio.sleep(monitor_interval_minutes * 60) # Wait for specified interval


# --- Telegram Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(f"👋 Hello! Your Telegram ID is: `{user_id}`. I am your Instagram Auto-Editor & Telegram Sender Bot. Use /help for commands.", parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = f"""
    *Bot Commands:*
    /start - Get your Telegram ID.
    /help - Show this help message.
    /autopost_status - Check if auto-posting is enabled.
    /autopost_on - Enable automatic Instagram monitoring & sending.
    /autopost_off - Disable automatic Instagram monitoring & sending.
    /check_instagram - Manually trigger an Instagram check *now*.
    /process_test_file <file_name> <caption> - Manually process a file from 'downloads/' and send to Telegram (for testing).
    /rescan_logo <file_name> - Rescan & re-process an image for watermarks/logo (saves as _rescanned).
    
    *Current Auto-Post Status:* {'ENABLED' if auto_post_enabled else 'DISABLED'}
    """
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def autopost_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Auto-posting is currently: {'ENABLED' if auto_post_enabled else 'DISABLED'}")

async def autopost_on_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global auto_post_enabled
    if str(update.effective_user.id) != OWNER_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        return
    auto_post_enabled = True
    await update.message.reply_text("Automatic Instagram monitoring & sending is now ENABLED.")

async def autopost_off_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global auto_post_enabled
    if str(update.effective_user.id) != OWNER_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        return
    auto_post_enabled = False
    await update.message.reply_text("Automatic Instagram monitoring & sending is now DISABLED.")

# Manually trigger an Instagram check (even if auto-post is off)
async def check_instagram_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != OWNER_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        return
    await update.message.reply_text("Manually triggering Instagram check now...")
    monitor = InstagramMonitor(INSTAGRAM_PROFILES_TO_MONITOR, context.bot, OWNER_ID)
    asyncio.create_task(monitor.check_for_new_posts()) # Run in background
    await update.message.reply_text("Check initiated. Monitor logs for results.")


# Command to process a file from 'downloads/' (for testing without live Instagram scraping)
async def process_test_file_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != OWNER_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    args = context.args
    if not args or len(args) < 2:
        await update.message.reply_text("Usage: /process_test_file <file_name_in_downloads_folder> <caption_text>")
        return

    file_name = args[0]
    file_path = os.path.join("downloads", file_name)
    caption = " ".join(args[1:])

    if not os.path.exists(file_path):
        await update.message.reply_text(f"Error: File '{file_name}' not found in 'downloads/' folder.")
        return

    is_reel = False
    if file_path.lower().endswith(('.mp4', '.mov')):
        is_reel = True

    await update.message.reply_text(f"Processing '{file_name}' and sending to Telegram (via test command)...")
    # Dynamically import handle_processing
    from main_processor import handle_processing
    asyncio.create_task(handle_processing(file_path, caption, is_reel=is_reel))
    await update.message.reply_text("Processing started. Check logs for progress and your Telegram channel.")


# /rescan_logo command (for testing watermark/overlay)
async def rescan_logo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != OWNER_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    args = context.args
    if not args or len(args) < 1:
        await update.message.reply_text("Usage: /rescan_logo <file_name_in_downloads_folder>")
        return

    file_name = args[0]
    original_file_path = os.path.join("downloads", file_name)

    if not os.path.exists(original_file_path):
        await update.message.reply_text(f"Error: File '{file_name}' not found in 'downloads/' folder.")
        return

    # Generate a temporary processed path for rescan to avoid overwriting original immediately
    base, ext = os.path.splitext(original_file_path)
    temp_processed_path = f"{base}_rescanned{ext}"

    await update.message.reply_text(f"Rescanning and processing '{file_name}'...")
    
    from watermark_handler import detect_and_blur_watermark # Dynamic import
    overlay_logo_path = os.getenv("OVERLAY_LOGO_PATH", None)

    success = False
    try:
        success = detect_and_blur_watermark(original_file_path, temp_processed_path, overlay_logo_path)
    except Exception as e:
        logger.error(f"Error during rescan of {original_file_path}: {e}", exc_info=True)
        await update.message.reply_text(f"Error during rescan: {e}")
        return

    if success:
        await update.message.reply_text(f"Rescan complete. New processed file saved to: `{temp_processed_path}`", parse_mode="Markdown")
        # Try to send preview, handle if it's video or not
        try:
            if temp_processed_path.lower().endswith(('.jpg', '.jpeg', '.png')):
                await update.message.reply_photo(photo=InputFile(temp_processed_path), caption="Rescanned Image Preview")
            elif temp_processed_path.lower().endswith(('.mp4', '.mov')):
                await update.message.reply_video(video=InputFile(temp_processed_path), caption="Rescanned Video Preview")
        except Exception as e:
            logger.warning(f"Could not send preview for {temp_processed_path}: {e}")
            await update.message.reply_text("Could not send preview. File might be too large or invalid.")
    else:
        await update.message.reply_text("Rescan failed. Check logs for details.")

# --- Main Bot Setup ---
app = ApplicationBuilder().token(BOT_TOKEN).build()

async def main():
    # Register command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("autopost_status", autopost_status_command))
    app.add_handler(CommandHandler("autopost_on", autopost_on_command))
    app.add_handler(CommandHandler("autopost_off", autopost_off_command))
    app.add_handler(CommandHandler("check_instagram", check_instagram_command))
    app.add_handler(CommandHandler("process_test_file", process_test_file_command)) # Changed command name
    app.add_handler(CommandHandler("rescan_logo", rescan_logo_command))

    # Schedule the Instagram monitoring task to run in the background
    app.job_queue.run_once(
        lambda context: asyncio.create_task(instagram_monitoring_task(context.bot)),
        when=1, # Run after 1 second initially
        name="initial_instagram_monitor_start"
    )

    logger.info("Bot is running...")
    await app.run_polling() # Use await for run_polling in async main

if __name__ == "__main__":
    asyncio.run(main())
