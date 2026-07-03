-- ============================================================
-- GAME MARKET INTELLIGENCE — Database Schema
-- PostgreSQL 15+
--
-- Design: Star Schema
--   - Dimension tables: games, publishers, developers, genres,
--     platforms, countries
--   - Fact table: sales
--
-- Run order: this file first, then 02_seed_dimensions.sql,
-- then python/01_fetch_steam_games.py (games), then
-- python/02_generate_sales.py (sales). 03_business_queries.sql
-- is read-only and can be run any time after that.
-- ============================================================

DROP TABLE IF EXISTS sales CASCADE;
DROP TABLE IF EXISTS game_genres CASCADE;
DROP TABLE IF EXISTS games CASCADE;
DROP TABLE IF EXISTS publishers CASCADE;
DROP TABLE IF EXISTS developers CASCADE;
DROP TABLE IF EXISTS genres CASCADE;
DROP TABLE IF EXISTS platforms CASCADE;
DROP TABLE IF EXISTS countries CASCADE;

-- ============================================================
-- DIMENSION: Publishers
-- ============================================================
CREATE TABLE publishers (
    publisher_id    SERIAL PRIMARY KEY,
    name            VARCHAR(150) NOT NULL UNIQUE,
    country         VARCHAR(100),
    founded_year    INT
);

-- ============================================================
-- DIMENSION: Developers
-- ============================================================
CREATE TABLE developers (
    developer_id    SERIAL PRIMARY KEY,
    name            VARCHAR(150) NOT NULL UNIQUE,
    country         VARCHAR(100)
);

-- ============================================================
-- DIMENSION: Genres
-- ============================================================
CREATE TABLE genres (
    genre_id        SERIAL PRIMARY KEY,
    name            VARCHAR(100) NOT NULL UNIQUE
);

-- ============================================================
-- DIMENSION: Platforms
-- ============================================================
CREATE TABLE platforms (
    platform_id     SERIAL PRIMARY KEY,
    name            VARCHAR(100) NOT NULL UNIQUE,
    company         VARCHAR(100),         -- Valve, Epic Games, Sony, etc.
    launch_year     INT,
    revenue_cut_pct NUMERIC(5,2)          -- platform's typical cut, e.g. 30.00 for Steam
);

-- ============================================================
-- DIMENSION: Countries
-- ============================================================
CREATE TABLE countries (
    country_id      SERIAL PRIMARY KEY,
    name            VARCHAR(100) NOT NULL UNIQUE,
    iso_code        CHAR(2),
    region          VARCHAR(50)            -- North America, Europe, Asia, etc.
);

-- ============================================================
-- DIMENSION: Games
-- Real metadata sourced from Steam (title, publisher, genre,
-- price, release date, review score)
-- ============================================================
CREATE TABLE games (
    game_id             SERIAL PRIMARY KEY,
    steam_appid         INT UNIQUE,             -- original Steam app id, for traceability
    title               VARCHAR(255) NOT NULL,
    publisher_id        INT REFERENCES publishers(publisher_id),
    developer_id        INT REFERENCES developers(developer_id),
    release_date        DATE,
    base_price_usd      NUMERIC(10,2),
    positive_review_pct NUMERIC(5,2),
    is_indie            BOOLEAN DEFAULT FALSE,
    created_at          TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- BRIDGE: Game ↔ Genre (many-to-many — a game can have multiple genres)
-- ============================================================
CREATE TABLE game_genres (
    game_id     INT REFERENCES games(game_id) ON DELETE CASCADE,
    genre_id    INT REFERENCES genres(genre_id) ON DELETE CASCADE,
    PRIMARY KEY (game_id, genre_id)
);

-- ============================================================
-- FACT: Sales
-- Simulated data — one row per game/platform/country/month
-- ============================================================
CREATE TABLE sales (
    sale_id         BIGSERIAL PRIMARY KEY,
    game_id         INT NOT NULL REFERENCES games(game_id),
    platform_id     INT NOT NULL REFERENCES platforms(platform_id),
    country_id      INT NOT NULL REFERENCES countries(country_id),
    sale_date        DATE NOT NULL,
    units_sold       INT NOT NULL CHECK (units_sold >= 0),
    revenue_usd      NUMERIC(14,2) NOT NULL CHECK (revenue_usd >= 0)
);

-- ============================================================
-- INDEXES — critical for query performance on the fact table
-- ============================================================
CREATE INDEX idx_sales_game        ON sales(game_id);
CREATE INDEX idx_sales_platform    ON sales(platform_id);
CREATE INDEX idx_sales_country     ON sales(country_id);
CREATE INDEX idx_sales_date        ON sales(sale_date);
CREATE INDEX idx_sales_date_game   ON sales(sale_date, game_id);

CREATE INDEX idx_games_publisher   ON games(publisher_id);
CREATE INDEX idx_games_developer   ON games(developer_id);
CREATE INDEX idx_games_release     ON games(release_date);

-- ============================================================
-- COMMENTS — document the schema for anyone reading it
-- ============================================================
COMMENT ON TABLE sales IS 'Fact table: simulated sales data for educational/portfolio purposes. Game metadata is real (sourced from Steam).';
COMMENT ON COLUMN games.steam_appid IS 'Original Steam App ID — kept for traceability to source data.';
COMMENT ON COLUMN platforms.revenue_cut_pct IS 'Typical platform revenue share (e.g. Steam takes 30%).';
