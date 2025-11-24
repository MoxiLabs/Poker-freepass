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
from .parser import FreerollParser

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
def fetch_freerolls_password():
    """Fetch freerolls from freeroll-password.com"""
    try:
        r = requests.get(URL_PASSWORD, timeout=10)
    except:
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    wrapper = soup.select_one("div.pt-cv-wrapper")
    
    if not wrapper:
        return []

    events = []
    items = wrapper.select(".pt-cv-content-item")

    for item in items:
        try:
            excerpt = item.select_one(".fpexcerpt")
            if not excerpt:
                continue

            # Parse room
            room_span = excerpt.select_one(".exroom")
            room = "Unknown"
            if room_span and room_span.next_sibling:
                room = str(room_span.next_sibling).strip()

            # Parse date
            date_span = excerpt.select_one(".date-display-single")
            date_str = date_span.text.strip() if date_span else None

            # Parse time with timezone
            time_span = excerpt.select_one(".extime")
            time_str = None
            if time_span and time_span.next_sibling:
                time_str = str(time_span.next_sibling).strip()

            # Parse prize
            prize_span = excerpt.select_one(".exprize")
            prize = "n/a"
            if prize_span and prize_span.next_sibling:
                prize = str(prize_span.next_sibling).strip()

            # Parse name
            name_span = excerpt.select_one(".exname")
            name = "Unknown"
            if name_span and name_span.next_sibling:
                name = str(name_span.next_sibling).strip()

            # Parse password
            password_span = excerpt.select_one(".expass2")
            password = password_span.text.strip() if password_span else "n/a"

            # Parse datetime with timezone conversion
            if date_str and time_str:
                # Format: "November 24, 2025" and "22:30 GMT+2"
                # Extract timezone offset from time string
                tz_match = re.search(r'GMT([+-]\d+)', time_str)
                tz_offset = int(tz_match.group(1)) if tz_match else 0
                
                time_clean = time_str.split()[0]  # Get just HH:MM
                dt_str = f"{date_str} {time_clean}"
                dt_naive = datetime.strptime(dt_str, "%B %d, %Y %H:%M")
                
                # Create timezone-aware datetime
                source_tz = timezone(timedelta(hours=tz_offset))
                dt_aware = dt_naive.replace(tzinfo=source_tz)
                
                # Convert to Budapest time (GMT+1)
                budapest_tz = timezone(timedelta(hours=1))
                dt_budapest = dt_aware.astimezone(budapest_tz)
                
                events.append({
                    "datetime": dt_budapest.replace(tzinfo=None),  # Store as naive datetime in Budapest time
                    "room": room,
                    "name": name,
                    "prize": prize,
                    "password": password,
                    "source": "freeroll-password.com"
                })
        except Exception as e:
            continue

    return events


# ------------------------------------------------------
# SCRAPER – freerollpass.com
# ------------------------------------------------------
def fetch_freerolls_pass():
    """Fetch freerolls from freerollpass.com"""
    try:
        parser = FreerollParser(url=URL_PASS)
        tournaments = parser.get_tournaments()
    except:
        return []

    events = []
    for tournament in tournaments:
        try:
            # Parse date and time with timezone
            date_str = tournament.get('date')  # e.g., "24.11.2025"
            time_str = tournament.get('time')  # e.g., "21:00"
            tz_offset = tournament.get('timezone_offset', 1)  # Get calculated offset, default to GMT+1
            
            if not date_str or not time_str:
                continue

            # Combine date and time (date_str already contains the year)
            dt_str = f"{date_str} {time_str}"
            try:
                # Format: "24.11.2025 21:00"
                dt_naive = datetime.strptime(dt_str, "%d.%m.%Y %H:%M")
            except:
                try:
                    # Try alternative format: "11/24/2025 21:00"
                    dt_naive = datetime.strptime(dt_str, "%m/%d/%Y %H:%M")
                except:
                    continue

            # Create timezone-aware datetime with calculated offset
            source_tz = timezone(timedelta(hours=tz_offset))
            dt_aware = dt_naive.replace(tzinfo=source_tz)
            
            # Convert to Budapest time (GMT+1)
            budapest_tz = timezone(timedelta(hours=1))
            dt_budapest = dt_aware.astimezone(budapest_tz)

            # Get password
            password = tournament.get('password', 'n/a')
            if password is None:
                password = "not required"

            events.append({
                "datetime": dt_budapest.replace(tzinfo=None),  # Store as naive datetime in Budapest time
                "room": tournament.get('poker_room', 'Unknown'),
                "name": tournament.get('tournament_name', 'Unknown'),
                "prize": tournament.get('prize_pool', 'n/a'),
                "password": password,
                "source": "freerollpass.com"
            })
        except Exception as e:
            continue

    return events


