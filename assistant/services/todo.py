"""Todo management service."""

from datetime import datetime
from typing import List, Optional
from sqlalchemy import or_

from assistant.db import get_session, Todo, Reminder, Setting
from assistant.db.models import Priority, TodoStatus


class TodoService:
    """Manage todo items."""

    def add(
        self,
        title: str,
        description: str = None,
        priority: str = "medium",
        due_date: datetime = None,
        tags: List[str] = None,
    ) -> Todo:
        """Add a new todo item."""
        with get_session() as session:
            todo = Todo(
                title=title,
                description=description,
                priority=Priority(priority.lower()),
                due_date=due_date,
                tags=",".join(tags) if tags else None,
            )
            session.add(todo)
            session.flush()
            return todo.to_dict()

    def list(
        self,
        status: str = None,
        priority: str = None,
        include_completed: bool = False,
        tag: str = None,
        limit: int = 50,
    ) -> List[dict]:
        """List todo items with optional filters."""
        with get_session() as session:
            query = session.query(Todo)

            if status:
                query = query.filter(Todo.status == TodoStatus(status))
            elif not include_completed:
                query = query.filter(
                    Todo.status.in_([TodoStatus.PENDING, TodoStatus.IN_PROGRESS])
                )

            if priority:
                query = query.filter(Todo.priority == Priority(priority))

            if tag:
                query = query.filter(Todo.tags.contains(tag))

            # Order by priority (urgent first) then due date
            query = query.order_by(
                Todo.priority.desc(),
                Todo.due_date.asc().nulls_last(),
                Todo.created_at.desc(),
            )

            todos = query.limit(limit).all()
            return [t.to_dict() for t in todos]

    def get(self, todo_id: int) -> Optional[dict]:
        """Get a specific todo by ID."""
        with get_session() as session:
            todo = session.query(Todo).filter(Todo.id == todo_id).first()
            return todo.to_dict() if todo else None

    def update(
        self,
        todo_id: int,
        title: str = None,
        description: str = None,
        priority: str = None,
        status: str = None,
        due_date: datetime = None,
        tags: List[str] = None,
    ) -> Optional[dict]:
        """Update a todo item."""
        with get_session() as session:
            todo = session.query(Todo).filter(Todo.id == todo_id).first()
            if not todo:
                return None

            if title:
                todo.title = title
            if description is not None:
                todo.description = description
            if priority:
                todo.priority = Priority(priority.lower())
            if status:
                new_status = TodoStatus(status)
                todo.status = new_status
                if new_status == TodoStatus.COMPLETED:
                    todo.completed_at = datetime.utcnow()
            if due_date is not None:
                todo.due_date = due_date
            if tags is not None:
                todo.tags = ",".join(tags) if tags else None

            session.flush()
            return todo.to_dict()

    def complete(self, todo_id: int) -> Optional[dict]:
        """Mark a todo as completed."""
        # Clear active task if completing it
        active = self.get_active_task()
        if active and active["id"] == todo_id:
            self.clear_active_task()
        return self.update(todo_id, status="completed")

    def set_active_task(self, todo_id: int) -> Optional[dict]:
        """Set the currently active/focused task."""
        todo = self.get(todo_id)
        if not todo:
            return None

        with get_session() as session:
            setting = session.query(Setting).filter(Setting.key == "active_task_id").first()
            if setting:
                setting.value = str(todo_id)
            else:
                setting = Setting(key="active_task_id", value=str(todo_id))
                session.add(setting)

        return todo

    def get_active_task(self) -> Optional[dict]:
        """Get the currently active/focused task."""
        with get_session() as session:
            setting = session.query(Setting).filter(Setting.key == "active_task_id").first()
            if not setting or not setting.value:
                return None

            try:
                todo_id = int(setting.value)
                todo = session.query(Todo).filter(Todo.id == todo_id).first()
                if todo and todo.status != TodoStatus.COMPLETED:
                    return todo.to_dict()
                else:
                    # Clear if task no longer exists or is completed
                    setting.value = None
                    return None
            except (ValueError, TypeError):
                return None

    def clear_active_task(self) -> bool:
        """Clear the active task."""
        with get_session() as session:
            setting = session.query(Setting).filter(Setting.key == "active_task_id").first()
            if setting:
                setting.value = None
                return True
            return False

    def delete(self, todo_id: int) -> bool:
        """Delete a todo item."""
        with get_session() as session:
            todo = session.query(Todo).filter(Todo.id == todo_id).first()
            if todo:
                session.delete(todo)
                return True
            return False

    def search(self, query: str, limit: int = 20) -> List[dict]:
        """Search todos by title or description."""
        with get_session() as session:
            todos = (
                session.query(Todo)
                .filter(
                    or_(
                        Todo.title.ilike(f"%{query}%"),
                        Todo.description.ilike(f"%{query}%"),
                    )
                )
                .limit(limit)
                .all()
            )
            return [t.to_dict() for t in todos]

    def get_due_soon(self, hours: int = 24) -> List[dict]:
        """Get todos due within the specified hours."""
        with get_session() as session:
            from datetime import timedelta

            now = datetime.utcnow()
            deadline = now + timedelta(hours=hours)

            todos = (
                session.query(Todo)
                .filter(
                    Todo.due_date.between(now, deadline),
                    Todo.status.in_([TodoStatus.PENDING, TodoStatus.IN_PROGRESS]),
                )
                .order_by(Todo.due_date.asc())
                .all()
            )
            return [t.to_dict() for t in todos]

    def add_reminder(
        self, todo_id: int, remind_at: datetime, message: str = None
    ) -> dict:
        """Add a reminder for a todo."""
        with get_session() as session:
            todo = session.query(Todo).filter(Todo.id == todo_id).first()
            if not todo:
                raise ValueError(f"Todo {todo_id} not found")

            reminder = Reminder(
                message=message or f"Reminder: {todo.title}",
                remind_at=remind_at,
                todo_id=todo_id,
            )
            session.add(reminder)
            session.flush()

            return {
                "id": reminder.id,
                "message": reminder.message,
                "remind_at": reminder.remind_at.isoformat(),
            }
