#!/usr/bin/env python3
"""Check Luke's task reminder configuration."""

import sys
sys.path.insert(0, '/home/ja/projects/personal_assistant')

from assistant.db import init_db, get_session, Todo
from assistant.config import get as get_config

db_path = get_config("database.path", "data/assistant.db")
init_db(db_path)

with get_session() as session:
    todo = session.query(Todo).filter_by(id=16).first()
    if todo:
        print(f'ID: {todo.id}')
        print(f'Title: {todo.title}')
        print(f'Reminder Config: {todo.reminder_config}')
        print(f'Last Reminder At: {todo.last_reminder_at}')
        print(f'Status: {todo.status}')
        print(f'User ID: {todo.user_id}')
    else:
        print('Task not found')
