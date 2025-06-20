import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import os
from dotenv import load_dotenv

load_dotenv()

# --- Configuration from your provided details ---
# These will be loaded from Render's environment variables.
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = os.getenv("OWNER_ID")

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

    logger.info("Bot is running...")
    # This directly runs the polling loop, resolving the "event loop already running" error.
    app.run_polling()
