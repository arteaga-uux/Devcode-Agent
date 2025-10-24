#!/bin/bash
# Quick local test script for GNOME Assistant

set -e

echo "🧪 Running local tests for GNOME Assistant..."
echo ""

# Check if we're in the right directory
if [ ! -f "test_local.py" ]; then
    echo "❌ Error: Please run this script from the my_agent directory"
    exit 1
fi

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "🐍 Python version: $python_version"

# Check if .env file exists
if [ -f "../.env" ]; then
    echo "✅ .env file found"
    export $(cat ../.env | grep -v '^#' | xargs)
else
    echo "⚠️  No .env file found (looking for ../.env)"
    echo "   You may need to set OPENAI_API_KEY manually"
fi

# Check if virtualenv is active
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  No virtual environment detected"
    echo "   Consider activating a venv for cleaner testing"
else
    echo "✅ Virtual environment active: $VIRTUAL_ENV"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Run the test
python3 test_local.py

exit_code=$?

echo ""
if [ $exit_code -eq 0 ]; then
    echo "✅ All tests passed!"
else
    echo "❌ Tests failed with exit code $exit_code"
fi

exit $exit_code

