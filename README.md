# CR Series Tracker

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)
![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)

A full-stack application to track and analyze Best-of-7 series for 2v2 Touchdown Draft games in Clash Royale.

This project automatically fetches game data from the official Clash Royale API, detects series, calculates player Elo ratings, and presents detailed statistics through a clean, data-rich web interface.

**Live Demo:** [compound-cr.com](https://compound-cr.com)

---

## Key Features

- **Automatic Series Detection**: Groups games into sessions and identifies completed Best-of-7 series.
- **Elo Rating System**: Implements a standard Elo rating system to track player skill over time.
- **Comprehensive Statistics**: Provides detailed stats for players, cards, and head-to-head matchups.
- **Data-Rich Frontend**: A responsive single-page application built with vanilla JavaScript and styled with Tailwind CSS to visualize all the data.
- **Scheduled Data Ingestion**: Automatically fetches the latest games periodically to keep the database up-to-date.
- **RESTful API**: A complete backend API built with FastAPI to serve all processed data.

## Tech Stack

- **Backend**: Python, FastAPI, SQLAlchemy
- **Database**: SQLite
- **Frontend**: HTML, Tailwind CSS, Vanilla JavaScript
- **Scheduling**: APScheduler
- **API Client**: `requests`

## Setup and Installation

Follow these steps to get the project running locally.

### 1. Clone the Repository

```bash
git clone https://github.com/cbolson22/cr-series-tracker.git
cd cr-series-tracker
```

### 2. Set up the Python Environment

A virtual environment is recommended.

```bash
python3 -m venv .venv
source .venv/bin/activate
# On Windows, use: .venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a file named `.env` in the project root and add the following variables. This file stores your secret keys and configuration.

**.env.example**

```env
# Your developer token from the Clash Royale API website
CR_TOKEN=your_clash_royale_api_token

# The clan tag to monitor for games
CLAN_TAG=#YOURCLANTAG

# Comma-separated list of player tags to track (no spaces)
PLAYER_TAGS=#TAG1,#TAG2,#TAG3,#TAG4,#TAG5,#TAG6,#TAG7,#TAG8

# Comma-separated list of corresponding player names (must be in the same order as tags)
PLAYER_NAMES=Name1,Name2,Name3,Name4,Name5,Name6,Name7,Name8

# (Optional) Database URL, defaults to a local SQLite file
# DATABASE_URL="sqlite:///./cr_series.db"

# (Optional) Max time gap between games to be considered part of the same session
# SESSION_MAX_GAP_MINUTES=30
```

### 5. Initialize the Database

This command creates the database schema based on the defined models.

```bash
python3 -c "from backend.db import engine, Base; from backend import models; Base.metadata.create_all(bind=engine)"
```

### 6. Seed Player Information

This script populates the `players` table with the tags and names from your `.env` file.

```bash
python3 -m backend.seed_players
```

## Running the Application

### Fetch Initial Data

Run `fetch_once.py` to populate the database with the most recent games, detect any initial series, and recompute Elo ratings.

```bash
python3 -m scripts.fetch_once
```

### Run the Backend API Server

This will start the FastAPI server.

```bash
uvicorn backend.api:app --reload --port 8000
```

You can now view the API documentation at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

### View the Frontend

Simply open the `frontend/index.html` file in your web browser. It will automatically connect to the local API server.

## Maintenance Scripts

The `scripts/` directory contains useful scripts for data management:

- `fetch_once.py`: Fetches recent games, updates series, and rebuilds Elo ratings if new games are found. Ideal for running on a cron job if you don't use the built-in scheduler.
- `recompute.py`: Re-processes all games in the database to detect series. Useful if you change the series detection logic.
- `recompute_elo.py`: Recalculates all Elo ratings from scratch based on the existing series data.

The project also includes a built-in scheduler that fetches games, detects series, and **rebuilds Elo ratings** automatically every 20 minutes.

```bash
python3 -m backend.scheduler
```

---

<details>
<summary><strong>API Endpoints</strong></summary>

- `GET /health`: Health check.
- `GET /last-update`: Timestamp of the last recorded battle.
- `GET /leaderboard/series`: Player leaderboard sorted by series wins.
- `GET /players/{tag}/elo-history`: Elo rating history for a specific player.
-
- `GET /stats/elixir`: Average elixir leak per player.
- `GET /stats/cards`: Overall card usage and win rates.
- `GET /stats/cards/head-to-head`: Head-to-head statistics between two cards.
- `GET /players/{tag}/summary`: A summary for a player including top cards and teammates.

</details>
