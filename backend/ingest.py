from datetime import datetime, timezone
from typing import Tuple
import hashlib
from sqlalchemy.orm import Session
from .models import Game, GamePlayer, GamePlayerCard
from .config import TOUCHDOWN_DRAFT_MODE_ID, TWO_VS_TWO_TYPES, CLAN_TAG, PLAYER_TAGS

# Parse Clash Royale timestamp string into a timezone-aware datetime
def parse_time(ts: str) -> datetime:
    # '20251013T235247.000Z' -> aware UTC datetime
    return datetime.strptime(ts, "%Y%m%dT%H%M%S.%fZ").replace(tzinfo=timezone.utc)

# Create a unique ID for a battle based on its key attributes
def game_uid(b: dict) -> str:
    tags = sorted(p["tag"].strip().upper() for p in b.get("team", []) + b.get("opponent", []))
    raw = "|".join([
        b.get("type", ""),
        b.get("battleTime", ""),
        str((b.get("gameMode") or {}).get("id", 0)),
        *tags,
    ])
    return hashlib.sha256(raw.encode()).hexdigest()

# Check if battle is a 2v2 Touchdown match
def is_target_mode(b: dict) -> bool:
    if b.get("type") not in TWO_VS_TWO_TYPES:
        return False
    if (b.get("gameMode") or {}).get("id") != TOUCHDOWN_DRAFT_MODE_ID:
        return False
    # Ensure 2v2 and (optionally) same clan
    if len(b.get("team", [])) != 2 or len(b.get("opponent", [])) != 2:
        return False
    if CLAN_TAG:
        for p in (b.get("team", []) + b.get("opponent", [])):
            clan = p.get("clan") or {}
            if clan.get("tag") != CLAN_TAG:
                return False
    return True

# Set of player tags we care about
ALLOWED = {t.strip().upper() for t in PLAYER_TAGS}
def participants(b: dict) -> set[str]:
    return {p["tag"].strip().upper() for p in b.get("team", []) + b.get("opponent", [])}

# Return crowns for a team (key is "team" or "opponent")
def team_crowns(b: dict, key: str) -> int:
    players = b.get(key, [])
    return players[0].get("crowns", 0) if players else 0

# Return two sorted tuples of player tags for each team, and whether we swapped sides
def normalize_teams(b: dict) -> Tuple[tuple[str, ...], tuple[str, ...], bool]:
    """Return canonical (teamA, teamB) tag tuples and whether we swapped sides."""
    tA = tuple(sorted(p["tag"].strip().upper() for p in b.get("team", [])))
    tB = tuple(sorted(p["tag"].strip().upper() for p in b.get("opponent", [])))
    if tB and tA and tB < tA:
        return tB, tA, True   # swapped
    return tA, tB, False      # not swapped

# Determine winner team: 'A', 'B', or 'D' (draw)
def winner_team(b: dict) -> str:
    a = team_crowns(b, "team")
    o = team_crowns(b, "opponent")
    if a > o: return 'A'
    if o > a: return 'B'
    return 'D'

# Insert a battle into the database if it's a new, relevant game
def upsert_game(db: Session, b: dict) -> bool:
    if not is_target_mode(b):
        return False
    if not participants(b) <= ALLOWED:
        return False  # skip games with any outsider

    gid = game_uid(b)
    if db.get(Game, gid):
        return False  # already ingested

    # canonicalize team ordering
    (a1, a2), (b1, b2), swapped = normalize_teams(b)

    # crowns per side (don’t sum per-player; each has team total)
    a_c = team_crowns(b, "team")
    b_c = team_crowns(b, "opponent")

    # winner relative to original sides
    w = winner_team(b)
    if swapped:
        # flip winner if we flipped sides
        w = {'A': 'B', 'B': 'A', 'D': 'D'}[w]
        a_c, b_c = b_c, a_c  # flip crowns to match canonical sides

    bt = parse_time(b["battleTime"]).replace(tzinfo=None)  # store naive UTC
    mode_id = (b.get("gameMode") or {}).get("id")
    event_tag = b.get("eventTag")

    g = Game(
        id=gid,
        battle_time=bt,
        type=b.get("type"),
        mode_id=mode_id,
        event_tag=event_tag,
        teamA_tag1=a1, teamA_tag2=a2,
        teamB_tag1=b1, teamB_tag2=b2,
        teamA_crowns=a_c, teamB_crowns=b_c,
        winner_team=w,
        season_id=None,
    )
    db.add(g)

    # write GamePlayer rows according to canonical A/B
    # figure out which original list maps to canonical A
    orig_team_is_A = not swapped
    for p in b.get("team", []):
        tag = p["tag"].strip().upper()
        db.add(GamePlayer(
            game_id=gid,
            player_tag=tag,
            team='A' if orig_team_is_A else 'B',
            crowns=p.get("crowns", 0),
            elixir_leaked=float(p.get("elixirLeaked", 0.0) or 0.0),
        ))
        for c in p.get("cards", []) or []:
            db.add(GamePlayerCard(game_id=gid, player_tag=tag, card_id=c.get("id")))

    for p in b.get("opponent", []):
        tag = p["tag"].strip().upper()
        db.add(GamePlayer(
            game_id=gid,
            player_tag=tag,
            team='B' if orig_team_is_A else 'A',
            crowns=p.get("crowns", 0),
            elixir_leaked=float(p.get("elixirLeaked", 0.0) or 0.0),
        ))
        for c in p.get("cards", []) or []:
            db.add(GamePlayerCard(game_id=gid, player_tag=tag, card_id=c.get("id")))

    return True  # caller should commit