# ------------------------------------------------------
# COMBINED SCRAPER
# ------------------------------------------------------
def fetch_freerolls():
    """Fetch freerolls from all sources and combine them"""
    events = []
    
    # Fetch from both sources
    events.extend(fetch_freerolls_password())
    events.extend(fetch_freerolls_pass())
    
    # Sort by datetime
    events.sort(key=lambda x: x["datetime"])
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

def save_last_event(event):
    """Save the last sent event to file"""
    event_data = {
        "datetime": event["datetime"].isoformat(),
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

def event_is_after_last(event):
    """Check if an event is after the last sent event"""
    last_event = load_last_event()
    if last_event is None:
        return True
    
    event_data = {
        "datetime": event["datetime"].isoformat(),
        "room": event["room"],
        "name": event["name"],
        "prize": event["prize"],
        "password": event["password"],
        "source": event.get("source", "n/a")
    }
    
    # Compare datetime to see if this event is newer
    return event_data["datetime"] > last_event["datetime"] or event_data != last_event

# ------------------------------------------------------
# FORMATTER
# ------------------------------------------------------
def fmt(e):
    source_emoji = "🌐" if e.get('source') == "freeroll-password.com" else "🎯"
    return (
        f"💰 **{e['name']}**\n"
        f"🏢 Terem: **{e['room']}**\n"
        f"💵 Díjazás: **{e['prize']}**\n"
        f"🕒 Kezdés: **{e['datetime'].strftime('%H:%M %d.%m.%Y')}**\n"
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
    next_24h = [e for e in events if now <= e["datetime"] <= next_24h_cutoff]

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
    future = [e for e in events if e["datetime"] > now]

    if not future:
        await message.channel.send("❌ Nincs közelgő freeroll.")
        return

    nxt = future[0]
    delta = nxt["datetime"] - now
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
GLOBAL_EVENTS = []

async def watcher():
    global SENT_ALERTS, GLOBAL_EVENTS
    await bot.wait_until_ready()
    channel = bot.get_channel(CHANNEL_ID)

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
            next_24h = [e for e in events if now <= e["datetime"] <= next_24h_cutoff]
            
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
        future = [e for e in events if e["datetime"] > now]
        role = discord.utils.get(channel.guild.roles, name="notif_poker")

        for nxt in future:
            delta = nxt["datetime"] - now
            total_minutes = int(delta.total_seconds() / 60)

            # 1 órás figyelmeztetés (60 perc alatt van, de több mint 10 perc múlva kezdődik)
            if total_minutes < 60 and total_minutes > 10:
                event_key = (nxt["datetime"], nxt["name"], '1hour')
                if event_key not in SENT_ALERTS:
                    SENT_ALERTS.add(event_key)
                    await channel.send(
                        f"{role.mention} ⏰ **{total_minutes} perc múlva indul!**\n\n" + fmt(nxt)
                    )

            # 10 perces figyelmeztetés (10 perc alatt van, de még nem küldtük el)
            if total_minutes < 10 and total_minutes >= 0:
                event_key = (nxt["datetime"], nxt["name"], '10min')
                if event_key not in SENT_ALERTS:
                    SENT_ALERTS.add(event_key)
                    await channel.send(
                        f"{role.mention} 🚨 **FIGYELEM! {total_minutes} perc múlva indul!**\n\n" + fmt(nxt)
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
