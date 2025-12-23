from sqlalchemy.orm import Session
from datetime import datetime
from backend.db import Base, engine, SessionLocal
from backend.config import PLAYER_TAGS
from backend.cr_client import player_battlelog
from backend.elo import rebuild_elo
from backend.ingest import upsert_game
from backend.series import detect_series

Base.metadata.create_all(bind=engine)

def main():
    db: Session = SessionLocal()
    try:
        new_count = 0
        print(f"[{datetime.utcnow().isoformat()}] Fetching latest battle logs...")
        for tag in PLAYER_TAGS:
            print(f"  → Fetching {tag}...")
            log = player_battlelog(tag)
            for b in log:
                if upsert_game(db, b):
                    new_count += 1
            db.commit()
        detect_series(db, since_hours=24)
        
        # Only rebuild ELO if new games were added
        if new_count > 0:
            n = rebuild_elo(db)
            print(f"ELO rebuild done. Inserted {n} rows.")
        print(f"[{datetime.utcnow().isoformat()}] Fetched. New games: {new_count}")
    finally:
        db.close()

if __name__ == '__main__':
    main()