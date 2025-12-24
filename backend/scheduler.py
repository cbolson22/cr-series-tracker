from apscheduler.schedulers.blocking import BlockingScheduler
from sqlalchemy.orm import Session
from .db import Base, engine, SessionLocal
from .config import PLAYER_TAGS
from .cr_client import player_battlelog
from .ingest import upsert_game
from .series import detect_series
from .elo import rebuild_elo

Base.metadata.create_all(bind=engine)

sched = BlockingScheduler()

@sched.scheduled_job('interval', minutes=20)
def timed_sync():
    db: Session = SessionLocal()
    try:
        new_count = 0
        for tag in PLAYER_TAGS:
            try:
                log = player_battlelog(tag)
            except Exception as e:
                print(f"fetch error {tag}: {e}")
                continue
            for b in log:
                try:
                    if upsert_game(db, b):
                        new_count += 1
                except Exception as e:
                    print('ingest error:', e)
            db.commit()
        detect_series(db, since_hours=6)
        if new_count > 0: # Added conditional Elo rebuild
            n = rebuild_elo(db)
            print(f"ELO rebuild done. Inserted {n} rows.")
        print(f"sync done, new games: {new_count}")
    finally:
        db.close()

if __name__ == '__main__':
    print('Running initial sync...')
    timed_sync()              # run once immediately
    print('Starting 20-minute scheduler...')
    try:
        sched.start()
    except (KeyboardInterrupt, SystemExit):
        print('Scheduler stopped.')