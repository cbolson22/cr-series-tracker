# CR Series Tracker

Best-of-7 Clash Royale tracker for 2v2 Touchdown Draft (in-clan).  
Backend: FastAPI + SQLAlchemy (SQLite).  
Scheduler: APScheduler.  
Scripts: one-shot fetch & full recompute.

---

## Quickstart

### 0) Setup

python3 -m venv .venv

source .venv/bin/activate # Windows: .venv\Scripts\Activate.ps1

pip install -r requirements.txt

fill in your values in a .env file # fill in CR_TOKEN, PLAYER_TAGS, etc.

### 1) Init DB + seed players

python3 -c "from backend.db import engine, Base; from backend import models; Base.metadata.create_all(bind=engine)"

python3 -m backend.seed_players # optional now, recommended before ingest

### 2) Fetch once (ingest) & detect series

python3 -m backend.scripts.fetch_once

### 3) Run API

uvicorn backend.api:app --reload --port 8000

# Open http://127.0.0.1:8000/docs

### 4) (Optional) Scheduler every 20 min

python3 -m backend.scheduler

### 5) Inspect DB

Open `cr_series.db` with the VS Code “SQLite” extension
or in terminal: sqlite3 cr_series.db

---

## Endpoints

GET /health  
GET /last-update  
GET /leaderboard/series  
GET /stats/elixir  
GET /stats/cards

---

## Notes

• Ingest accepts only games where all 4 players are in PLAYER_TAGS.  
• Series are created when a Bo7 is completed in a session (gap ≤ SESSION_MAX_GAP_MINUTES).  
• If scheduler pauses for a while, you can catch up and rebuild series with:

python3 -m backend.scripts.fetch_once  
python3 -m backend.scripts.recompute
