from datetime import datetime
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    first_name: Mapped[str] = mapped_column(String(100), default="Грибник")
    level: Mapped[int] = mapped_column(Integer, default=1)
    xp: Mapped[int] = mapped_column(Integer, default=0)
    coins: Mapped[int] = mapped_column(Integer, default=500)
    energy: Mapped[int] = mapped_column(Integer, default=20)
    max_energy: Mapped[int] = mapped_column(Integer, default=20)
    basket_capacity: Mapped[float] = mapped_column(Float, default=10.0)
    total_weight: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_energy_update: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Location(Base):
    __tablename__ = "locations"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String(500))
    required_level: Mapped[int] = mapped_column(Integer, default=1)
    unlock_price: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class Mushroom(Base):
    __tablename__ = "mushrooms"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    rarity: Mapped[str] = mapped_column(String(30))
    chance: Mapped[float] = mapped_column(Float)
    min_weight: Mapped[int] = mapped_column(Integer)
    max_weight: Mapped[int] = mapped_column(Integer)
    price_100g: Mapped[int] = mapped_column(Integer)
    xp: Mapped[int] = mapped_column(Integer)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"))
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class Catch(Base):
    __tablename__ = "catches"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    mushroom_id: Mapped[int] = mapped_column(ForeignKey("mushrooms.id"))
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"))
    weight: Mapped[float] = mapped_column(Float)
    quality: Mapped[str] = mapped_column(String(30))
    price: Mapped[int] = mapped_column(Integer)
    xp: Mapped[int] = mapped_column(Integer)
    sold: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
