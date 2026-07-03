"""
02_generate_sales.py

Gera dados de vendas SIMULADOS, realistas, para os jogos já carregados
no banco (metadados reais via Steam). A simulação considera:

  - Preço base do jogo (jogos mais caros vendem menos unidades, mais receita/unidade)
  - Review score (jogos melhor avaliados vendem mais)
  - Idade do jogo (vendas decaem com o tempo, com picos em lançamento e sales sazonais)
  - Plataforma (Steam domina volume; consoles têm padrões próprios)
  - País (mercados maiores compram mais)

Isso gera uma distribuição que PARECE dados reais — não é uniforme/aleatória,
o que torna as queries de SQL e o dashboard de BI muito mais interessantes
de analisar (sazonalidade, outliers, tendências).

Requisitos:
    pip install psycopg2-binary python-dotenv numpy

.env esperado: igual ao 01_fetch_steam_games.py
"""
import os
import random
from datetime import date

import numpy as np
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

random.seed(42)
np.random.seed(42)

ANALYSIS_START = date(2023, 1, 1)
ANALYSIS_END = date(2025, 12, 31)

# Relative market share weights — Steam dominates PC digital sales
PLATFORM_WEIGHTS = {
    "Steam": 0.45,
    "Epic Games Store": 0.10,
    "GOG": 0.03,
    "PlayStation Store": 0.20,
    "Xbox Store": 0.14,
    "Nintendo eShop": 0.08,
}

# Relative market size weights by country (rough proxy for digital game spend)
COUNTRY_WEIGHTS = {
    "United States": 0.30,
    "China": 0.12,
    "Japan": 0.10,
    "Germany": 0.08,
    "United Kingdom": 0.07,
    "Brazil": 0.06,
    "France": 0.05,
    "Canada": 0.05,
    "South Korea": 0.04,
    "Australia": 0.03,
    "Poland": 0.03,
    "Mexico": 0.03,
    "Spain": 0.02,
    "Russia": 0.01,
    "India": 0.01,
}


def month_range(start: date, end: date):
    """Yield the first day of each month between start and end, inclusive."""
    current = date(start.year, start.month, 1)
    while current <= end:
        yield current
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)


def seasonal_multiplier(month: int) -> float:
    """Holiday sales spike in Nov/Dec, summer sale bump in June/July."""
    boosts = {6: 1.25, 7: 1.30, 11: 1.40, 12: 1.60}
    return boosts.get(month, 1.0)


def review_multiplier(pct: float | None) -> float:
    """Better reviews → more sales. Unreviewed games get a neutral multiplier."""
    if pct is None:
        return 0.7
    if pct >= 90:
        return 1.6
    if pct >= 80:
        return 1.3
    if pct >= 70:
        return 1.0
    if pct >= 60:
        return 0.7
    return 0.4


def age_decay(release_date: date, current_month: date) -> float:
    """Sales peak at launch month, then decay with a long tail."""
    if release_date is None:
        return 0.5
    months_since_release = (current_month.year - release_date.year) * 12 + \
                            (current_month.month - release_date.month)
    if months_since_release < 0:
        return 0.0  # game not released yet in this period
    if months_since_release == 0:
        return 3.0  # launch month spike
    if months_since_release <= 2:
        return 1.8
    if months_since_release <= 6:
        return 1.0
    if months_since_release <= 18:
        return 0.5
    return 0.25  # long tail, older games still sell a trickle


def price_to_base_units(price: float) -> int:
    """Cheaper games sell more units on average; expensive AAA titles sell fewer but pricier units."""
    if price <= 0:
        return 8000  # free-to-play proxy baseline (cosmetics-driven, kept simple)
    if price < 15:
        return 6000
    if price < 30:
        return 4000
    if price < 50:
        return 2500
    return 1500


