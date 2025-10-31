from sqlalchemy.orm import Session
from backend.db import SessionLocal, Base, engine
from backend.elo import rebuild_elo

def main():
    Base.metadata.create_all(bind=engine)  # ensure table exists
    db: Session = SessionLocal()
    try:
        n = rebuild_elo(db)
        print(f"ELO rebuild done. Inserted {n} rows.")
    finally:
        db.close()

if __name__ == "__main__":
    main()