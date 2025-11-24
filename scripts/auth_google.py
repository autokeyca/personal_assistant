#!/usr/bin/env python3
"""Script to authenticate with Google APIs.

Run this once to get your Google OAuth token.
"""

import sys
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from assistant.config import load_config
from assistant.services.google_auth import get_google_auth


def main():
    """Authenticate with Google."""
    config_path = project_root / "config" / "config.yaml"

    if not config_path.exists():
        print("Error: config/config.yaml not found")
        sys.exit(1)

    load_config(str(config_path))

    print("Authenticating with Google...")
    print("A browser window will open for authentication.")
    print("")

    auth = get_google_auth()

    try:
        creds = auth.get_credentials()
        print("Authentication successful!")
        print(f"Token saved to: {auth.token_file}")
    except Exception as e:
        print(f"Authentication failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
