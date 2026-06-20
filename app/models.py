from sqlalchemy import Column, Integer, Float, String, ForeignKey, DateTime, Boolean, Table
from datetime import datetime, timezone
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass

user_account_association = Table(
    "user_accounts",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key = True),
    Column("account_id", Integer, ForeignKey("accounts.id", ondelete="CASCADE"), primary_key = True)
        )
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    pesel = Column(String, unique  = True, index = True, nullable = False)

    accounts = relationship("Account", secondary=user_account_association, back_populates="users")
    notifications = relationship("Notification", back_populates="user", cascade = "all, delete-orphan")

class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True, index=True)
    account_number = Column(String, unique=True, index=True, nullable = False)
    balance = Column(Float, default=1000.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    users = relationship("User", secondary=user_account_association, back_populates="accounts")

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
