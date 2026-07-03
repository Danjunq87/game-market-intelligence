-- ============================================================
-- GAME MARKET INTELLIGENCE — Business Queries
-- Organized by business question. Demonstrates: JOINs, CTEs,
-- Window Functions, Aggregations, Views.
-- ============================================================


-- ============================================================
-- 1. Qual plataforma vende mais? (volume e receita)
-- ============================================================
SELECT
    p.name                          AS platform,
    SUM(s.units_sold)               AS total_units,
    SUM(s.revenue_usd)              AS total_revenue,
    ROUND(SUM(s.revenue_usd) / NULLIF(SUM(s.units_sold), 0), 2) AS avg_price_per_unit
FROM sales s
JOIN platforms p ON p.platform_id = s.platform_id
GROUP BY p.name
ORDER BY total_revenue DESC;


-- ============================================================
-- 2. Qual publisher gera mais receita?
-- ============================================================
SELECT
    pub.name                        AS publisher,
    COUNT(DISTINCT g.game_id)       AS games_published,
    SUM(s.units_sold)               AS total_units,
    SUM(s.revenue_usd)              AS total_revenue,
    ROUND(SUM(s.revenue_usd) / COUNT(DISTINCT g.game_id), 2) AS avg_revenue_per_game
FROM sales s
JOIN games g       ON g.game_id = s.game_id
JOIN publishers pub ON pub.publisher_id = g.publisher_id
GROUP BY pub.name
ORDER BY total_revenue DESC
LIMIT 20;


-- ============================================================
-- 3. Qual gênero vende melhor em cada plataforma?
-- Uses window function RANK() to find the top genre per platform.
-- ============================================================
WITH genre_platform_sales AS (
    SELECT
        pl.name                     AS platform,
        gen.name                    AS genre,
        SUM(s.revenue_usd)          AS revenue
    FROM sales s
    JOIN platforms pl    ON pl.platform_id = s.platform_id
    JOIN games g         ON g.game_id = s.game_id
    JOIN game_genres gg  ON gg.game_id = g.game_id
    JOIN genres gen      ON gen.genre_id = gg.genre_id
    GROUP BY pl.name, gen.name
),
ranked AS (
    SELECT
        platform,
        genre,
        revenue,
        RANK() OVER (PARTITION BY platform ORDER BY revenue DESC) AS genre_rank
    FROM genre_platform_sales
)
SELECT platform, genre, revenue
FROM ranked
WHERE genre_rank = 1
ORDER BY revenue DESC;


-- ============================================================
-- 4. Receita por país
-- ============================================================
SELECT
    c.name                          AS country,
    c.region,
    SUM(s.units_sold)               AS total_units,
    SUM(s.revenue_usd)              AS total_revenue,
    ROUND(100.0 * SUM(s.revenue_usd) / SUM(SUM(s.revenue_usd)) OVER (), 2) AS pct_of_total_revenue
FROM sales s
JOIN countries c ON c.country_id = s.country_id
GROUP BY c.name, c.region
ORDER BY total_revenue DESC;


-- ============================================================
-- 5. Receita por trimestre
-- ============================================================
SELECT
    DATE_TRUNC('quarter', s.sale_date)::DATE AS quarter_start,
    EXTRACT(YEAR FROM s.sale_date)            AS year,
    EXTRACT(QUARTER FROM s.sale_date)         AS quarter,
    SUM(s.units_sold)                          AS total_units,
    SUM(s.revenue_usd)                         AS total_revenue
FROM sales s
GROUP BY quarter_start, year, quarter
ORDER BY quarter_start;


-- ============================================================
-- 6. Crescimento mensal (Month-over-Month %)
-- Uses LAG() window function to compare to the previous month.
-- ============================================================
WITH monthly_revenue AS (
    SELECT
        DATE_TRUNC('month', sale_date)::DATE AS month,
        SUM(revenue_usd)                      AS revenue
    FROM sales
    GROUP BY DATE_TRUNC('month', sale_date)
)
SELECT
    month,
    revenue,
    LAG(revenue) OVER (ORDER BY month)        AS prev_month_revenue,
    ROUND(
        100.0 * (revenue - LAG(revenue) OVER (ORDER BY month))
        / NULLIF(LAG(revenue) OVER (ORDER BY month), 0),
        2
    ) AS mom_growth_pct
FROM monthly_revenue
ORDER BY month;


-- ============================================================
-- 7. Ticket médio (Average Revenue Per Unit) — geral e por plataforma
-- ============================================================
SELECT
    'Overall' AS scope,
    ROUND(SUM(revenue_usd) / NULLIF(SUM(units_sold), 0), 2) AS avg_ticket
FROM sales

UNION ALL

SELECT
    p.name AS scope,
    ROUND(SUM(s.revenue_usd) / NULLIF(SUM(s.units_sold), 0), 2) AS avg_ticket
FROM sales s
JOIN platforms p ON p.platform_id = s.platform_id
GROUP BY p.name
ORDER BY avg_ticket DESC;


