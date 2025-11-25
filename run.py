#!/usr/bin/env python3
"""Standalone runner for the poker parser Discord bot"""

import sys
import os

# Add the pokerparser directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and run the bot
from pokerparser.discordbot import bot, TOKEN

if __name__ == "__main__":
    try:
        print("Starting Discord bot...", flush=True)
        bot.run(TOKEN)
    except KeyboardInterrupt:
        print("\nBot stopped by user.", flush=True)
        sys.exit(0)
    except Exception as e:
        print(f"Error starting bot: {e}", flush=True)
        sys.exit(1)
