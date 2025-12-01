"""Main FastAPI application for Jarvis inter-agent communication API."""

import logging
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from typing import List, Optional

from assistant.config import get
from assistant.db import get_session, Todo, Reminder, APIKey as APIKeyModel
from assistant.services import TodoService, UserService, FrequencyParser
from .auth import verify_api_key, check_permission
from .schemas import (
    MessageRequest, MessageResponse,
    TaskCreateRequest, TaskResponse,
    ReminderCreateRequest, ReminderResponse,
    TaskReminderRequest,
    StatusResponse,
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Jarvis Agent API",
    description="REST API for inter-agent communication with Jarvis personal assistant",
    version="1.0.0",
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc",  # ReDoc
)


# Bot instance for sending messages (will be set by run_api.py)
_bot_instance = None


def set_bot_instance(bot):
    """Set the bot instance for sending messages."""
    global _bot_instance
    _bot_instance = bot


def get_bot():
    """Get the bot instance."""
    if _bot_instance is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Bot is not connected. Please ensure Jarvis is running."
        )
    return _bot_instance


@app.get("/", tags=["general"])
async def root():
    """Root endpoint - API information."""
    return {
        "name": "Jarvis Agent API",
        "version": "1.0.0",
        "status": "online",
        "docs": "/docs",
        "endpoints": {
            "message": "POST /message - Send message to user",
            "task": "POST /task - Create new task",
            "tasks": "GET /tasks - List tasks",
            "reminder": "POST /reminder - Create reminder",
            "task_reminder": "POST /task-reminder - Set custom task reminder",
            "status": "GET /status - Get Jarvis status",
        }
    }


