"""Pydantic models for API requests and responses."""

from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


# Request models
class MessageRequest(BaseModel):
    """Request to send a message to user."""
    user_id: Optional[int] = Field(None, description="Telegram user ID (optional, defaults to owner)")
    message: str = Field(..., description="Message text to send")
    parse_mode: Optional[str] = Field("Markdown", description="Parse mode: Markdown or HTML")


class TaskCreateRequest(BaseModel):
    """Request to create a new task."""
    title: str = Field(..., description="Task title")
    description: Optional[str] = Field(None, description="Task description")
    priority: Optional[str] = Field("medium", description="Priority: low, medium, high, urgent")
    due_date: Optional[str] = Field(None, description="Due date in ISO format")
    user_name: Optional[str] = Field(None, description="User to assign task to (by first name)")
    user_id: Optional[int] = Field(None, description="User to assign task to (by telegram ID)")
    follow_up_intensity: Optional[str] = Field("medium", description="Follow-up intensity: none, low, medium, high, urgent")


class ReminderCreateRequest(BaseModel):
    """Request to create a reminder."""
    message: str = Field(..., description="Reminder message")
    remind_at: str = Field(..., description="When to remind (ISO datetime)")
    user_id: Optional[int] = Field(None, description="User to remind (defaults to owner)")


class TaskReminderRequest(BaseModel):
    """Request to set a custom reminder frequency for a task."""
    task_id: int = Field(..., description="Task ID")
    frequency: str = Field(..., description="Natural language frequency (e.g., 'every 2 hours during business hours')")


# Response models
class MessageResponse(BaseModel):
    """Response after sending a message."""
    success: bool
    message_id: Optional[int] = None
    error: Optional[str] = None


class TaskResponse(BaseModel):
    """Task information."""
    id: int
    title: str
    description: Optional[str]
    priority: str
    status: str
    due_date: Optional[str]
    user_id: Optional[int]
    created_at: str
    reminder_config: Optional[str] = None


class ReminderResponse(BaseModel):
    """Reminder information."""
    id: int
    message: str
    remind_at: str
    is_sent: bool


class StatusResponse(BaseModel):
    """Jarvis status information."""
    status: str
    uptime: Optional[str]
    active_task: Optional[TaskResponse]
    pending_tasks: int
    in_progress_tasks: int


class APIKeyResponse(BaseModel):
    """API key information (without the actual key)."""
    id: int
    name: str
    description: Optional[str]
    permissions: List[str]
    is_active: bool
    created_at: str
    last_used: Optional[str]
    usage_count: int


class APIKeyCreateResponse(BaseModel):
    """Response when creating a new API key."""
    api_key: str = Field(..., description="The actual API key (only shown once!)")
    key_info: APIKeyResponse