def main():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # Valida que as dimensões já foram carregadas ANTES de truncar sales —
    # evita deixar a tabela vazia se o script rodar fora de ordem
    # (esperado: 01_schema.sql -> 02_seed_dimensions.sql -> 01_fetch_steam_games.py -> este script)
    cur.execute("SELECT game_id, base_price_usd, positive_review_pct, release_date FROM games")
    games = cur.fetchall()

    cur.execute("SELECT platform_id, name FROM platforms")
    platforms = cur.fetchall()

    cur.execute("SELECT country_id, name FROM countries")
    countries = cur.fetchall()

    if not games or not platforms or not countries:
        raise RuntimeError(
            "Dimensões vazias (games/platforms/countries). Rode nesta ordem: "
            "sql/01_schema.sql -> sql/02_seed_dimensions.sql -> "
            "python/01_fetch_steam_games.py -> python/02_generate_sales.py"
        )

    platform_ids = [p[0] for p in platforms]
    platform_names = [p[1] for p in platforms]
    platform_probs = [PLATFORM_WEIGHTS.get(n, 1 / len(platforms)) for n in platform_names]
    platform_probs = np.array(platform_probs) / sum(platform_probs)

    country_ids = [c[0] for c in countries]
    country_names = [c[1] for c in countries]
    country_probs = [COUNTRY_WEIGHTS.get(n, 1 / len(countries)) for n in country_names]
    country_probs = np.array(country_probs) / sum(country_probs)

    # Limpa a tabela para evitar duplicação ao executar o script novamente
    cur.execute("TRUNCATE TABLE sales RESTART IDENTITY;")
    conn.commit()

    rows_to_insert = []

    for game_id, price, review_pct, release_date in games:
        price = float(price) if price else 0.0
        base_units = price_to_base_units(price)
        rev_mult = review_multiplier(float(review_pct) if review_pct is not None else None)

        for month_start in month_range(ANALYSIS_START, ANALYSIS_END):
            decay = age_decay(release_date, month_start)
            if decay == 0.0:
                continue  # game not released yet

            season = seasonal_multiplier(month_start.month)
            month_total_units = base_units * decay * rev_mult * season
            month_total_units = max(0, int(np.random.normal(month_total_units, month_total_units * 0.15)))

            if month_total_units == 0:
                continue

            # Distribute this month's units across platforms (3-4 platforms get sales, not all 6)
            n_platforms = random.randint(2, 4)
            chosen_platform_idx = np.random.choice(
                len(platform_ids), size=n_platforms, replace=False,
                p=platform_probs
            )

            for p_idx in chosen_platform_idx:
                platform_id = platform_ids[p_idx]
                platform_share = platform_probs[p_idx] / platform_probs[chosen_platform_idx].sum()
                platform_units = max(1, int(month_total_units * platform_share))

                # Distribute platform's units across 3-6 countries
                n_countries = random.randint(3, 6)
                chosen_country_idx = np.random.choice(
                    len(country_ids), size=n_countries, replace=False,
                    p=country_probs
                )
                for c_idx in chosen_country_idx:
                    country_id = country_ids[c_idx]
                    country_share = country_probs[c_idx] / country_probs[chosen_country_idx].sum()
                    units = max(1, int(platform_units * country_share))

                    # Random day within the month for sale_date
                    day = random.randint(1, 28)
                    sale_date = date(month_start.year, month_start.month, day)

                    revenue = round(units * price, 2)

                    rows_to_insert.append((
                        game_id, platform_id, country_id, sale_date, units, revenue
                    ))

    print(f"Generated {len(rows_to_insert):,} sales rows. Inserting...")

    from psycopg2.extras import execute_values
    execute_values(
        cur,
        """
        INSERT INTO sales (game_id, platform_id, country_id, sale_date, units_sold, revenue_usd)
        VALUES %s
        """,
        rows_to_insert,
        page_size=1000,
    )
    conn.commit()

    cur.execute("SELECT COUNT(*), SUM(units_sold), SUM(revenue_usd) FROM sales")
    count, total_units, total_revenue = cur.fetchone()
    print(f"\nDone. Rows in sales table: {count:,}")
    print(f"Total units sold: {total_units:,}")
    print(f"Total revenue: ${total_revenue:,.2f}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
