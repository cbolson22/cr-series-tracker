from dotenv import load_dotenv
import os

# Load environment variables from a .env file if present
load_dotenv()

CR_TOKEN = os.getenv("CR_TOKEN", "")

PLAYER_TAGS = [t.strip().upper() for t in os.getenv("PLAYER_TAGS", "").split(",") if t.strip()]
PLAYER_NAMES = [n.strip() for n in os.getenv("PLAYER_NAMES", "").split(",") if n.strip()]

# Ensure tag and name lists are the same length
if len(PLAYER_TAGS) != len(PLAYER_NAMES):
    raise ValueError("PLAYER_TAGS and PLAYER_NAMES must have the same length.")

CLAN_TAG = os.getenv("CLAN_TAG","").strip() or None

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./cr_series.db")

SESSION_MAX_GAP_MINUTES = int(os.getenv("SESSION_MAX_GAP_MINUTES", "30"))

# Constants for Clash Royale API
TOUCHDOWN_DRAFT_MODE_ID = 72000051
TWO_VS_TWO_TYPES = {"clanMate2v2"}