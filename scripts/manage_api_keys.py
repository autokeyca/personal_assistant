#!/usr/bin/env python3
"""Manage API keys for Jarvis Agent API."""

import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from assistant.db import get_session, init_db, APIKey
from assistant.config import get
from assistant.api.auth import generate_api_key, hash_api_key


def create_key(name: str, description: str = None, permissions: str = "*"):
    """Create a new API key."""
    # Initialize database
    db_path = get("database.path")
    init_db(db_path)

    # Generate new key
    api_key = generate_api_key()
    key_hash = hash_api_key(api_key)

    with get_session() as session:
        # Create key record
        key_obj = APIKey(
            key=key_hash,
            name=name,
            description=description,
            permissions=permissions,
            is_active=True
        )
        session.add(key_obj)
        session.commit()
        session.refresh(key_obj)

        print("\n✅ API Key Created Successfully!")
        print("\n" + "="*60)
        print(f"Agent Name: {name}")
        print(f"Description: {description or 'N/A'}")
        print(f"Permissions: {permissions}")
        print(f"Created: {key_obj.created_at}")
        print("\n" + "="*60)
        print(f"API Key: {api_key}")
        print("="*60)
        print("\n⚠️  IMPORTANT: Save this key now - it won't be shown again!")
        print()


def list_keys():
    """List all API keys."""
    db_path = get("database.path")
    init_db(db_path)

    with get_session() as session:
        keys = session.query(APIKey).order_by(APIKey.created_at.desc()).all()

        if not keys:
            print("No API keys found.")
            return

        print("\nAPI Keys:")
        print("="*80)
        for key in keys:
            status = "✓ Active" if key.is_active else "✗ Inactive"
            last_used = key.last_used.strftime("%Y-%m-%d %H:%M") if key.last_used else "Never"

            print(f"\n ID: {key.id}")
            print(f" Name: {key.name}")
            print(f" Description: {key.description or 'N/A'}")
            print(f" Permissions: {key.permissions}")
            print(f" Status: {status}")
            print(f" Created: {key.created_at.strftime('%Y-%m-%d %H:%M')}")
            print(f" Last Used: {last_used}")
            print(f" Usage Count: {key.usage_count}")

        print("="*80)
        print()


def deactivate_key(key_id: int):
    """Deactivate an API key."""
    db_path = get("database.path")
    init_db(db_path)

    with get_session() as session:
        key = session.query(APIKey).filter_by(id=key_id).first()

        if not key:
            print(f"❌ API key #{key_id} not found.")
            return

        key.is_active = False
        session.commit()

        print(f"\n✅ API key '{key.name}' (ID: {key_id}) has been deactivated.")
        print()


def activate_key(key_id: int):
    """Activate an API key."""
    db_path = get("database.path")
    init_db(db_path)

    with get_session() as session:
        key = session.query(APIKey).filter_by(id=key_id).first()

        if not key:
            print(f"❌ API key #{key_id} not found.")
            return

        key.is_active = True
        session.commit()

        print(f"\n✅ API key '{key.name}' (ID: {key_id}) has been activated.")
        print()


def delete_key(key_id: int):
    """Delete an API key."""
    db_path = get("database.path")
    init_db(db_path)

    with get_session() as session:
        key = session.query(APIKey).filter_by(id=key_id).first()

        if not key:
            print(f"❌ API key #{key_id} not found.")
            return

        name = key.name
        session.delete(key)
        session.commit()

        print(f"\n✅ API key '{name}' (ID: {key_id}) has been deleted.")
        print()


def main():
    parser = argparse.ArgumentParser(description="Manage API keys for Jarvis Agent API")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new API key")
    create_parser.add_argument("name", help="Agent name/identifier")
    create_parser.add_argument("--description", "-d", help="Description of this agent")
    create_parser.add_argument("--permissions", "-p", default="*",
                              help="Permissions (default: * for all)")

    # List command
    subparsers.add_parser("list", help="List all API keys")

    # Deactivate command
    deactivate_parser = subparsers.add_parser("deactivate", help="Deactivate an API key")
    deactivate_parser.add_argument("id", type=int, help="API key ID")

    # Activate command
    activate_parser = subparsers.add_parser("activate", help="Activate an API key")
    activate_parser.add_argument("id", type=int, help="API key ID")

    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete an API key")
    delete_parser.add_argument("id", type=int, help="API key ID")

    args = parser.parse_args()

    if args.command == "create":
        create_key(args.name, args.description, args.permissions)
    elif args.command == "list":
        list_keys()
    elif args.command == "deactivate":
        deactivate_key(args.id)
    elif args.command == "activate":
        activate_key(args.id)
    elif args.command == "delete":
        delete_key(args.id)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
