from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from fastapi.middleware.cors import CORSMiddleware
from .db import Base, engine, get_db
from .models import Game, GamePlayer, GamePlayerCard, Series
from .config import PLAYER_TAGS


app = FastAPI(title="ClashRoyale Series Tracker API")
# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

# Basic health check endpoint
@app.get("/health")
def health():
    return {"ok": True}

# Endpoint to get the timestamp of the last recorded battle
@app.get("/last-update")
def last_update(db: Session = Depends(get_db)):
    q = select(func.max(Game.battle_time))
    return {"last_battle_time": db.scalar(q)}

# Leaderboard endpoint: returns players sorted by number of wins
@app.get("/leaderboard/series")
def series_leaderboard(db: Session = Depends(get_db)):
    wins = {}
    for s in db.scalars(select(Series)):
        winners = (s.teamA_tag1, s.teamA_tag2) if s.winner_team == 'A' else (s.teamB_tag1, s.teamB_tag2)
        for tag in winners:
            wins[tag] = wins.get(tag, 0) + 1
    return sorted([{ 'player_tag': tag, 'series_wins': wins.get(tag, 0)} for tag in PLAYER_TAGS], key=lambda r: r['series_wins'], reverse=True)

# Endpoint to get elixir leak statistics per player
@app.get("/stats/elixir")
def elixir_stats(db: Session = Depends(get_db)):
    results = []
    for tag in PLAYER_TAGS:
        q = select(func.count(), func.avg(GamePlayer.elixir_leaked)).where(GamePlayer.player_tag == tag)
        count_, avg_ = db.execute(q).one()
        results.append({'player_tag': tag, 'games': count_ or 0, 'avg_leaked': float(avg_ or 0.0)})
    return sorted(results, key=lambda r: r['avg_leaked'])

# Endpoint to get card usage and win rates
@app.get("/stats/cards")
def card_stats(db: Session = Depends(get_db)):
    from collections import defaultdict
    winners = {g.id: g.winner_team for g in db.scalars(select(Game))}
    uses, wins, losses = defaultdict(int), defaultdict(int), defaultdict(int)
    gps = {(gp.game_id, gp.player_tag): gp for gp in db.scalars(select(GamePlayer))}

    for c in db.scalars(select(GamePlayerCard)):
        gp = gps.get((c.game_id, c.player_tag))
        if not gp:
            continue
        wteam = winners.get(c.game_id)
        if wteam == 'D':
            continue
        uses[c.card_id] += 1
        if gp.team == wteam:
            wins[c.card_id] += 1
        else:
            losses[c.card_id] += 1
    
    data = []
    for cid, u in uses.items():
        w, l = wins.get(cid, 0), losses.get(cid, 0)
        win_pct = round(w / (w + l), 4) if (w + l) > 0 else 0.0
        data.append({'card_id': cid, 'uses': u, 'wins': w, 'losses': l, 'win_pct': win_pct})
    
    return sorted(data, key=lambda x: (x['win_pct'], x['uses']), reverse=True)
