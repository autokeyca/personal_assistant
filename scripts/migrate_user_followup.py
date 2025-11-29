#!/usr/bin/env python3
"""Add follow-up settings to users table."""

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
    print("Adding follow-up settings to users table...\n")

    # Check existing columns
    cursor.execute("PRAGMA table_info(users)")
    existing_columns = {row[1] for row in cursor.fetchall()}

    # Add default_followup_intensity column
    if "default_followup_intensity" not in existing_columns:
        print("Adding default_followup_intensity column...")
        cursor.execute("ALTER TABLE users ADD COLUMN default_followup_intensity VARCHAR(20) DEFAULT 'medium'")
        print("✓ Added default_followup_intensity column")
    else:
        print("✓ default_followup_intensity column already exists")

    # Add followup_enabled column
    if "followup_enabled" not in existing_columns:
        print("Adding followup_enabled column...")
        cursor.execute("ALTER TABLE users ADD COLUMN followup_enabled BOOLEAN DEFAULT 1")
        print("✓ Added followup_enabled column")
    else:
        print("✓ followup_enabled column already exists")

    # Commit changes
    conn.commit()
    print("\n✅ User follow-up settings migration completed!")

except Exception as e:
    conn.rollback()
    print(f"\n✗ Error during migration: {e}")
    sys.exit(1)
finally:
    conn.close()
