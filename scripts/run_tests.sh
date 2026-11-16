#!/usr/bin/env bash
set -e

echo "=== Running Premiere AI Editor Test Suite ==="

echo "1. Python Unit Tests..."
python3 -m unittest discover -s tests/unit -p "test_*.py"

echo "2. JavaScript Unit Tests..."
node tests/unit/test_cut_planner.js

echo "3. Python Engine API Integration Tests..."
python3 -m unittest discover -s tests/integration -p "test_*.py"

echo "4. Premiere Pro Mock Integration Tests..."
node tests/integration/test_premiere_mock.js

echo "=== All Tests Passed Successfully! ==="
