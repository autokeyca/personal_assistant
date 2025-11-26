"""SQLAlchemy database models."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Enum, BigInteger, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
import enum

Base = declarative_base()


class Priority(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TodoStatus(enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Todo(Base):
    """Todo items."""
    __tablename__ = "todos"

    id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(Enum(Priority), default=Priority.MEDIUM)
    status = Column(Enum(TodoStatus), default=TodoStatus.PENDING)
    due_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    tags = Column(String(500), nullable=True)  # Comma-separated tags

    def __repr__(self):
        return f"<Todo(id={self.id}, title='{self.title[:30]}...', status={self.status.value})>"

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority.value,
            "status": self.status.value,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "created_at": self.created_at.isoformat(),
            "tags": self.tags.split(",") if self.tags else [],
        }


class Reminder(Base):
    """Scheduled reminders."""
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True)
    message = Column(Text, nullable=False)
    remind_at = Column(DateTime, nullable=False)
    repeat = Column(String(50), nullable=True)  # daily, weekly, monthly, or cron expression
    is_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    todo_id = Column(Integer, nullable=True)  # Optional link to a todo

    def __repr__(self):
        return f"<Reminder(id={self.id}, remind_at={self.remind_at}, sent={self.is_sent})>"


class Setting(Base):
    """Key-value settings storage."""
    __tablename__ = "settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Setting(key='{self.key}')>"


class EmailCache(Base):
    """Cache for processed emails to avoid duplicate notifications."""
    __tablename__ = "email_cache"

    id = Column(String(100), primary_key=True)  # Gmail message ID
    subject = Column(String(500))
    sender = Column(String(200))
    received_at = Column(DateTime)
    notified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<EmailCache(id='{self.id}', subject='{self.subject[:30]}...')>"


class User(Base):
    """Users who have interacted with Jarvis."""
    __tablename__ = "users"

    telegram_id = Column(BigInteger, primary_key=True)  # Telegram user ID
    first_name = Column(String(200), nullable=True)
    last_name = Column(String(200), nullable=True)
    username = Column(String(200), nullable=True)  # @username
    is_owner = Column(Boolean, default=False)  # True for the authorized owner
    is_authorized = Column(Boolean, default=False)  # True if allowed to send tasks
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to conversation history
    conversations = relationship("ConversationHistory", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(telegram_id={self.telegram_id}, name='{self.first_name}', owner={self.is_owner})>"

    def to_dict(self):
        return {
            "telegram_id": self.telegram_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "username": self.username,
            "is_owner": self.is_owner,
            "is_authorized": self.is_authorized,
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
        }

    @property
    def full_name(self):
        """Get user's full name."""
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.username or f"User {self.telegram_id}"


class ConversationHistory(Base):
    """Conversation history for context retention."""
    __tablename__ = "conversation_history"

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    message = Column(Text, nullable=False)
    channel = Column(String(20), nullable=True)  # 'telegram', 'email', or None
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationship to user
    user = relationship("User", back_populates="conversations")

    def __repr__(self):
        return f"<ConversationHistory(id={self.id}, user_id={self.user_id}, role='{self.role}')>"

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "role": self.role,
            "message": self.message,
            "channel": self.channel,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


class PendingApproval(Base):
    """Pending task approvals from non-owner users."""
    __tablename__ = "pending_approvals"

    id = Column(Integer, primary_key=True)
    requester_id = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    request_message = Column(Text, nullable=False)  # What the user asked for
    intent = Column(String(50), nullable=True)  # Parsed intent from LLM
    entities = Column(Text, nullable=True)  # JSON-encoded entities
    status = Column(String(20), default="pending")  # pending, approved, rejected
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<PendingApproval(id={self.id}, requester_id={self.requester_id}, status='{self.status}')>"
