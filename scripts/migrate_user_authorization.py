#!/usr/bin/env python3
"""
Database migration: Add user authorization system

Changes:
- Add role, authorized_at, authorized_by columns to users table
- Drop pending_approvals table (no longer needed)
- Set owner as authorized with 'owner' role
"""

import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from assistant.db import init_db, get_session
from assistant.config import get as get_config
from sqlalchemy import text

def migrate():
    """Run the migration."""
    print("Starting database migration for user authorization system...")

    # Initialize database
    db_path = get_config("database.path", "data/assistant.db")
    init_db(db_path)

    with get_session() as session:
        try:
            # Check if columns already exist
            result = session.execute(text("PRAGMA table_info(users)"))
            columns = {row[1] for row in result.fetchall()}

            # Add new columns if they don't exist
            if 'role' not in columns:
                print("Adding 'role' column to users table...")
                session.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(20)"))

            if 'authorized_at' not in columns:
                print("Adding 'authorized_at' column to users table...")
                session.execute(text("ALTER TABLE users ADD COLUMN authorized_at DATETIME"))

            if 'authorized_by' not in columns:
                print("Adding 'authorized_by' column to users table...")
                session.execute(text("ALTER TABLE users ADD COLUMN authorized_by BIGINT"))

            session.commit()
            print("✅ User table columns added successfully")

            # Set owner as authorized
            owner_id = get_config("telegram.authorized_user_id")
            if owner_id:
                print(f"Setting owner (ID: {owner_id}) as authorized with 'owner' role...")
                session.execute(
                    text("""
                        UPDATE users
                        SET is_authorized = 1,
                            role = 'owner',
                            authorized_at = :now,
                            is_owner = 1
                        WHERE telegram_id = :owner_id
                    """),
                    {"owner_id": owner_id, "now": datetime.utcnow()}
                )
                session.commit()
                print("✅ Owner set as authorized")

            # Check if pending_approvals table exists
            result = session.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='pending_approvals'"
            ))
            if result.fetchone():
                print("Dropping 'pending_approvals' table...")
                session.execute(text("DROP TABLE pending_approvals"))
                session.commit()
                print("✅ pending_approvals table dropped")
            else:
                print("ℹ️  pending_approvals table does not exist (already migrated)")

            print("\n✅ Migration completed successfully!")
            print("\n📋 Summary:")
            print("  - Added role, authorized_at, authorized_by columns to users table")
            print("  - Set owner as authorized with 'owner' role")
            print("  - Removed pending_approvals table")
            print("\n🔒 New authorization system:")
            print("  - Unauthorized users will be prompted to request access")
            print("  - You'll receive authorization requests with role selection")
            print("  - Roles: owner (full access), employee (tasks), contact (messaging)")

        except Exception as e:
            session.rollback()
            print(f"\n❌ Migration failed: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == "__main__":
    migrate()
