#!/usr/bin/env python3
"""Delete the problematic reminder."""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from assistant.db import init_db, get_session, Reminder

# Initialize database
db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'assistant.db')
init_db(db_path)

with get_session() as session:
    reminder = session.query(Reminder).filter_by(id=3).first()
    if reminder:
        print(f"Found reminder: ID={reminder.id}, Message='{reminder.message}', Remind at={reminder.remind_at}")
        session.delete(reminder)
        session.commit()
        print('✅ Deleted problematic reminder ID 3')
    else:
        print('ℹ️  Reminder ID 3 not found (already deleted)')
