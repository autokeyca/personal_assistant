#!/usr/bin/env python3
"""Migration script to add reminder_config and last_reminder_at to todos table."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from assistant.db import get_session, init_db
from assistant.config import get
from sqlalchemy import text

def migrate():
    """Add reminder_config and last_reminder_at columns to todos table."""
    print("Adding reminder_config and last_reminder_at columns to todos table...")

    # Initialize database connection
    db_path = get("database.path")
    init_db(db_path)

    with get_session() as session:
        try:
            # Check if columns already exist
            result = session.execute(text("PRAGMA table_info(todos)"))
            columns = {row[1] for row in result}

            if 'reminder_config' not in columns:
                session.execute(text("ALTER TABLE todos ADD COLUMN reminder_config TEXT"))
                print("✓ Added reminder_config column")
            else:
                print("✓ reminder_config column already exists")

            if 'last_reminder_at' not in columns:
                session.execute(text("ALTER TABLE todos ADD COLUMN last_reminder_at DATETIME"))
                print("✓ Added last_reminder_at column")
            else:
                print("✓ last_reminder_at column already exists")

            session.commit()
            print("\n✅ Migration completed successfully!")

        except Exception as e:
            print(f"\n❌ Migration failed: {e}")
            session.rollback()
            sys.exit(1)

if __name__ == "__main__":
    migrate()
