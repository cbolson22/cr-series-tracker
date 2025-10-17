from datetime import datetime
from sqlalchemy import ForeignKey, String, Integer, Float, DateTime, Text, CHAR, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base


class Player(Base):
    __tablename__ = "players"
    tag: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str | None] = mapped_column(String, nullable=True)

class Game(Base):
    __tablename__ = "games"
    id: Mapped[str] = mapped_column(String, primary_key=True) # hash id
    battle_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    type: Mapped[str] = mapped_column(String)
    mode_id: Mapped[int] = mapped_column(Integer)
    event_tag: Mapped[str | None] = mapped_column(String, nullable=True)
    teamA_tag1: Mapped[str] = mapped_column(String)
    teamA_tag2: Mapped[str] = mapped_column(String)
    teamB_tag1: Mapped[str] = mapped_column(String)
    teamB_tag2: Mapped[str] = mapped_column(String)
    teamA_crowns: Mapped[int] = mapped_column(Integer)
    teamB_crowns: Mapped[int] = mapped_column(Integer)
    winner_team: Mapped[str] = mapped_column(CHAR(1)) # 'A'|'B'|'D'
    season_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    players: Mapped[list["GamePlayer"]] = relationship(back_populates="game", cascade="all, delete-orphan")

class GamePlayer(Base):
    __tablename__ = "game_players"
    game_id: Mapped[str] = mapped_column(String, ForeignKey("games.id", ondelete="CASCADE"), primary_key=True)
    player_tag: Mapped[str] = mapped_column(String, ForeignKey("players.tag", ondelete="RESTRICT"), primary_key=True)
    team: Mapped[str] = mapped_column(CHAR(1)) # 'A'|'B'
    crowns: Mapped[int] = mapped_column(Integer)
    elixir_leaked: Mapped[float] = mapped_column(Float)
    game: Mapped[Game] = relationship(back_populates="players")

class GamePlayerCard(Base):
    __tablename__ = "game_player_cards"
    game_id: Mapped[str] = mapped_column(String, ForeignKey("games.id", ondelete="CASCADE"), primary_key=True)
    player_tag: Mapped[str] = mapped_column(String, ForeignKey("players.tag", ondelete="CASCADE"), primary_key=True)
    card_id: Mapped[int] = mapped_column(Integer, primary_key=True)

class Series(Base):
    __tablename__ = "series"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime)
    ended_at: Mapped[datetime] = mapped_column(DateTime)
    mode_id: Mapped[int] = mapped_column(Integer)
    teamA_tag1: Mapped[str] = mapped_column(String)
    teamA_tag2: Mapped[str] = mapped_column(String)
    teamB_tag1: Mapped[str] = mapped_column(String)
    teamB_tag2: Mapped[str] = mapped_column(String)
    winner_team: Mapped[str] = mapped_column(CHAR(1))
    game_ids: Mapped[str] = mapped_column(Text) # JSON array string
    season_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "teamA_tag1", "teamA_tag2", "teamB_tag1", "teamB_tag2", "started_at",
            name="uq_series_pair_time",
        ),
    )
