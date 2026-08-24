#!/bin/bash

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$PROJECT_DIR/clicker-bridge"

echo "========================================"
echo " PuppyClicker -> XToys Setup"
echo "========================================"
echo

# ------------------------------------------------------------
# Check Python
# ------------------------------------------------------------

if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: Python 3 was not found."
    echo "Install Python 3 and try again."
    exit 1
fi

echo "Python found:"
python3 --version
echo

# ------------------------------------------------------------
# Check tkinter
# ------------------------------------------------------------

if ! python3 -c "import tkinter" >/dev/null 2>&1; then
    echo "WARNING: tkinter is not installed."
    echo
    echo "On Ubuntu/Debian, install it with:"
    echo
    echo "    sudo apt install python3-tk"
    echo
    exit 1
fi

# ------------------------------------------------------------
# Create virtual environment
# ------------------------------------------------------------

if [ -d "$VENV_DIR" ]; then
    echo "Virtual environment already exists:"
    echo "$VENV_DIR"
else
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

echo

# ------------------------------------------------------------
# Upgrade pip
# ------------------------------------------------------------

echo "Updating pip..."

"$VENV_DIR/bin/python" -m pip install --upgrade pip

echo

# ------------------------------------------------------------
# Install requirements
# ------------------------------------------------------------

if [ ! -f "$PROJECT_DIR/requirements.txt" ]; then
    echo "ERROR: requirements.txt was not found."
    exit 1
fi

echo "Installing requirements..."

"$VENV_DIR/bin/python" -m pip install -r "$PROJECT_DIR/requirements.txt"

echo

# ------------------------------------------------------------
# Make launcher executable
# ------------------------------------------------------------

if [ -f "$PROJECT_DIR/launcher.sh" ]; then
    chmod +x "$PROJECT_DIR/launcher.sh"
fi

echo "========================================"
echo " Setup complete"
echo "========================================"
echo
echo "Virtual environment:"
echo "$VENV_DIR"
echo
echo "You can now run:"
echo
echo "    ./launcher.sh"
echo
