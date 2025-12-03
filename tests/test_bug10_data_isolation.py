"""Test for Bug #10: Owner sees all users' todos instead of just their own."""

import pytest
from assistant.services import TodoService


class TestBug10DataIsolation:
    """Bug #10: Data isolation - owner's list shows all users' todos."""

    def test_owner_creates_own_task_shows_only_own(self, test_db, owner_user, employee_user):
        """Bug #10: When owner creates task for themselves, should only see their own todos."""
        todo_service = TodoService()

        # Owner creates task for themselves
        owner_task = todo_service.add(
            title="Owner's personal task",
            user_id=owner_user['telegram_id']
        )

        # Employee has their own task
        employee_task = todo_service.add(
            title="Employee's task",
            user_id=employee_user['telegram_id']
        )

        # When owner lists their todos, should only see their own
        owner_todos = todo_service.list(user_id=owner_user['telegram_id'])

        # Should have exactly 1 todo (owner's task)
        assert len(owner_todos) == 1, f"Expected 1 todo for owner, got {len(owner_todos)}"
        assert owner_todos[0]['id'] == owner_task['id']
        assert owner_todos[0]['user_id'] == owner_user['telegram_id']

        # Should NOT include employee's task
        employee_ids = [t['id'] for t in owner_todos if t['id'] == employee_task['id']]
        assert len(employee_ids) == 0, "Owner's list should not include employee's tasks"

    def test_list_without_user_id_returns_all(self, test_db, owner_user, employee_user):
        """Test that list() without user_id returns ALL todos (current behavior issue)."""
        todo_service = TodoService()

        # Create tasks for both users
        owner_task = todo_service.add(
            title="Owner task",
            user_id=owner_user['telegram_id']
        )

        employee_task = todo_service.add(
            title="Employee task",
            user_id=employee_user['telegram_id']
        )

        # Call list() without user_id (like in general.py line 75)
        all_todos = todo_service.list()

        # This returns ALL todos (both owner and employee)
        assert len(all_todos) == 2, "Without user_id filter, returns all todos"

        # This is the source of the bug - handlers call list() without user_id

    def test_owner_can_see_all_with_flag(self, test_db, owner_user, employee_user):
        """Test that owner can explicitly request all users' todos with all_users=True."""
        todo_service = TodoService()

        # Create tasks for both users
        todo_service.add(title="Owner task", user_id=owner_user['telegram_id'])
        todo_service.add(title="Employee task", user_id=employee_user['telegram_id'])

        # Owner explicitly requests all todos
        all_todos = todo_service.list(all_users=True)

        assert len(all_todos) == 2, "all_users=True should return all todos"

    def test_employee_only_sees_own_tasks(self, test_db, owner_user, employee_user):
        """Test that employee only sees their own tasks."""
        todo_service = TodoService()

        # Create tasks for both users
        todo_service.add(title="Owner task", user_id=owner_user['telegram_id'])
        employee_task = todo_service.add(title="Employee task", user_id=employee_user['telegram_id'])

        # Employee lists their todos
        employee_todos = todo_service.list(user_id=employee_user['telegram_id'])

        # Should only see their own task
        assert len(employee_todos) == 1
        assert employee_todos[0]['id'] == employee_task['id']
