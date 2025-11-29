#!/usr/bin/env python3
"""Check todos in database."""

from assistant.db import init_db, get_session, Todo

# Initialize database
init_db()

with get_session() as session:
    todos = session.query(Todo).all()
    print(f"\n=== Current Todos ({len(todos)} total) ===\n")
    for t in todos:
        print(f"ID: {t.id}")
        print(f"Title: {t.title}")
        print(f"Status: {t.status.value}")
        print(f"Priority: {t.priority.value}")
        print(f"---")
