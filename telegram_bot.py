import logging
import os
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

load_dotenv()

# --- Configuration from your provided details ---
# These will be loaded from Render's environment variables.
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = os.getenv("OWNER_ID")
# Render automatically provides a PORT environment variable for Web Services
PORT = int(os.getenv("PORT", "8080")) # Default to 8080 if not set

# Render provides the service's public URL
WEBHOOK_URL = os.getenv("RENDER_EXTERNAL_URL")

# --- Basic Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Telegram Command Handlers ---

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(f"👋 Hello! Your Telegram ID is: `{user_id}`. I am your basic Telegram Bot. Use /help for commands.", parse_mode="Markdown")

# /help command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
    *Basic Bot Commands:*
    /start - Get your Telegram ID.
    /help - Show this help message.
    """
    await update.message.reply_text(help_text, parse_mode="Markdown")

# --- Main Bot Setup ---
# 'app' instance needs to be accessible for the bot to run
app = ApplicationBuilder().token(BOT_TOKEN).build()

if __name__ == "__main__":
    # Register command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    logger.info(f"Bot is starting on port {PORT}...")

    # For Web Service deployment, use webhooks instead of polling
    if WEBHOOK_URL:
        # We need to set the webhook URL for Telegram to send updates to this bot
        full_webhook_url = f"{WEBHOOK_URL}/telegram" # Use a specific path for the webhook
        logger.info(f"Setting webhook to: {full_webhook_url}")
        
        # Run the bot with webhooks - REMOVED on_startup and on_shutdown
        app.run_webhook(listen="0.0.0.0",
                        port=PORT,
                        url_path="telegram", # This path must match the one used in full_webhook_url
                        webhook_url=full_webhook_url,
                        )
        logger.info("Bot is running with webhooks.")
    else:
        logger.error("RENDER_EXTERNAL_URL environment variable not found. Cannot set up webhook.")
        logger.info("Falling back to polling (will likely spin down on Render Free Tier Web Service).")
        app.run_polling() # Fallback to polling if webhook URL is not available
