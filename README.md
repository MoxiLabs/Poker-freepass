# Poker Freeroll Bot

Discord bot a poker freeroll tornák automatikus figyelésére és értesítésére.

## Leírás

Ez a bot automatikusan figyeli a poker freeroll tornákat két forrásból:
- freeroll-password.com
- freerollpass.com

A bot Discord-on keresztül értesít a közelgő tornákról, és különböző parancsokkal lekérdezhetők az aktuális események.

## Features

- Automatikus freeroll figyelés és értesítések
- Napi összesítő a következő 24 óráról
- Értesítések 1 órával és 10 perccel a kezdés előtt
- Discord parancsok a tornák lekérdezésére
- Időzóna kezelés (Budapest idő)
- Két különböző forrás aggregálása

## Telepítés fps.ms platformra

### 1. Konfiguráció beállítása

Hozz létre egy `config.json` fájlt a projekt gyökérkönyvtárában a `config.example.json` alapján:

```bash
cp config.example.json config.json
```

Szerkeszd a `config.json` fájlt és add meg a saját Discord token-edet és channel ID-t:

```json
{
  "discord_token": "YOUR_DISCORD_BOT_TOKEN",
  "channel_id": YOUR_CHANNEL_ID
}
```

**Fontos:** A `config.json` fájl a `.gitignore`-ban van, így nem kerül fel verziókezelésre. Ezt a fájlt manuálisan kell feltöltened az fps.ms szerverre!

### 2. Fájlok feltöltése fps.ms-re

1. Jelentkezz be az [fps.ms panelre](https://panel.fps.ms/)
2. Navigálj a Files (Fájlok) tabra
3. Töltsd fel az összes fájlt, **beleértve a `config.json` fájlt is**
4. Ellenőrizd, hogy a következő fájlok megtalálhatók:
   - `app.py` (ez a futtatási pont az fps.ms-nek)
   - `config.json` (az éles token-nel)
   - `requirements.txt`
   - `pokerparser/` mappa az összes Python fájllal

### 3. Dependencies telepítése

Az fps.ms automatikusan telepíti a `requirements.txt`-ben megadott csomagokat.

### 4. Bot indítása

Az fps.ms automatikusan elindítja az `app.py` fájlt. Ha manuálisan szeretnéd indítani:

```bash
python app.py
```

## Biztonsági megjegyzések

- **SOHA ne commitáld a `config.json` fájlt** a git repository-ba!
- A `config.example.json` csak sablonként szolgál, ne írj bele éles adatokat
- Az fps.ms-en a `config.json` fájlt az SFTP-n keresztül kell feltölteni
- Ha meg szeretnéd változtatni a token-t, csak a `config.json` fájlt kell szerkeszteni az fps.ms Files tabján vagy SFTP-n keresztül

## Lokális fejlesztés

Lokális fejlesztéshez hozz létre egy `config.json` fájlt:

```bash
cp config.example.json config.json
```

Majd add meg a tesztelési token-t és channel ID-t.

Futtatás lokálisan:

```bash
python -m pokerparser.discordbot
```

Vagy egyszerűen:

```bash
python app.py
```

## Discord parancsok

- `!nap` - A következő 24 óra freerolljai
- `!kovetkezo` - A legközelebbi freeroll részletei  
- `!teszt` - Bot működésének ellenőrzése
- `!help` - Súgó üzenet

## Automatikus értesítések

A bot automatikusan figyeli a freerollokat és értesít:
- 📅 Napi összesítő a következő 24 óra eseményeiről
- ⏰ 1 órával a kezdés előtt
- 🚨 10 perccel a kezdés előtt

Az értesítések a `@notif_poker` szerepkört említik.

## Requirements

- Python 3.7+
- beautifulsoup4
- requests
- lxml
- discord.py
