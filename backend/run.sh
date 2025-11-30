#!/bin/bash
# Run the Quiz Taker backend

cd "$(dirname "$0")"

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

# Sync dependencies
echo "Installing dependencies..."
uv sync

# Run the server
echo "Starting Quiz Taker backend on http://127.0.0.1:8087"
uv run uvicorn app.main:app --reload --port 8087