@app.get("/health", tags=["general"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/message", response_model=MessageResponse, tags=["communication"])
async def send_message(
    request: MessageRequest,
    api_key: APIKeyModel = Depends(verify_api_key)
):
    """
    Send a message to a user via Telegram.

    Requires permission: `message:send`
    """
    # Check permission
    if not check_permission(api_key, "message:send"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key does not have permission to send messages"
        )

    try:
        bot = get_bot()

        # Get target user ID (default to owner)
        user_id = request.user_id or get("telegram.authorized_user_id")

        # Send message
        message = await bot.send_message(
            chat_id=user_id,
            text=request.message,
            parse_mode=request.parse_mode
        )

        logger.info(f"Agent '{api_key.name}' sent message to user {user_id}")

        return MessageResponse(
            success=True,
            message_id=message.message_id
        )

    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return MessageResponse(
            success=False,
            error=str(e)
        )


@app.post("/task", response_model=TaskResponse, tags=["tasks"])
async def create_task(
    request: TaskCreateRequest,
    api_key: APIKeyModel = Depends(verify_api_key)
):
    """
    Create a new task for a user.

    Requires permission: `task:create`
    """
    # Check permission
    if not check_permission(api_key, "task:create"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key does not have permission to create tasks"
        )

    try:
        todo_service = TodoService()
        user_service = UserService()

        # Determine target user
        target_user_id = None
        if request.user_id:
            target_user_id = request.user_id
        elif request.user_name:
            user = user_service.get_user_by_name(request.user_name)
            if user:
                target_user_id = user.telegram_id
        else:
            # Default to owner
            target_user_id = get("telegram.authorized_user_id")

        # Parse due date if provided
        due_date = None
        if request.due_date:
            from dateutil import parser
            due_date = parser.parse(request.due_date)

        # Create task
        todo = todo_service.add(
            title=request.title,
            description=request.description,
            priority=request.priority,
            due_date=due_date,
            user_id=target_user_id,
            follow_up_intensity=request.follow_up_intensity
        )

        logger.info(f"Agent '{api_key.name}' created task #{todo['id']} for user {target_user_id}")

        return TaskResponse(**todo)

    except Exception as e:
        logger.error(f"Error creating task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create task: {str(e)}"
        )


@app.get("/tasks", response_model=List[TaskResponse], tags=["tasks"])
async def list_tasks(
    user_id: Optional[int] = None,
    user_name: Optional[str] = None,
    include_completed: bool = False,
    limit: int = 10,
    api_key: APIKeyModel = Depends(verify_api_key)
):
    """
    List tasks for a user.

    Requires permission: `task:read`
    """
    # Check permission
    if not check_permission(api_key, "task:read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key does not have permission to read tasks"
        )

    try:
        todo_service = TodoService()
        user_service = UserService()

        # Determine target user
        target_user_id = None
        if user_id:
            target_user_id = user_id
        elif user_name:
            user = user_service.get_user_by_name(user_name)
            if user:
                target_user_id = user.telegram_id

        # Get tasks
        tasks = todo_service.list(
            user_id=target_user_id,
            include_completed=include_completed,
            limit=limit
        )

        return [TaskResponse(**task) for task in tasks]

    except Exception as e:
        logger.error(f"Error listing tasks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list tasks: {str(e)}"
        )


@app.post("/reminder", response_model=ReminderResponse, tags=["reminders"])
async def create_reminder(
    request: ReminderCreateRequest,
    api_key: APIKeyModel = Depends(verify_api_key)
):
    """
    Create a one-time reminder.

    Requires permission: `reminder:create`
    """
    # Check permission
    if not check_permission(api_key, "reminder:create"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key does not have permission to create reminders"
        )

    try:
        from dateutil import parser

        # Parse reminder time
        remind_at = parser.parse(request.remind_at)

        # Create reminder in database
        with get_session() as session:
            reminder = Reminder(
                message=request.message,
                remind_at=remind_at,
                is_sent=False
            )
            session.add(reminder)
            session.commit()
            session.refresh(reminder)

            logger.info(f"Agent '{api_key.name}' created reminder #{reminder.id}")

            return ReminderResponse(
                id=reminder.id,
                message=reminder.message,
                remind_at=reminder.remind_at.isoformat(),
                is_sent=reminder.is_sent
            )

    except Exception as e:
        logger.error(f"Error creating reminder: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create reminder: {str(e)}"
        )


@app.post("/task-reminder", response_model=dict, tags=["reminders"])
async def set_task_reminder(
    request: TaskReminderRequest,
    api_key: APIKeyModel = Depends(verify_api_key)
):
    """
    Set a custom reminder frequency for a task.

    Requires permission: `reminder:create`
    """
    # Check permission
    if not check_permission(api_key, "reminder:create"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key does not have permission to create reminders"
        )

    try:
        import json
        frequency_parser = FrequencyParser()

        # Parse frequency
        frequency_config = frequency_parser.parse(request.frequency)
        if not frequency_config:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not parse frequency: {request.frequency}"
            )

        # Update task with reminder config
        with get_session() as session:
            todo = session.query(Todo).filter_by(id=request.task_id).first()
            if not todo:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Task #{request.task_id} not found"
                )

            todo.reminder_config = json.dumps(frequency_config)
            session.commit()

            logger.info(f"Agent '{api_key.name}' set reminder for task #{request.task_id}")

            return {
                "success": True,
                "task_id": request.task_id,
                "frequency": frequency_parser.describe(frequency_config)
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting task reminder: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set task reminder: {str(e)}"
        )


@app.get("/status", response_model=StatusResponse, tags=["general"])
async def get_status(
    api_key: APIKeyModel = Depends(verify_api_key)
):
    """
    Get Jarvis status.

    Requires permission: `status:read`
    """
    # Check permission
    if not check_permission(api_key, "status:read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key does not have permission to read status"
        )

    try:
        todo_service = TodoService()

        # Get task counts
        todos = todo_service.list(limit=100)
        pending = len([t for t in todos if t["status"] == "pending"])
        in_progress = len([t for t in todos if t["status"] == "in_progress"])

        # Get active task
        active_task = todo_service.get_active_task()
        active_task_response = TaskResponse(**active_task) if active_task else None

        return StatusResponse(
            status="running",
            uptime=None,  # TODO: track uptime
            active_task=active_task_response,
            pending_tasks=pending,
            in_progress_tasks=in_progress
        )

    except Exception as e:
        logger.error(f"Error getting status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get status: {str(e)}"
        )


# Error handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )
