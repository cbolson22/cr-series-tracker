from __future__ import annotations
from datetime import datetime
from typing import Dict

from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from .models import Series, EloHistory

START_ELO = 400
WIN_STEP = 10
LOSS_STEP = 10

def rebuild_elo(db: Session, start_elo: int = START_ELO, win_step: int = WIN_STEP, loss_step: int = LOSS_STEP) -> int:
    """
    Recompute ELO history from scratch from all Series in chronological order.
    Returns the number of EloHistory rows inserted.
    """
    # 1) wipe previous history (full recompute)
    db.execute(delete(EloHistory))

    # 2) pull all series chronologically
    series_list = list(db.scalars(
        select(Series).order_by(Series.ended_at.asc(), Series.started_at.asc(), Series.id.asc())
    ))

    # 3) keep running ELO in memory
    elo: Dict[str, int] = {}

    inserted = 0
    for s in series_list:
        # normalize team sets (canonical A/B already guaranteed in your ingest)
        teamA = [s.teamA_tag1, s.teamA_tag2]
        teamB = [s.teamB_tag1, s.teamB_tag2]

        # initialize new players lazily
        for t in teamA + teamB:
            if t not in elo:
                elo[t] = start_elo

        # skip unfinished/unknown winners
        if s.winner_team not in ("A", "B"):
            continue

        if s.winner_team == "A":
            winners, losers = teamA, teamB
        else:
            winners, losers = teamB, teamA

        # apply deltas
        for p in winners:
            elo[p] = elo[p] + win_step
        for p in losers:
            elo[p] = elo[p] - loss_step

        # record snapshot at series end time
        ts = s.ended_at  # naive UTC in your schema
        for p in teamA + teamB:
            db.add(EloHistory(player_tag=p, timestamp=ts, elo=elo[p]))
            inserted += 1

    db.commit()
    return inserted