#!/bin/bash
# Run the Quiz Taker backend

cd "$(dirname "$0")"

# Load .env file if it exists
if [ -f .env ]; then
    echo "Loading environment from .env file..."
    set -a
    source .env
    set +a
fi

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "uv is not installed. Please install it: https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi

# Check for OPENAI_API_KEY
if [ -z "$OPENAI_API_KEY" ]; then
    echo "Error: OPENAI_API_KEY environment variable is not set"
    exit 1
fi

# Get port from environment or default
BACKEND_PORT="${BACKEND_PORT:-8000}"
BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"

# Sync dependencies
echo "Installing dependencies..."
uv sync

# Run the server
echo "Starting Quiz Taker backend on http://${BACKEND_HOST}:${BACKEND_PORT}"
uv run uvicorn app.main:app --reload --host "${BACKEND_HOST}" --port "${BACKEND_PORT}"
