#🎮 Game Market Intelligence | PostgreSQL + Python + Power BI

An end-to-end Data Analytics project that simulates digital game sales across multiple gaming platforms.

The project combines **real game metadata collected from the Steam Store API** with **simulated sales data** to build a complete Business Intelligence solution using **Python, PostgreSQL, SQL and Power BI**.

---

# Project Overview

This project answers common business questions from the video game industry, including:

- Which platform generates the most revenue?
- Which publishers perform the best?
- Which genres sell better on each platform?
- Revenue by country.
- Revenue by quarter.
- Monthly growth.
- Average ticket size.
- Top-performing games.

---

# Tech Stack

- Python
- PostgreSQL
- SQL
- Power BI
- Git
- GitHub

---

# Data Sources

### Real Data

Game metadata are collected from the Steam Store API.

Collected fields include:

- Title
- Publisher
- Developer
- Genres
- Release Date
- Base Price
- Positive Review Score

### Simulated Data

Sales data were generated for educational purposes.

The simulation considers:

- Platform market share
- Country market size
- Review score
- Game age
- Seasonal sales
- Game price

---

# Database Model

Star Schema

Fact Table

- Sales

Dimension Tables

- Games
- Publishers
- Developers
- Platforms
- Countries
- Genres

---

# Business Questions

The SQL scripts answer questions such as:

- Top revenue platform
- Top publishers
- Best-selling genres
- Revenue by country
- Revenue by quarter
- Monthly growth
- Average ticket
- Top games by revenue
- Indie vs AAA comparison

---

# Project Structure

```text
game-market-intelligence/

├── python/
│   ├── 01_fetch_steam_games.py
│   └── 02_generate_sales.py
│
├── sql/
│   ├── 01_schema.sql
│   ├── 02_seed_dimensions.sql
│   └── 03_business_queries.sql
│
├── powerbi/
│   └── game-market-intelligence.pbix
│
├── docs/
│
├── requirements.txt
├── .env.example
└── README.md
```

---

# Skills Demonstrated

- Data Modeling
- ETL Development
- REST API Integration
- SQL Query Optimization
- Window Functions
- Common Table Expressions (CTEs)
- PostgreSQL
- Business Intelligence
- Power BI Dashboard Development

---

# Dashboard

Dashboard screenshots will be added after the Power BI report is completed.

---

# Future Improvements

- Add more Steam games
- Add a Date Dimension
- Add discount simulation
- Add refunds simulation
- Add DLC sales
- Add regional pricing

---

# Disclaimer

Game metadata come from public Steam data.

Sales data are **simulated for educational and portfolio purposes**.