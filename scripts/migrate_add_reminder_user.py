#!/usr/bin/env python3
"""Add user_id column to reminders table for multi-user reminder support."""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from assistant.db import get_session, init_db
from assistant.config import get as get_config
from sqlalchemy import text

# Initialize database
db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'assistant.db')
init_db(db_path)

print("Adding user_id column to reminders table...")

try:
    with get_session() as session:
        # Check if column already exists
        result = session.execute(text("PRAGMA table_info(reminders)"))
        columns = [row[1] for row in result.fetchall()]

        if 'user_id' in columns:
            print("✅ user_id column already exists")
        else:
            # Add the column
            session.execute(text("ALTER TABLE reminders ADD COLUMN user_id BIGINT"))
            session.commit()
            print("✅ Added user_id column")

            # Set existing reminders to owner (for backwards compatibility)
            owner_id = get_config("telegram.authorized_user_id")
            if owner_id:
                session.execute(
                    text("UPDATE reminders SET user_id = :owner_id WHERE user_id IS NULL"),
                    {"owner_id": owner_id}
                )
                session.commit()
                print(f"✅ Set existing reminders to owner (ID: {owner_id})")

    print("\n✅ Migration completed successfully!")

except Exception as e:
    print(f"\n❌ Migration failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
