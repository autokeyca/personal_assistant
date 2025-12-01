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

    # Multi-user support
    user_id = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=True)
    created_by = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=True)

    # Follow-up system
    follow_up_intensity = Column(String(20), default='medium')  # none, low, medium, high, urgent
    last_followup_at = Column(DateTime, nullable=True)
    next_followup_at = Column(DateTime, nullable=True)

    # Custom reminder configuration (JSON-encoded FrequencyParser config)
    reminder_config = Column(Text, nullable=True)  # JSON: {interval_value, interval_unit, time_range, days, enabled}
    last_reminder_at = Column(DateTime, nullable=True)  # Track when last reminder was sent

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
            "reminder_config": self.reminder_config,
            "last_reminder_at": self.last_reminder_at.isoformat() if self.last_reminder_at else None,
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
    is_authorized = Column(Boolean, default=False)  # True if allowed to interact with Jarvis
    role = Column(String(20), nullable=True)  # 'owner', 'employee', 'contact'
    authorized_at = Column(DateTime, nullable=True)  # When they were authorized
    authorized_by = Column(BigInteger, nullable=True)  # Telegram ID of who authorized them
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Follow-up settings
    default_followup_intensity = Column(String(20), default='medium')  # none, low, medium, high, urgent
    followup_enabled = Column(Boolean, default=True)

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
            "role": self.role,
            "authorized_at": self.authorized_at.isoformat() if self.authorized_at else None,
            "authorized_by": self.authorized_by,
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


class BehaviorConfig(Base):
    """Runtime behavior configuration for dynamic system modification."""
    __tablename__ = "behavior_configs"

    key = Column(String(100), primary_key=True)  # Config parameter name
    value = Column(Text, nullable=False)  # Current value (stored as JSON string if complex)
    value_type = Column(String(20), default="string")  # string, int, float, bool, json
    description = Column(Text, nullable=True)  # Human-readable description
    category = Column(String(50), nullable=True)  # Category: timing, behavior, feature, etc.
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(String(200), nullable=True)  # Who/what updated it

    def __repr__(self):
        return f"<BehaviorConfig(key='{self.key}', value='{self.value}')>"

    def to_dict(self):
        return {
            "key": self.key,
            "value": self.value,
            "value_type": self.value_type,
            "description": self.description,
            "category": self.category,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "updated_by": self.updated_by,
        }


class APIKey(Base):
    """API keys for inter-agent communication."""
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True)
    key = Column(String(64), unique=True, nullable=False)  # API key (hashed)
    name = Column(String(200), nullable=False)  # Agent name/identifier
    description = Column(Text, nullable=True)  # Purpose of this agent
    permissions = Column(Text, default="*")  # Comma-separated permissions or "*" for all
    is_active = Column(Boolean, default=True)  # Can be disabled without deleting
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime, nullable=True)  # Track usage
    usage_count = Column(Integer, default=0)  # Number of API calls made

    def __repr__(self):
        return f"<APIKey(name='{self.name}', active={self.is_active})>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "permissions": self.permissions.split(",") if self.permissions != "*" else ["*"],
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "usage_count": self.usage_count,
        }
