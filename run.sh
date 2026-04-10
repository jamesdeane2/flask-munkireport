#!/bin/bash
# Flask MunkiReport API Server Startup Script
# For use with macOS LaunchAgent

# Change to the project directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Determine the correct Python and venv paths
PYTHON_PATH="/opt/homebrew/opt/python@3.11/bin/python3.11"
VENV_PATH="$DIR/.venv"

# Check if virtual environment exists
if [ ! -d "$VENV_PATH" ]; then
    echo "Creating virtual environment..."
    "$PYTHON_PATH" -m venv "$VENV_PATH"
fi

# Activate virtual environment
source "$VENV_PATH/bin/activate"

# Install requirements if needed
if [ ! -f "$VENV_PATH/.installed" ]; then
    echo "Installing requirements..."
    pip install -r requirements.txt
    touch "$VENV_PATH/.installed"
fi

# Start the server using gunicorn for production
# Use python run.py for development mode
"$VENV_PATH/bin/python" -m flask run --host=0.0.0.0 --port=5030
