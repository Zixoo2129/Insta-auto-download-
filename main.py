import os
import sys
import subprocess
import asyncio

# This main.py will simply execute telegram_bot.py, which is your main bot logic.
# This is a common pattern for Render to define the start command.

if __name__ == "__main__":
    print("Starting Bot (Instagram Auto-Editor & Telegram Sender)...")
    try:
        # Run telegram_bot.py as a subprocess
        # This allows telegram_bot.py to handle its own polling loop and background tasks
        subprocess.run([sys.executable, "telegram_bot.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running telegram_bot.py: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("Error: telegram_bot.py not found. Ensure it's in the project root.")
        sys.exit(1)
