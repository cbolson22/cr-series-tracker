from datetime import timedelta
import json, hashlib
from sqlalchemy.orm import Session
from sqlalchemy import select
from .models import Game, Series
from .config import SESSION_MAX_GAP_MINUTES, TOUCHDOWN_DRAFT_MODE_ID

MAX_GAP = timedelta(minutes=SESSION_MAX_GAP_MINUTES)

# Return a canonical key for a pair of teams
def pair_key(g: Game):
    teamA = tuple(sorted([g.teamA_tag1, g.teamA_tag2]))
    teamB = tuple(sorted([g.teamB_tag1, g.teamB_tag2]))
    return tuple(sorted([teamA, teamB]))

# Create a unique ID for a series based on teams and start time
def series_id(teams, start_dt) -> str:
    # teams is ((a1,a2),(b1,b2))
    raw = json.dumps({"teams": teams, "start": start_dt.isoformat()}, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()

# Detect and create Series from Games in the database
def detect_series(db: Session, since_hours: int | None = 6):
    from datetime import datetime
    q = select(Game).where(Game.mode_id == TOUCHDOWN_DRAFT_MODE_ID).order_by(Game.battle_time.asc())
    if since_hours is not None:
        cutoff = datetime.utcnow() - timedelta(hours=since_hours)
        q = q.where(Game.battle_time >= cutoff)
    
    games = list(db.scalars(q))
    grouped = {}
    for g in games:
        grouped.setdefault(pair_key(g), []).append(g)

    for pk, glist in grouped.items():
        glist.sort(key=lambda x: x.battle_time)
        session = []
        last_t = None
        for g in glist:
            if not session:
                session = [g]
                last_t = g.battle_time
                continue
            if (g.battle_time - last_t) > MAX_GAP:
                _finish_session(db, pk, session)
                session = [g]
            else:
                session.append(g)
            last_t = g.battle_time
        if session:
            _finish_session(db, pk, session)
    db.commit()

# Finalize a session of games, creating a Series if applicable
def _finish_session(db: Session, pk, session_games: list[Game]):
    wins = {'A': 0, 'B': 0}
    used = []
    for g in session_games:
        used.append(g)
        if g.winner_team in ('A', 'B'):
            wins[g.winner_team] += 1
        if wins['A'] == 4 or wins['B'] == 4:
            winner = 'A' if wins['A'] == 4 else 'B'
            sid = series_id(pk, session_games[0].battle_time)
            if not db.get(Series, sid):
                db.add(Series(
                    id=sid,
                    started_at=session_games[0].battle_time,
                    ended_at=g.battle_time,
                    mode_id=session_games[0].mode_id,
                    teamA_tag1=session_games[0].teamA_tag1,
                    teamA_tag2=session_games[0].teamA_tag2,
                    teamB_tag1=session_games[0].teamB_tag1,
                    teamB_tag2=session_games[0].teamB_tag2,
                    winner_team=winner,
                    game_ids=json.dumps([x.id for x in used]),
                    season_id=None,
                ))
            break
