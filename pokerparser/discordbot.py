import discord
import asyncio
import requests
import re
import json
import os
import sys
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
from itertools import cycle
from typing import List, cast, Union
from .freerollpass import FreerollParser
from .freeroll_password import FreeRollPasswordParser
from .models import TournamentEvent

# ------------------------------------------------------
# CONFIG LOADING
# ------------------------------------------------------
def load_config():
    """Load configuration from config.json file"""
    # Try to find config.json in multiple locations
    possible_paths = [
        "config.json",  # Current directory
        os.path.join(os.path.dirname(__file__), "..", "config.json"),  # Parent directory
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config.json"),  # Absolute parent
    ]
    
    for config_path in possible_paths:
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading config from {config_path}: {e}")
                continue
    
    # If no config file found, show error and exit
    print("ERROR: config.json not found!")
    print("Please create a config.json file based on config.example.json")
    print("Expected locations:")
    for path in possible_paths:
        print(f"  - {os.path.abspath(path)}")
    sys.exit(1)

# Load configuration
config = load_config()
TOKEN = config.get("discord_token")
CHANNEL_ID = config.get("channel_id")

if not TOKEN:
    print("ERROR: discord_token not found in config.json")
    sys.exit(1)

if not CHANNEL_ID:
    print("ERROR: channel_id not found in config.json")
    sys.exit(1)

LAST_EVENT_FILE = "last_event.json"

intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)

URL_PASSWORD = "https://freeroll-password.com/"
URL_PASS = "https://freerollpass.com/"

# ------------------------------------------------------
# SCRAPER – freeroll-password.com
# ------------------------------------------------------
def fetch_freerolls_password() -> List[TournamentEvent]:
    """Fetch freerolls from freeroll-password.com"""
    try:
        parser = FreeRollPasswordParser(url=URL_PASSWORD)
        tournaments = parser.get_tournaments()
        return tournaments if tournaments else []
    except:
        return []


# ------------------------------------------------------
# SCRAPER – freerollpass.com
# ------------------------------------------------------
def fetch_freerolls_pass() -> List[TournamentEvent]:
    """Fetch freerolls from freerollpass.com"""
    try:
        parser = FreerollParser(url=URL_PASS)
        tournaments = parser.get_tournaments()
        return tournaments if tournaments else []
    except:
        return []


# ------------------------------------------------------
# COMBINED SCRAPER
# ------------------------------------------------------
def get_event_datetime(event: TournamentEvent) -> datetime:
    """Get datetime from event (date + time fields)"""
    if event['is_all_day'] or event['time'] is None:
        # For all-day events, use midnight
        return datetime.combine(event['date'], datetime.min.time())
    return datetime.combine(event['date'], event['time'])

def fetch_freerolls() -> List[TournamentEvent]:
    """Fetch freerolls from all sources and combine them"""
    events: List[TournamentEvent] = []    # Fetch from both sources
    events.extend(fetch_freerolls_password())
    events.extend(fetch_freerolls_pass())
    
    # Sort by date and time
    events.sort(key=lambda x: get_event_datetime(x))
    return events

