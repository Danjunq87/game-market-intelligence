"""
01_fetch_steam_games.py

Coleta metadados REAIS de jogos via Steam Store API (appdetails endpoint)
e insere em PostgreSQL: publishers, developers, genres, games, game_genres.

A tabela `sales` NÃO é populada aqui — ela é gerada separadamente como
dado simulado (ver 02_generate_sales.py).

Requisitos:
    pip install requests psycopg2-binary python-dotenv tqdm

.env esperado:
    DB_HOST=localhost
    DB_PORT=5432
    DB_NAME=game_market_intelligence
    DB_USER=postgres
    DB_PASSWORD=your_password
"""
import os
import time
import requests
import psycopg2
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "dbname": os.getenv("DB_NAME", "game_market_intelligence"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD"),
}

# Lista curada de App IDs da Steam — jogos verificados, cobrindo
# múltiplos publishers/gêneros/anos para um dataset variado e
# representativo do mercado (AAA + indie, vários gêneros).
STEAM_APP_IDS = [
    1091500,   # Cyberpunk 2077 — CD Projekt
    1245620,   # Elden Ring — Bandai Namco
    1145360,   # Hades — Supergiant Games
    570,       # Dota 2 — Valve
    730,       # Counter-Strike 2 — Valve
    1086940,   # Baldur's Gate 3 — Larian / Hasbro
    271590,    # Grand Theft Auto V — Rockstar / Take-Two
    1172470,   # Apex Legends — EA
    359550,    # Rainbow Six Siege — Ubisoft
    413150,    # Stardew Valley — ConcernedApe
    105600,    # Terraria — Re-Logic
    632360,    # Risk of Rain 2 — Gearbox
    1174180,   # Red Dead Redemption 2 — Rockstar / Take-Two
    292030,    # The Witcher 3: Wild Hunt — CD Projekt
    374320,    # Dark Souls III — Bandai Namco
    582010,    # Monster Hunter: World — Capcom
    489830,    # The Elder Scrolls V: Skyrim Special Edition — Bethesda
    346110,    # ARK: Survival Evolved — Studio Wildcard
    230410,    # Warframe — Digital Extremes
    252490,    # Rust — Facepunch Studios
    304930,    # Unturned — Smartly Dressed Games
    1426210,   # It Takes Two — EA
    1551360,   # Forza Horizon 5 — Xbox Game Studios
    1097150,   # Fall Guys — Epic Games
    367520,    # Hollow Knight — Team Cherry
    646570,    # Slay the Spire — Mega Crit
    1794680,   # Vampire Survivors — poncle
    1716740,   # Starfield — Bethesda
    1086940,   # (dup safe — removed below by set())
    1517290,   # Battlefield 2042 — EA
    1238810,   # Battlefield V — EA
    1238840,   # Battlefield 1 — EA
    1888160,   # Diablo IV — Blizzard
    1942280,   # Lethal Company — Zeekerss
    1623730,   # Palworld — Pocketpair
    1903340,   # Helldivers 2 — Sony / Arrowhead
    2050650,   # Resident Evil 4 — Capcom
    1599340,   # Lost Ark — Amazon Games
    1222670,   # The Sims 4 — EA
    1085660,   # Destiny 2 — Bungie
]
STEAM_APP_IDS = sorted(set(STEAM_APP_IDS))

STEAM_API_URL = "https://store.steampowered.com/api/appdetails"


def fetch_game_details(appid: int) -> dict | None:
    """Fetch a single game's metadata from the Steam Store API."""
    try:
        resp = requests.get(
            STEAM_API_URL,
            params={"appids": appid, "cc": "us", "l": "english"},
            timeout=10,
        )
        resp.raise_for_status()
        payload = resp.json().get(str(appid))
        if not payload or not payload.get("success"):
            return None
        return payload["data"]
    except (requests.RequestException, ValueError):
        return None


def fetch_review_summary(appid: int) -> float | None:
    """Fetch positive review percentage from the Steam reviews endpoint."""
    try:
        resp = requests.get(
            f"https://store.steampowered.com/appreviews/{appid}",
            params={"json": 1, "language": "all", "purchase_type": "all"},
            timeout=10,
        )
        resp.raise_for_status()
        summary = resp.json().get("query_summary", {})
        total = summary.get("total_reviews", 0)
        positive = summary.get("total_positive", 0)
        if total == 0:
            return None
        return round(positive / total * 100, 2)
    except (requests.RequestException, ValueError):
        return None


def get_or_create(cur, table: str, id_col: str, name_col: str, name: str, extra_cols: dict | None = None) -> int:
    """Generic upsert helper: returns the id of an existing or newly created row."""
    cur.execute(f"SELECT {id_col} FROM {table} WHERE {name_col} = %s", (name,))
    row = cur.fetchone()
    if row:
        return row[0]

    cols = [name_col]
    vals = [name]
    if extra_cols:
        cols += list(extra_cols.keys())
        vals += list(extra_cols.values())

    placeholders = ", ".join(["%s"] * len(vals))
    col_names = ", ".join(cols)
    cur.execute(
        f"INSERT INTO {table} ({col_names}) VALUES ({placeholders}) RETURNING {id_col}",
        vals,
    )
    return cur.fetchone()[0]


def main():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    inserted, skipped = 0, 0

    for appid in tqdm(STEAM_APP_IDS, desc="Fetching Steam games"):
        data = fetch_game_details(appid)
        time.sleep(1.2)  # Steam rate-limits aggressively — be polite

        if not data or data.get("type") != "game":
            skipped += 1
            continue

        title = data.get("name", "").strip()
        if not title:
            skipped += 1
            continue

        # Skip if already loaded (idempotent re-runs)
        cur.execute("SELECT 1 FROM games WHERE steam_appid = %s", (appid,))
        if cur.fetchone():
            skipped += 1
            continue

        publishers = data.get("publishers") or ["Unknown"]
        developers = data.get("developers") or ["Unknown"]
        genres = [g["description"] for g in data.get("genres", [])]
        is_indie = "Indie" in genres

        price_overview = data.get("price_overview", {})
        base_price = price_overview.get("initial", 0) / 100 if price_overview else 0.0

        release_date_raw = data.get("release_date", {}).get("date", "")
        release_date = parse_steam_date(release_date_raw)

        review_pct = fetch_review_summary(appid)
        time.sleep(1.0)

        publisher_id = get_or_create(cur, "publishers", "publisher_id", "name", publishers[0])
        developer_id = get_or_create(cur, "developers", "developer_id", "name", developers[0])

        cur.execute(
            """
            INSERT INTO games
                (steam_appid, title, publisher_id, developer_id,
                 release_date, base_price_usd, positive_review_pct, is_indie)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING game_id
            """,
            (appid, title, publisher_id, developer_id,
             release_date, base_price, review_pct, is_indie),
        )
        game_id = cur.fetchone()[0]

        for genre_name in genres:
            genre_id = get_or_create(cur, "genres", "genre_id", "name", genre_name)
            cur.execute(
                "INSERT INTO game_genres (game_id, genre_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (game_id, genre_id),
            )

        conn.commit()
        inserted += 1

    cur.close()
    conn.close()
    print(f"\nDone. Inserted: {inserted} | Skipped: {skipped}")


def parse_steam_date(raw: str):
    """Steam dates come as 'DD Mon, YYYY' or 'Mon DD, YYYY' — best-effort parse."""
    from datetime import datetime
    formats = ["%d %b, %Y", "%b %d, %Y"]
    for fmt in formats:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


if __name__ == "__main__":
    main()
