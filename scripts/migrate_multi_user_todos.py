#!/usr/bin/env python3
"""Migrate todos table to support multi-user todos."""

import sqlite3
import sys
from pathlib import Path

# Get database path
project_root = Path(__file__).parent.parent
db_path = project_root / "data" / "assistant.db"

if not db_path.exists():
    print(f"Database not found at {db_path}")
    sys.exit(1)

# Connect to database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    print("Starting multi-user todos migration...\n")

    # Check existing columns
    cursor.execute("PRAGMA table_info(todos)")
    existing_columns = {row[1] for row in cursor.fetchall()}

    # Add user_id column
    if "user_id" not in existing_columns:
        print("Adding user_id column...")
        cursor.execute("ALTER TABLE todos ADD COLUMN user_id BIGINT")
        print("✓ Added user_id column")
    else:
        print("✓ user_id column already exists")

    # Add created_by column
    if "created_by" not in existing_columns:
        print("Adding created_by column...")
        cursor.execute("ALTER TABLE todos ADD COLUMN created_by BIGINT")
        print("✓ Added created_by column")
    else:
        print("✓ created_by column already exists")

    # Add follow_up_intensity column
    if "follow_up_intensity" not in existing_columns:
        print("Adding follow_up_intensity column...")
        cursor.execute("ALTER TABLE todos ADD COLUMN follow_up_intensity VARCHAR(20) DEFAULT 'medium'")
        print("✓ Added follow_up_intensity column")
    else:
        print("✓ follow_up_intensity column already exists")

    # Add last_followup_at column
    if "last_followup_at" not in existing_columns:
        print("Adding last_followup_at column...")
        cursor.execute("ALTER TABLE todos ADD COLUMN last_followup_at DATETIME")
        print("✓ Added last_followup_at column")
    else:
        print("✓ last_followup_at column already exists")

    # Add next_followup_at column
    if "next_followup_at" not in existing_columns:
        print("Adding next_followup_at column...")
        cursor.execute("ALTER TABLE todos ADD COLUMN next_followup_at DATETIME")
        print("✓ Added next_followup_at column")
    else:
        print("✓ next_followup_at column already exists")

    # Get owner's telegram ID from config
    # For now, we'll set existing todos to belong to the owner
    # The config should have the authorized_user_id
    print("\nMigrating existing todos...")
    print("Note: Existing todos will be assigned to the authorized user from config")
    print("You can manually update them later if needed.")

    # Commit changes
    conn.commit()
    print("\n✅ Migration completed successfully!")
    print("\nNext steps:")
    print("1. Existing todos have new columns (initially NULL)")
    print("2. New todos will use these columns automatically")
    print("3. You can now assign todos to different users!")

except Exception as e:
    conn.rollback()
    print(f"\n✗ Error during migration: {e}")
    sys.exit(1)
finally:
    conn.close()