# ------------------------------------------------------
# EVENT STORAGE HELPERS
# ------------------------------------------------------
def load_last_event():
    """Load the last sent event from file"""
    if not os.path.exists(LAST_EVENT_FILE):
        return None
    try:
        with open(LAST_EVENT_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return None

def save_last_event(event: TournamentEvent) -> None:
    """Save the last sent event to file"""
    event_data = {
        "date": event["date"].isoformat(),
        "time": event["time"].isoformat() if event["time"] else None,
        "is_all_day": event["is_all_day"],
        "room": event["room"],
        "name": event["name"],
        "prize": event["prize"],
        "password": event["password"],
        "source": event.get("source", "n/a")
    }
    try:
        with open(LAST_EVENT_FILE, 'w', encoding='utf-8') as f:
            json.dump(event_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving event: {e}")

def event_is_after_last(event: TournamentEvent) -> bool:
    """Check if an event is after the last sent event"""
    last_event = load_last_event()
    if last_event is None:
        return True
    
    event_data = {
        "date": event["date"].isoformat(),
        "time": event["time"].isoformat() if event["time"] else None,
        "is_all_day": event["is_all_day"],
        "room": event["room"],
        "name": event["name"],
        "prize": event["prize"],
        "password": event["password"],
        "source": event.get("source", "n/a")
    }
    
    # Compare datetime to see if this event is newer
    event_dt = get_event_datetime(event)
    last_dt_str = f"{last_event['date']} {last_event.get('time', '00:00:00')}"
    try:
        last_dt = datetime.fromisoformat(last_dt_str.replace(' ', 'T'))
    except:
        # If can't parse last event, consider current event as new
        return True
    
    return event_dt > last_dt or event_data != last_event

# ------------------------------------------------------
# FORMATTER
# ------------------------------------------------------
def fmt(e: TournamentEvent) -> str:
    source_emoji = "🌐" if e.get('source') == "freeroll-password.com" else "🎯"
    
    # Format time display
    if e['is_all_day'] or e['time'] is None:
        time_display = f"**{e['date'].strftime('%d.%m.%Y')} (egész nap)**"
    else:
        dt = get_event_datetime(e)
        time_display = f"**{dt.strftime('%H:%M %d.%m.%Y')}**"
    
    return (
        f"💰 **{e['name']}**\n"
        f"🏢 Terem: **{e['room']}**\n"
        f"💵 Díjazás: **{e['prize']}**\n"
        f"🕒 Kezdés: {time_display}\n"
        f"🔑 Jelszó: **{e['password']}**\n"
        f"{source_emoji} Forrás: {e.get('source', 'n/a')}\n"
        f"──────────────"
    )

# ------------------------------------------------------
# COMMANDS
# ------------------------------------------------------
async def send_today(message):
    # Használjuk a globálisan tárolt eseményeket a watcher-ből
    global GLOBAL_EVENTS
    events = GLOBAL_EVENTS if GLOBAL_EVENTS else fetch_freerolls()
    now = datetime.now()
    
    # Következő 24 óra eseményei (most + 24 óra)
    next_24h_cutoff = now + timedelta(hours=24)
    next_24h = [e for e in events if now <= get_event_datetime(e) <= next_24h_cutoff]

    if not next_24h:
        await message.channel.send("📭 Nincs freeroll a következő 24 órában.")
        return

    await message.channel.send("📅 **Következő 24 óra freerolljai:**\n")
    for e in next_24h:
        await message.channel.send(fmt(e))

async def send_next(message):
    # Használjuk a globálisan tárolt eseményeket a watcher-ből
    global GLOBAL_EVENTS
    events = GLOBAL_EVENTS if GLOBAL_EVENTS else fetch_freerolls()
    now = datetime.now()
    
    # Filter out all-day events and get future events
    future = [e for e in events if not e['is_all_day'] and get_event_datetime(e) > now]

    if not future:
        await message.channel.send("❌ Nincs közelgő freeroll.")
        return

    nxt = future[0]
    delta = get_event_datetime(nxt) - now
    total_minutes = int(delta.total_seconds() / 60)
    
    time_msg = f"⏰ **{total_minutes} perc múlva kezdődik!**\n\n"
    await message.channel.send("👉 **Következő freeroll:**\n" + time_msg + fmt(nxt))


async def send_debug(message):
    events = fetch_freerolls()
    await message.channel.send(f"🔧 Debug: {len(events)} freeroll olvasva.")


async def send_test(message):
    await message.channel.send("🧪 Teszt OK! A bot fut.")


async def send_help(message):
    help_text = (
        "🃏 **Freeroll Bot Parancsok:**\n\n"
        "**!nap** - A következő 24 óra freerolljai\n"
        "**!kovetkezo** - A legközelebbi freeroll részletei\n"
        "**!teszt** - Bot működésének ellenőrzése\n"
        "**!help** - Ez a súgó üzenet\n\n"
        "A bot automatikusan figyeli a freerollokat és értesít:\n"
        "⏰ 1 órával a kezdés előtt\n"
        "🚨 10 perccel a kezdés előtt"
    )
    await message.channel.send(help_text)

# ------------------------------------------------------
# STATUS ROTATOR (presence ciklus)
# ------------------------------------------------------
STATUS_MESSAGES = cycle([
    "👹 Figyelem a freerollokat…",
    "🃏 Vadászat indul…",
    "💰 Botzilla aktív módban",
    "🧨 10 perces riasztások készen",
    "♠️ Új freeroll közeleg…"
])

async def status_rotator():
    await bot.wait_until_ready()
    while not bot.is_closed():
        current_status = next(STATUS_MESSAGES)
        await bot.change_presence(activity=discord.Game(name=current_status))
        await asyncio.sleep(20)

# ------------------------------------------------------
# WATCHER – Napi összesítő és figyelmeztetések
# ------------------------------------------------------
# Tároljuk az elküldött figyelmeztetéseket
# Kulcs: (datetime, name, alert_type) ahol alert_type: 'daily', '1hour', '10min'
SENT_ALERTS = set()

# Globálisan tárolt események a watcher-ből
GLOBAL_EVENTS: List[TournamentEvent] = []

async def watcher():
    global SENT_ALERTS, GLOBAL_EVENTS
    await bot.wait_until_ready()
    channel_obj = bot.get_channel(CHANNEL_ID)
    
    if channel_obj is None:
        print(f"Error: Channel with ID {CHANNEL_ID} not found")
        return
    
    # Type narrowing - ensure we have a text channel
    if not isinstance(channel_obj, (discord.TextChannel, discord.Thread)):
        print(f"Error: Channel {CHANNEL_ID} is not a text channel or thread")
        return
    
    channel = cast(Union[discord.TextChannel, discord.Thread], channel_obj)

    last_daily_send = None

    while True:
        events = fetch_freerolls()
        GLOBAL_EVENTS = events  # Tároljuk globálisan az eseményeket
        now = datetime.now()
        today = now.date()

        # Napi összesítő küldése (egyszer naponta)
        if last_daily_send is None or last_daily_send != today:
            # Következő 24 óra eseményei (most + 24 óra)
            next_24h_cutoff = now + timedelta(hours=24)
            next_24h = [e for e in events if now <= get_event_datetime(e) <= next_24h_cutoff]
            
            # Csak azokat küldjük el, amik az utolsó elküldött esemény után vannak
            unsent_events = [e for e in next_24h if event_is_after_last(e)]
            
            if unsent_events:
                await channel.send("📅 **Következő 24 óra freerolljai:**\n")
                for e in unsent_events:
                    await channel.send(fmt(e))
                # Az utolsó eseményt mentjük el
                if unsent_events:
                    save_last_event(unsent_events[-1])
                last_daily_send = today

        # Jövőbeli események figyelmeztetésekhez
        # Filter out all-day events from alerts (1h and 10min warnings)
        next_24h_cutoff = now + timedelta(hours=24)
        next_24h_timed = [e for e in events if not e['is_all_day'] and now <= get_event_datetime(e) <= next_24h_cutoff]
        
        role = None
        if isinstance(channel, discord.TextChannel) and channel.guild:
            role = discord.utils.get(channel.guild.roles, name="notif_poker")

        for nxt in next_24h_timed:
            delta = get_event_datetime(nxt) - now
            total_minutes = int(delta.total_seconds() / 60)

            # 1 órás figyelmeztetés (60 perc alatt van, de több mint 10 perc múlva kezdődik)
            if total_minutes < 60 and total_minutes > 10:
                event_key = (get_event_datetime(nxt), nxt["name"], '1hour')
                if event_key not in SENT_ALERTS:
                    SENT_ALERTS.add(event_key)
                    if role:
                        await channel.send(
                            f"{role.mention} ⏰ **{total_minutes} perc múlva indul!**\n\n" + fmt(nxt)
                        )
                    else:
                        await channel.send(
                            f"⏰ **{total_minutes} perc múlva indul!**\n\n" + fmt(nxt)
                        )

            # 10 perces figyelmeztetés (10 perc alatt van, de még nem küldtük el)
            if total_minutes < 10 and total_minutes >= 0:
                event_key = (get_event_datetime(nxt), nxt["name"], '10min')
                if event_key not in SENT_ALERTS:
                    SENT_ALERTS.add(event_key)
                    if role:
                        await channel.send(
                            f"{role.mention} 🚨 **FIGYELEM! {total_minutes} perc múlva indul!**\n\n" + fmt(nxt)
                        )
                    else:
                        await channel.send(
                            f"🚨 **FIGYELEM! {total_minutes} perc múlva indul!**\n\n" + fmt(nxt)
                        )

        # Memória tisztítás: töröljük a lejárt eseményeket
        cutoff_time = now - timedelta(hours=2)
        SENT_ALERTS = {
            (dt, name, alert_type) for (dt, name, alert_type) in SENT_ALERTS 
            if dt > cutoff_time
        }

        await asyncio.sleep(300)  # Várakozás 5 percig

# ------------------------------------------------------
# BOT EVENTS
# ------------------------------------------------------
@bot.event
async def on_ready():
    print("Bot online:", bot.user)

    asyncio.create_task(status_rotator())
    asyncio.create_task(watcher())


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    msg = message.content.lower()

    if msg == "!nap":
        await send_today(message)

    if msg == "!kovetkezo":
        await send_next(message)

    if msg == "!teszt":
        await send_test(message)

    if msg == "!help":
        await send_help(message)



bot.run(TOKEN)
