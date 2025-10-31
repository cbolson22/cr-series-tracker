from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_, and_
from fastapi.middleware.cors import CORSMiddleware
from .db import Base, engine, get_db
from .models import Game, GamePlayer, GamePlayerCard, Series, EloHistory
from .config import PLAYER_TAGS, TOUCHDOWN_DRAFT_MODE_ID


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

# Endpoint to get ELO history for a specific player
@app.get("/players/{tag}/elo-history")
def elo_history(tag: str, db: Session = Depends(get_db)):
    safe_tag = tag.strip().upper()
    rows = db.execute(
        select(EloHistory.timestamp, EloHistory.elo)
        .where(EloHistory.player_tag == safe_tag)
        .order_by(EloHistory.timestamp.asc(), EloHistory.id.asc())
    ).all()
    history = [{"timestamp": ts.isoformat(), "elo": elo} for ts, elo in rows]
    return {"player_tag": safe_tag, "history": history}

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

# Endpoint to get head-to-head stats between two cards
@app.get("/stats/cards/head-to-head")
def card_head_to_head_games(
    card1: int = Query(..., ge=0),
    card2: int = Query(..., ge=0),
    db: Session = Depends(get_db),
):
    if card1 == card2:
        raise HTTPException(status_code=400, detail="card1 and card2 must be different")

    # Pull all relevant rows in one query:
    #   game_id, game winner, team ('A'/'B'), and the card_id (only card1 or card2)
    rows = db.execute(
        select(
            Game.id,
            Game.winner_team,
            GamePlayer.team,
            GamePlayerCard.card_id,
        )
        .join(GamePlayer, Game.id == GamePlayer.game_id)
        .join(
            GamePlayerCard,
            (GamePlayerCard.game_id == GamePlayer.game_id)
            & (GamePlayerCard.player_tag == GamePlayer.player_tag),
        )
        .where(
            Game.mode_id == TOUCHDOWN_DRAFT_MODE_ID,     # <-- remove this line if you want ALL modes
            GamePlayerCard.card_id.in_([card1, card2]),
        )
    ).all()

    # Aggregate per game → which team used which of the two cards
    # games[gid] = {"winner": 'A'|'B'|'D', "A": set(card_ids), "B": set(card_ids)}
    games = {}
    for game_id, winner_team, team, cid in rows:
        g = games.setdefault(game_id, {"winner": winner_team, "A": set(), "B": set()})
        if team in ("A", "B"):
            g[team].add(cid)

    games_played = 0
    games_won = 0  # games won by the side that used card1

    for g in games.values():
        winner = g["winner"]
        if winner not in ("A", "B"):
            continue  # skip draws

        a_has_1 = card1 in g["A"]
        a_has_2 = card2 in g["A"]
        b_has_1 = card1 in g["B"]
        b_has_2 = card2 in g["B"]

        # True H2H only if the cards are on opposite sides
        if (a_has_1 and b_has_2) or (a_has_2 and b_has_1):
            games_played += 1
            # Did the side with card1 win this game?
            if (winner == "A" and a_has_1) or (winner == "B" and b_has_1):
                games_won += 1

    return {
        "card1": card1,
        "card2": card2,
        "games_played": games_played,
        "games_won": games_won,                         # wins by the side with card1
        "win_pct": (games_won / games_played) if games_played else 0.0,
    }

# Endpoint to get a player's summary: top cards and most played-with teammate
@app.get("/players/{tag}/summary")
def player_summary(tag: str, db: Session = Depends(get_db)):
    safe = tag.strip().upper()

    # ---- Top 3 cards (unchanged) ----
    rows = db.execute(
        select(GamePlayerCard.card_id, func.count())
        .join(
            GamePlayer,
            (GamePlayerCard.game_id == GamePlayer.game_id) &
            (GamePlayerCard.player_tag == GamePlayer.player_tag)
        )
        .where(GamePlayer.player_tag == safe)
        .group_by(GamePlayerCard.card_id)
        .order_by(func.count().desc())
        .limit(3)
    ).all()
    top_cards = [{"card_id": int(cid), "uses": int(cnt)} for cid, cnt in rows]

    # ---- Series played / won ----
    series_played = db.scalar(
        select(func.count())
        .select_from(Series)
        .where(
            or_(
                Series.teamA_tag1 == safe,
                Series.teamA_tag2 == safe,
                Series.teamB_tag1 == safe,
                Series.teamB_tag2 == safe,
            )
        )
    ) or 0

    series_won = (
        (db.scalar(
            select(func.count())
            .select_from(Series)
            .where(
                and_(
                    Series.winner_team == 'A',
                    or_(Series.teamA_tag1 == safe, Series.teamA_tag2 == safe)
                )
            )
        ) or 0)
        +
        (db.scalar(
            select(func.count())
            .select_from(Series)
            .where(
                and_(
                    Series.winner_team == 'B',
                    or_(Series.teamB_tag1 == safe, Series.teamB_tag2 == safe)
                )
            )
        ) or 0)
    )

    # ---- Top teammates (2) with series + games together (as before but returns a list) ----
    gt = db.execute(
        select(GamePlayer.game_id, GamePlayer.team)
        .where(GamePlayer.player_tag == safe)
    ).all()
    game_team = {gid: team for gid, team in gt}
    games_with: dict[str, int] = {}
    if game_team:
        co_rows = db.execute(
            select(GamePlayer.game_id, GamePlayer.player_tag, GamePlayer.team)
            .where(GamePlayer.game_id.in_(list(game_team.keys())))
        ).all()
        for gid, ptag, pteam in co_rows:
            if ptag == safe:
                continue
            if pteam == game_team.get(gid):
                games_with[ptag] = games_with.get(ptag, 0) + 1

    series_with: dict[str, int] = {}
    for s in db.scalars(select(Series)).all():
        sideA = {s.teamA_tag1, s.teamA_tag2}
        sideB = {s.teamB_tag1, s.teamB_tag2}
        if safe in sideA:
            mate = (sideA - {safe}).pop()
            series_with[mate] = series_with.get(mate, 0) + 1
        elif safe in sideB:
            mate = (sideB - {safe}).pop()
            series_with[mate] = series_with.get(mate, 0) + 1

    merged = []
    for mate in set(games_with) | set(series_with):
        merged.append({
            "player_tag": mate,
            "series_together": int(series_with.get(mate, 0)),
            "games_together": int(games_with.get(mate, 0)),
        })
    merged.sort(key=lambda x: (x["series_together"], x["games_together"]), reverse=True)
    top_teammates = merged[:2]

    return {
        "player_tag": safe,
        "series_played": int(series_played),
        "series_won": int(series_won),
        "top_cards": top_cards,
        "top_teammates": top_teammates,
    }