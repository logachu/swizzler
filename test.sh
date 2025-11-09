#!/bin/bash
# Test runner script for use case validation

set -e

echo "Running use case tests..."
echo ""

# Run tests using venv python
venv/bin/python3.13 test_use_cases.py

echo ""
echo "Tests complete!"
