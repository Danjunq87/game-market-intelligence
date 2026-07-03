"""
Export the current PostgreSQL database into two portable sample artifacts:

    data/sample_data.sql  - PostgreSQL INSERT dump, loadable right after
                             sql/01_schema.sql without running the Python
                             pipeline or hitting the Steam API.
    data/sample.db         - Self-contained SQLite copy of the same data,
                             for anyone who wants to browse the dataset
                             without installing PostgreSQL at all.

Usage:
    python python/03_export_sample_data.py

.env esperado: igual ao 01_fetch_steam_games.py
"""
import datetime
import decimal
import os
import sqlite3

import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "dbname": os.getenv("DB_NAME", "game_market_intelligence"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD"),
}

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
SQL_DUMP_PATH = os.path.join(OUTPUT_DIR, "sample_data.sql")
SQLITE_PATH = os.path.join(OUTPUT_DIR, "sample.db")

# Insert order respects foreign key dependencies.
TABLES = [
    "publishers",
    "developers",
    "genres",
    "platforms",
    "countries",
    "games",
    "game_genres",
    "sales",
]

SQLITE_SCHEMA = """
CREATE TABLE publishers (
    publisher_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    country TEXT,
    founded_year INTEGER
);

CREATE TABLE developers (
    developer_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    country TEXT
);

CREATE TABLE genres (
    genre_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE platforms (
    platform_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    company TEXT,
    launch_year INTEGER,
    revenue_cut_pct REAL
);

CREATE TABLE countries (
    country_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    iso_code TEXT,
    region TEXT
);

CREATE TABLE games (
    game_id INTEGER PRIMARY KEY,
    steam_appid INTEGER UNIQUE,
    title TEXT NOT NULL,
    publisher_id INTEGER REFERENCES publishers(publisher_id),
    developer_id INTEGER REFERENCES developers(developer_id),
    release_date TEXT,
    base_price_usd REAL,
    positive_review_pct REAL,
    is_indie INTEGER DEFAULT 0,
    created_at TEXT
);

CREATE TABLE game_genres (
    game_id INTEGER REFERENCES games(game_id),
    genre_id INTEGER REFERENCES genres(genre_id),
    PRIMARY KEY (game_id, genre_id)
);

CREATE TABLE sales (
    sale_id INTEGER PRIMARY KEY,
    game_id INTEGER NOT NULL REFERENCES games(game_id),
    platform_id INTEGER NOT NULL REFERENCES platforms(platform_id),
    country_id INTEGER NOT NULL REFERENCES countries(country_id),
    sale_date TEXT NOT NULL,
    units_sold INTEGER NOT NULL,
    revenue_usd REAL NOT NULL
);
"""


def fetch_rows(pg_cursor, table):
    pg_cursor.execute(f"SELECT * FROM {table} ORDER BY 1")
    columns = [desc[0] for desc in pg_cursor.description]
    return columns, pg_cursor.fetchall()


def write_sql_dump(pg_cursor):
    with open(SQL_DUMP_PATH, "w", encoding="utf-8") as f:
        f.write(
            "-- Sample data dump generated from a locally populated database.\n"
            "-- Load after sql/01_schema.sql to skip the Python/Steam API pipeline.\n\n"
        )
        for table in TABLES:
            columns, rows = fetch_rows(pg_cursor, table)
            if not rows:
                continue
            col_list = ", ".join(columns)
            f.write(f"-- {table} ({len(rows)} rows)\n")
            for i in range(0, len(rows), 500):
                chunk = rows[i : i + 500]
                values_sql = ",\n".join(
                    pg_cursor.mogrify("(" + ", ".join(["%s"] * len(columns)) + ")", row).decode(
                        "utf-8"
                    )
                    for row in chunk
                )
                f.write(f"INSERT INTO {table} ({col_list}) VALUES\n{values_sql};\n")
            f.write("\n")
    print(f"Wrote {SQL_DUMP_PATH}")


def sqlite_safe(value):
    if isinstance(value, decimal.Decimal):
        return float(value)
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    return value


def write_sqlite(pg_cursor):
    if os.path.exists(SQLITE_PATH):
        os.remove(SQLITE_PATH)
    conn = sqlite3.connect(SQLITE_PATH)
    conn.executescript(SQLITE_SCHEMA)
    for table in TABLES:
        columns, rows = fetch_rows(pg_cursor, table)
        if not rows:
            continue
        placeholders = ", ".join(["?"] * len(columns))
        col_list = ", ".join(columns)
        safe_rows = [tuple(sqlite_safe(v) for v in row) for row in rows]
        conn.executemany(
            f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})", safe_rows
        )
    conn.commit()
    conn.close()
    print(f"Wrote {SQLITE_PATH}")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    write_sql_dump(cur)
    write_sqlite(cur)
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
