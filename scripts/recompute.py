# Recompute series for all games ingested (not just recent ones in last 6 hours)

from sqlalchemy.orm import Session
from backend.db import SessionLocal
from backend.series import detect_series

def main():
    db: Session = SessionLocal()
    try:
        detect_series(db, since_hours=None)
        print('Recomputed series across all games.')
    finally:
        db.close()

if __name__ == '__main__':
    main()