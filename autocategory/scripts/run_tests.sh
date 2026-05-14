#!/bin/bash
# Run all tests for AutoCategory

set -e  # Exit on error

echo "========================================="
echo "Running AutoCategory Test Suite"
echo "========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Change to API directory
cd "$(dirname "$0")/../api"

echo "📦 Installing dependencies..."
pip install -r requirements.txt -q

echo ""
echo "========================================="
echo "1. Backend Unit Tests"
echo "========================================="
pytest tests/ -v --ignore=tests/test_e2e.py --ignore=tests/test_performance.py --ignore=tests/test_security.py

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Unit tests passed${NC}"
else
    echo -e "${RED}❌ Unit tests failed${NC}"
    exit 1
fi

echo ""
echo "========================================="
echo "2. End-to-End Tests"
echo "========================================="
pytest tests/test_e2e.py -v

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ E2E tests passed${NC}"
else
    echo -e "${RED}❌ E2E tests failed${NC}"
    exit 1
fi

echo ""
echo "========================================="
echo "3. Security Tests"
echo "========================================="
pytest tests/test_security.py -v

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Security tests passed${NC}"
else
    echo -e "${RED}❌ Security tests failed${NC}"
    exit 1
fi

echo ""
echo "========================================="
echo "4. Performance Tests"
echo "========================================="
echo -e "${YELLOW}⚠️  Running performance tests (may take a few minutes)${NC}"
pytest tests/test_performance.py -v -m performance

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Performance tests passed${NC}"
else
    echo -e "${YELLOW}⚠️  Performance tests had issues (non-blocking)${NC}"
fi

echo ""
echo "========================================="
echo "5. Test Coverage Report"
echo "========================================="
pytest tests/ --cov=. --cov-report=term-missing --cov-report=html

echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}✅ All tests completed!${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo "Coverage report: file://$(pwd)/htmlcov/index.html"
