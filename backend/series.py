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
    """
    Scan a contiguous time 'session' of games between the same two duos.
    Create a Series every time one side reaches 4 wins (Bo7), then reset
    counters and keep scanning in case there is another back-to-back Bo7.
    Returns the number of Series rows created.
    """
    wins = {'A': 0, 'B': 0}
    used: list[Game] = []          # games in the current Bo7-in-progress
    current_start = None           # started_at for the current Bo7
    created = 0

    for g in session_games:
        # If we are starting a fresh Bo7 chunk, mark its start time
        if not used:
            current_start = g.battle_time
        used.append(g)

        # Count only decisive games
        if g.winner_team in ('A', 'B'):
            wins[g.winner_team] += 1

        # Check for Bo7 completion
        if wins['A'] == 4 or wins['B'] == 4:
            winner = 'A' if wins['A'] == 4 else 'B'
            # First game of this Bo7 chunk determines tags/mode
            first_game = used[0]
            sid = series_id(pk, current_start)

            if not db.get(Series, sid):
                db.add(Series(
                    id=sid,
                    started_at=current_start,
                    ended_at=g.battle_time,                # clincher time
                    mode_id=first_game.mode_id,
                    teamA_tag1=first_game.teamA_tag1,
                    teamA_tag2=first_game.teamA_tag2,
                    teamB_tag1=first_game.teamB_tag1,
                    teamB_tag2=first_game.teamB_tag2,
                    winner_team=winner,
                    game_ids=json.dumps([x.id for x in used]),
                    season_id=None,
                ))
                created += 1

            # Reset to look for another Bo7 immediately after
            wins = {'A': 0, 'B': 0}
            used = []
            current_start = None

    return created
