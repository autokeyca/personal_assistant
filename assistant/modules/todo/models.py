"""Database models for Todo module."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Enum, DateTime, BigInteger, ForeignKey
from assistant.db.models import Base
import enum


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

    # Multi-user support
    user_id = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=True)
    created_by = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=True)

    # Follow-up system
    follow_up_intensity = Column(String(20), default='medium')
    last_followup_at = Column(DateTime, nullable=True)
    next_followup_at = Column(DateTime, nullable=True)

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
            "user_id": self.user_id,
            "created_by": self.created_by,
            "follow_up_intensity": self.follow_up_intensity,
            "last_followup_at": self.last_followup_at.isoformat() if self.last_followup_at else None,
            "next_followup_at": self.next_followup_at.isoformat() if self.next_followup_at else None,
        }
