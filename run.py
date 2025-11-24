#!/usr/bin/env python3
"""Main entry point for the Personal Assistant."""

import sys
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from assistant.config import load_config
from assistant.bot import run_bot


def main():
    """Run the personal assistant bot."""
    # Load configuration
    config_path = project_root / "config" / "config.yaml"

    if not config_path.exists():
        print("Error: config/config.yaml not found")
        print("Copy config/config.example.yaml to config/config.yaml and configure it")
        sys.exit(1)

    load_config(str(config_path))

    # Run the bot
    run_bot()


if __name__ == "__main__":
    main()
