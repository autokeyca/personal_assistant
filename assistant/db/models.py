"""SQLAlchemy database models."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Enum
from sqlalchemy.orm import declarative_base
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
