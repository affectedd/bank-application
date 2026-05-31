from sqlalchemy import Column, Integer, Float, String, ForeignKey, DateTime, Boolean
from datetime import datetime, timezone
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    balance = Column(Float, default=0.00)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    notifications = relationship("Notification", back_populates="user")

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key = True, index = True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable = False)
    recipient_id = Column(Integer, ForeignKey("users.id"), nullable  = False)
    amount = Column(Float, nullable = False)
    description = Column(String, nullable = True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    sender = relationship("User", foreign_keys=[sender_id])
    recipient = relationship("User", foreign_keys=[recipient_id])

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key = True, index = True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable = False)
    message = Column(String, nullable = False)
    is_read = Column(Boolean, default = False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="notifications")
