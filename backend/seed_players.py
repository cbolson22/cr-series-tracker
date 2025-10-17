from backend.db import SessionLocal
from backend.models import Player
from backend.config import PLAYER_TAGS, PLAYER_NAMES

def seed_players():
    session = SessionLocal()
    inserted = 0
    try:
        for tag, name in zip(PLAYER_TAGS, PLAYER_NAMES):
            tag = tag.strip().upper()
            if not session.get(Player, tag):
                session.add(Player(tag=tag, name=name))
                inserted += 1
        session.commit()
        print(f"Players seeded successfully. Inserted: {inserted}.")
    except Exception as e:
        session.rollback()
        print("Error seeding players:", e)
    finally:
        session.close()

if __name__ == "__main__":
    seed_players()