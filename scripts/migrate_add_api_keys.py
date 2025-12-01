#!/usr/bin/env python3
"""Migration script to add api_keys table."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from assistant.db import get_session, init_db
from assistant.config import get
from sqlalchemy import text

def migrate():
    """Add api_keys table."""
    print("Adding api_keys table...")

    # Initialize database connection
    db_path = get("database.path")
    init_db(db_path)

    with get_session() as session:
        try:
            # Check if table already exists
            result = session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='api_keys'"))
            if result.fetchone():
                print("✓ api_keys table already exists")
                return

            # Create api_keys table
            session.execute(text("""
                CREATE TABLE api_keys (
                    id INTEGER PRIMARY KEY,
                    key VARCHAR(64) UNIQUE NOT NULL,
                    name VARCHAR(200) NOT NULL,
                    description TEXT,
                    permissions TEXT DEFAULT '*',
                    is_active BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_used DATETIME,
                    usage_count INTEGER DEFAULT 0
                )
            """))
            session.commit()
            print("✓ Created api_keys table")

            print("\n✅ Migration completed successfully!")

        except Exception as e:
            print(f"\n❌ Migration failed: {e}")
            session.rollback()
            sys.exit(1)

if __name__ == "__main__":
    migrate()
