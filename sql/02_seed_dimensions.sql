-- ============================================================
-- SEED: Platforms
-- ============================================================
INSERT INTO platforms (name, company, launch_year, revenue_cut_pct) VALUES
('Steam',             'Valve',          2003, 30.00),
('Epic Games Store',  'Epic Games',     2018, 12.00),
('GOG',               'CD Projekt',     2008, 30.00),
('PlayStation Store', 'Sony',           2006, 30.00),
('Xbox Store',        'Microsoft',      2005, 30.00),
('Nintendo eShop',    'Nintendo',       2011, 30.00);

-- ============================================================
-- SEED: Countries
-- Top markets for digital game sales, by region
-- ============================================================
INSERT INTO countries (name, iso_code, region) VALUES
('United States',  'US', 'North America'),
('Brazil',         'BR', 'South America'),
('Germany',        'DE', 'Europe'),
('United Kingdom', 'GB', 'Europe'),
('France',         'FR', 'Europe'),
('Japan',          'JP', 'Asia'),
('South Korea',    'KR', 'Asia'),
('China',          'CN', 'Asia'),
('Canada',         'CA', 'North America'),
('Australia',      'AU', 'Oceania'),
('Mexico',         'MX', 'North America'),
('Poland',         'PL', 'Europe'),
('Russia',         'RU', 'Europe'),
('India',          'IN', 'Asia'),
('Spain',          'ES', 'Europe');

-- ============================================================
-- SEED: Genres
-- Standard Steam-style genre taxonomy
-- ============================================================
INSERT INTO genres (name) VALUES
('Action'),
('Adventure'),
('RPG'),
('Strategy'),
('Simulation'),
('Sports'),
('Racing'),
('FPS'),
('Survival'),
('Horror'),
('Puzzle'),
('Indie'),
('Massively Multiplayer'),
('Sandbox'),
('Platformer');
