from __future__ import annotations
from typing import Dict
from math import pow
from sqlalchemy import select, delete
from sqlalchemy.orm import Session
from .models import Series, EloHistory

START_ELO = 400.0  # keep float in memory for accuracy

def _k_for(series_played: int) -> float:
    # K = 50 / (1 + (series_played / 60))
    return 50.0 / (1.0 + (series_played / 60.0))

def _exp_vs_two(ep: float, eo1: float, eo2: float) -> float:
    # Expected score vs each opponent (base-10 logistic with denominator 500), then average
    e1 = 1.0 / (1.0 + pow(10.0, (eo1 - ep) / 500.0))
    e2 = 1.0 / (1.0 + pow(10.0, (eo2 - ep) / 500.0))
    return (e1 + e2) / 2.0

def rebuild_elo(db: Session) -> int:
    """
    Recompute ELO history from scratch from all Series in chronological order.

    - Everyone starts at 400
    - K = 50 / (1 + (series_played/60)) per player (uses count BEFORE this series)
    - score = 1 for winners else 0
    - Team expected scores:
        E_A = ( E(p1 vs {p3,p4}) + E(p2 vs {p3,p4}) ) / 2
        E_B = ( E(p3 vs {p1,p2}) + E(p4 vs {p1,p2}) ) / 2
    - Update each player: elo' = elo + K*(score - E_team)
    - Store a snapshot for all 4 players at Series.ended_at (rounded for storage)
    """
    # wipe previous history
    db.execute(delete(EloHistory))

    # chronological series
    series_list = list(
        db.scalars(select(Series).order_by(Series.ended_at.asc(),
                                           Series.started_at.asc(),
                                           Series.id.asc()))
    )

    elo: Dict[str, float] = {}
    played: Dict[str, int] = {}

    inserted = 0
    for s in series_list:
        if s.winner_team not in ("A", "B"):
            continue

        A = [s.teamA_tag1, s.teamA_tag2]
        B = [s.teamB_tag1, s.teamB_tag2]

        for p in A + B:
            if p not in elo:
                elo[p] = START_ELO
                played[p] = 0

        p1, p2 = A
        p3, p4 = B
        e1, e2, e3, e4 = elo[p1], elo[p2], elo[p3], elo[p4]

        # Expected team scores (your definition)
        E_p1 = _exp_vs_two(e1, e3, e4)
        E_p2 = _exp_vs_two(e2, e3, e4)
        expected_A = (E_p1 + E_p2) / 2.0

        E_p3 = _exp_vs_two(e3, e1, e2)
        E_p4 = _exp_vs_two(e4, e1, e2)
        expected_B = (E_p3 + E_p4) / 2.0   # <-- not (1 - expected_A)

        score_A = 1.0 if s.winner_team == "A" else 0.0
        score_B = 1.0 - score_A

        K1 = _k_for(played[p1]); K2 = _k_for(played[p2])
        K3 = _k_for(played[p3]); K4 = _k_for(played[p4])

        elo[p1] = e1 + K1 * (score_A - expected_A)
        elo[p2] = e2 + K2 * (score_A - expected_A)
        elo[p3] = e3 + K3 * (score_B - expected_B)
        elo[p4] = e4 + K4 * (score_B - expected_B)

        played[p1] += 1; played[p2] += 1; played[p3] += 1; played[p4] += 1

        ts = s.ended_at  # naive UTC
        for p in (p1, p2, p3, p4):
            db.add(EloHistory(player_tag=p, timestamp=ts, elo=int(round(elo[p]))))
            inserted += 1

    db.commit()
    return inserted