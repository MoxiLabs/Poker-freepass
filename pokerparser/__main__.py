"""Main entry point for the poker parser - runs the Discord bot"""

import sys
from .discordbot import bot, TOKEN


def main():
    """Main function to start the Discord bot"""
    try:
        print("Starting Discord bot...", file=sys.stderr)
        bot.run(TOKEN)
    except Exception as e:
        print(f"Error starting bot: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
