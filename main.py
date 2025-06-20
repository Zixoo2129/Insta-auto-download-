import os
import sys
import subprocess

if __name__ == "__main__":
    print("Starting the simplified Telegram Bot...")
    try:
        subprocess.run([sys.executable, "telegram_bot.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running telegram_bot.py: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("Error: telegram_bot.py not found. Ensure it's in the project root.")
        sys.exit(1)