-- ============================================================
-- 8. Top 10 jogos por receita total — com publisher e gênero principal
-- Uses CTE + STRING_AGG to flatten multi-genre games into one row.
-- ============================================================
WITH game_genre_list AS (
    SELECT
        g.game_id,
        STRING_AGG(gen.name, ', ' ORDER BY gen.name) AS genres
    FROM games g
    JOIN game_genres gg ON gg.game_id = g.game_id
    JOIN genres gen     ON gen.genre_id = gg.genre_id
    GROUP BY g.game_id
)
SELECT
    g.title,
    pub.name                AS publisher,
    ggl.genres,
    g.base_price_usd,
    g.positive_review_pct,
    SUM(s.units_sold)       AS total_units,
    SUM(s.revenue_usd)      AS total_revenue
FROM sales s
JOIN games g          ON g.game_id = s.game_id
JOIN publishers pub   ON pub.publisher_id = g.publisher_id
LEFT JOIN game_genre_list ggl ON ggl.game_id = g.game_id
GROUP BY g.title, pub.name, ggl.genres, g.base_price_usd, g.positive_review_pct
ORDER BY total_revenue DESC
LIMIT 10;


-- ============================================================
-- 9. Indie vs AAA — comparação de performance
-- ============================================================
SELECT
    CASE WHEN g.is_indie THEN 'Indie' ELSE 'Non-Indie' END AS category,
    COUNT(DISTINCT g.game_id)        AS games_count,
    SUM(s.units_sold)                AS total_units,
    SUM(s.revenue_usd)               AS total_revenue,
    ROUND(AVG(g.positive_review_pct), 1) AS avg_review_score,
    ROUND(SUM(s.revenue_usd) / COUNT(DISTINCT g.game_id), 2) AS avg_revenue_per_game
FROM sales s
JOIN games g ON g.game_id = s.game_id
GROUP BY g.is_indie
ORDER BY total_revenue DESC;


-- ============================================================
-- 10. Jogos com melhor relação review score x receita
-- (identifica jogos "subestimados": ótima nota, baixa receita)
-- ============================================================
WITH game_totals AS (
    SELECT
        g.game_id,
        g.title,
        g.positive_review_pct,
        SUM(s.revenue_usd) AS total_revenue
    FROM sales s
    JOIN games g ON g.game_id = s.game_id
    WHERE g.positive_review_pct IS NOT NULL
    GROUP BY g.game_id, g.title, g.positive_review_pct
),
percentiles AS (
    SELECT
        *,
        PERCENT_RANK() OVER (ORDER BY total_revenue) AS revenue_percentile
    FROM game_totals
)
SELECT title, positive_review_pct, total_revenue, ROUND(revenue_percentile::NUMERIC, 2) AS revenue_percentile
FROM percentiles
WHERE positive_review_pct >= 90
ORDER BY revenue_percentile ASC
LIMIT 10;


-- ============================================================
-- 11. VIEW: Executive Summary
-- A reusable view for the Power BI executive dashboard page —
-- pre-aggregates the core KPIs so the BI tool queries less data.
-- ============================================================
CREATE OR REPLACE VIEW vw_executive_summary AS
SELECT
    DATE_TRUNC('month', s.sale_date)::DATE AS month,
    p.name                                  AS platform,
    c.name                                  AS country,
    g.title                                 AS game_title,
    pub.name                                AS publisher,
    g.is_indie,
    g.positive_review_pct,
    s.units_sold,
    s.revenue_usd
FROM sales s
JOIN games g       ON g.game_id = s.game_id
JOIN platforms p   ON p.platform_id = s.platform_id
JOIN countries c   ON c.country_id = s.country_id
JOIN publishers pub ON pub.publisher_id = g.publisher_id;

-- Power BI connects directly to this view for the Executive Dashboard page.


-- ============================================================
-- 12. VIEW: Platform Performance (for Power BI page 2)
-- ============================================================
CREATE OR REPLACE VIEW vw_platform_performance AS
SELECT
    p.name                          AS platform,
    DATE_TRUNC('quarter', s.sale_date)::DATE AS quarter,
    SUM(s.units_sold)               AS units_sold,
    SUM(s.revenue_usd)              AS revenue,
    COUNT(DISTINCT s.game_id)       AS distinct_games_sold
FROM sales s
JOIN platforms p ON p.platform_id = s.platform_id
GROUP BY p.name, quarter;


-- ============================================================
-- 13. VIEW: Genre Revenue (for Power BI Genres page)
-- ============================================================
CREATE OR REPLACE VIEW vw_genre_revenue AS
SELECT
    gen.name                        AS genre,
    SUM(s.revenue_usd)              AS revenue_usd,
    SUM(s.units_sold)               AS units_sold
FROM sales s
JOIN games g         ON g.game_id = s.game_id
JOIN game_genres gg  ON gg.game_id = g.game_id
JOIN genres gen      ON gen.genre_id = gg.genre_id
GROUP BY gen.name;
