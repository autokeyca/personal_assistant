#!/usr/bin/env python3
"""Run the Jarvis Agent API server."""

import logging
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from assistant.config import get
from assistant.db import init_db

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def main():
    """Run the API server."""
    # Initialize database
    db_path = get("database.path")
    init_db(db_path)

    # Get API configuration
    host = get("api.host", "127.0.0.1")
    port = get("api.port", 8000)

    logger.info(f"Starting Jarvis Agent API on {host}:{port}")
    logger.info("API documentation available at:")
    logger.info(f"  - Swagger UI: http://{host}:{port}/docs")
    logger.info(f"  - ReDoc: http://{host}:{port}/redoc")

    # Import here to avoid circular imports
    import uvicorn
    from assistant.api import app

    # Run server
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=True,
    )


if __name__ == "__main__":
    main()
