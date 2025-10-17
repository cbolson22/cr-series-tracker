from dotenv import load_dotenv
import os

# Load environment variables from a .env file if present
load_dotenv()

CR_TOKEN = os.getenv("CR_TOKEN", "")
PLAYER_TAGS = [t.strip() for t in os.getenv("PLAYER_TAGS", "").split(",") if t.strip()]
CLAN_TAG = os.getenv("CLAN_TAG","").strip() or None

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./cr_series.db")

SESSION_MAX_GAP_MINUTES = int(os.getenv("SESSION_MAX_GAP_MINUTES", "30"))

# Constants for Clash Royale API
TOUCHDOWN_DRAFT_MODE_ID = 72000051
TWO_VS_TWO_TYPES = {"clanMate2v2", "2v2"}