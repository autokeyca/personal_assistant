#!/bin/bash
# Setup script for Personal Assistant

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Personal Assistant Setup ==="
echo ""

# Check Python version
python3 --version || { echo "Python 3 is required"; exit 1; }

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv "$PROJECT_DIR/venv"

# Activate and install dependencies
echo "Installing dependencies..."
source "$PROJECT_DIR/venv/bin/activate"
pip install --upgrade pip
pip install -r "$PROJECT_DIR/requirements.txt"

# Create directories
echo "Creating directories..."
mkdir -p "$PROJECT_DIR/data"
mkdir -p "$PROJECT_DIR/logs"

# Copy config if needed
if [ ! -f "$PROJECT_DIR/config/config.yaml" ]; then
    echo "Copying example config..."
    cp "$PROJECT_DIR/config/config.example.yaml" "$PROJECT_DIR/config/config.yaml"
    echo ""
    echo "IMPORTANT: Edit config/config.yaml with your settings:"
    echo "  - Telegram bot token (from @BotFather)"
    echo "  - Your Telegram user ID (from @userinfobot)"
    echo "  - Google Cloud credentials"
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Edit config/config.yaml with your settings"
echo "2. Set up Google Cloud credentials (see README)"
echo "3. Run: source venv/bin/activate && python run.py"
echo ""
echo "To install as a service:"
echo "  sudo cp scripts/personal-assistant.service /etc/systemd/system/"
echo "  sudo systemctl daemon-reload"
echo "  sudo systemctl enable personal-assistant"
echo "  sudo systemctl start personal-assistant"
