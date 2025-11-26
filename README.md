# Botzilla Poker Freeroll Bot

Discord bot for automatic monitoring and notifications of poker freeroll tournaments.

## Description

This bot automatically monitors poker freeroll tournaments from two sources:
- freeroll-password.com
- freerollpass.com

The bot sends notifications through Discord about upcoming tournaments, and you can query current events using various commands.

## Features

- Automatic freeroll monitoring and notifications
- Daily summary for the next 24 hours
- Notifications 1 hour and 10 minutes before start
- Discord commands to query tournaments
- Timezone handling (Budapest time)
- Aggregation from two different sources

## Installation on fps.ms platform

### 1. Configuration setup

Create a `config.json` file in the project root directory based on `config.example.json`:

```bash
cp config.example.json config.json
```

Edit the `config.json` file and provide your Discord token and channel ID:

```json
{
  "discord_token": "YOUR_DISCORD_BOT_TOKEN",
  "channel_id": YOUR_CHANNEL_ID
}
```

**Important:** The `config.json` file is in `.gitignore`, so it won't be committed to version control. You must upload this file manually to the fps.ms server!

### 2. Upload files to fps.ms

1. Log in to the [fps.ms panel](https://panel.fps.ms/)
2. Navigate to the Files tab
3. Upload all files, **including the `config.json` file**
4. Verify that the following files are present:
   - `app.py` (this is the entry point for fps.ms)
   - `config.json` (with the production token)
   - `requirements.txt`
   - `pokerparser/` folder with all Python files

### 3. Installing dependencies

fps.ms automatically installs packages specified in `requirements.txt`.

### 4. Starting the bot

fps.ms automatically starts the `app.py` file. If you want to start it manually:

```bash
python app.py
```

## Security notes

- **NEVER commit the `config.json` file** to the git repository!
- The `config.example.json` only serves as a template, don't put production data in it
- On fps.ms, the `config.json` file must be uploaded via SFTP
- If you want to change the token, you only need to edit the `config.json` file in the fps.ms Files tab or via SFTP

## Local development

For local development, create a `config.json` file:

```bash
cp config.example.json config.json
```

Then provide the test token and channel ID.

Running locally:

```bash
python -m pokerparser.discordbot
```

Or simply:

```bash
python app.py
```

## Discord commands

- `!day` - Freerolls for the next 24 hours
- `!next` - Details of the nearest freeroll  
- `!test` - Check bot operation
- `!help` - Help message

## Automatic notifications

The bot automatically monitors freerolls and sends notifications:
- 📅 Daily summary of events for the next 24 hours
- ⏰ 1 hour before start
- 🚨 10 minutes before start

Notifications mention the `@notif_poker` role.

## Requirements

- Python 3.7+
- beautifulsoup4
- requests
- lxml
- discord.py
