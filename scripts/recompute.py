# MAYBE FOR LATER USE - recompute series for all games
# IF RULES CHANGE

# from sqlalchemy.orm import Session
# from backend.db import SessionLocal
# from backend.series import detect_series

# def main():
#     db: Session = SessionLocal()
#     try:
#         detect_series(db, since_hours=None)
#         print('Recomputed series across all games.')
#     finally:
#         db.close()

# if __name__ == '__main__':
#     main()