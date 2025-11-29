#!/usr/bin/env python3
"""Add channel column to conversation_history table."""

import sqlite3
import sys
from pathlib import Path

# Get database path
project_root = Path(__file__).parent.parent
db_path = project_root / "data" / "assistant.db"

if not db_path.exists():
    print(f"Database not found at {db_path}")
    sys.exit(1)

# Connect and add column
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # Check if column already exists
    cursor.execute("PRAGMA table_info(conversation_history)")
    columns = [row[1] for row in cursor.fetchall()]

    if "channel" in columns:
        print("✓ Column 'channel' already exists in conversation_history table")
    else:
        # Add the column
        cursor.execute("ALTER TABLE conversation_history ADD COLUMN channel VARCHAR(20)")
        conn.commit()
        print("✓ Successfully added 'channel' column to conversation_history table")

except sqlite3.OperationalError as e:
    print(f"✗ Error: {e}")
    sys.exit(1)
finally:
    conn.close()
