#!/bin/bash
# Verification Script - Backend Fix Validation
# Run this after applying the fixes to verify everything is working

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║        Backend Fix Verification Script                        ║"
echo "║                    404 Error Resolution                        ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Check credentials
echo "Step 1: Checking DhanHQ Credentials..."
echo "─────────────────────────────────────────────────────────────────"

if [ -z "$DHAN_CLIENT_ID" ]; then
    echo -e "${RED}✗ DHAN_CLIENT_ID not set${NC}"
    echo "  Set with: export DHAN_CLIENT_ID=\"your_client_id\""
else
    echo -e "${GREEN}✓ DHAN_CLIENT_ID is set${NC}"
fi

if [ -z "$DHAN_ACCESS_TOKEN" ]; then
    echo -e "${RED}✗ DHAN_ACCESS_TOKEN not set${NC}"
    echo "  Set with: export DHAN_ACCESS_TOKEN=\"your_token\""
else
    echo -e "${GREEN}✓ DHAN_ACCESS_TOKEN is set${NC}"
fi

echo ""

# Step 2: Check if backend is running
echo "Step 2: Checking Backend Status..."
echo "─────────────────────────────────────────────────────────────────"

if curl -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend is running on port 8000${NC}"
else
    echo -e "${RED}✗ Backend is not responding on port 8000${NC}"
    echo "  Start backend with: cd fastapi_backend && python app/main.py"
    exit 1
fi

echo ""

# Step 3: Check cache statistics
echo "Step 3: Checking Cache Population..."
echo "─────────────────────────────────────────────────────────────────"

CACHE_STATS=$(curl -s http://127.0.0.1:8000/health | grep -o '"subscriptions":[0-9]*')
if [ ! -z "$CACHE_STATS" ]; then
    echo -e "${GREEN}✓ Backend responded to health check${NC}"
else
    echo -e "${RED}✗ Backend health check failed${NC}"
fi

echo ""

# Step 4: Test the endpoint
echo "Step 4: Testing /options/live Endpoint..."
echo "─────────────────────────────────────────────────────────────────"

RESPONSE=$(curl -s -w "\n%{http_code}" http://127.0.0.1:8000/api/v2/options/live?underlying=NIFTY\&expiry=2026-02-11)
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" == "200" ]; then
    echo -e "${GREEN}✓ Endpoint returned 200 OK${NC}"
    echo "  Response includes data for option chain"
elif [ "$HTTP_CODE" == "404" ]; then
    echo -e "${RED}✗ Endpoint returned 404 - Cache still empty${NC}"
    echo "  Check backend logs for: 'populate_with_live_data' errors"
    exit 1
else
    echo -e "${RED}✗ Endpoint returned $HTTP_CODE${NC}"
    echo "  Response: $BODY"
fi

echo ""

# Step 5: Check code changes
echo "Step 5: Verifying Code Changes..."
echo "─────────────────────────────────────────────────────────────────"

# Check main.py
if grep -q "Cache verified and ready" fastapi_backend/app/main.py; then
    echo -e "${GREEN}✓ main.py contains cache verification${NC}"
else
    echo -e "${RED}✗ main.py missing cache verification${NC}"
fi

# Check live_feed.py
if grep -q "update_option_price_from_websocket" fastapi_backend/app/dhan/live_feed.py; then
    echo -e "${GREEN}✓ live_feed.py contains WebSocket integration${NC}"
else
    echo -e "${RED}✗ live_feed.py missing WebSocket integration${NC}"
fi

# Check service
if grep -q "def update_option_price_from_websocket" fastapi_backend/app/services/authoritative_option_chain_service.py; then
    echo -e "${GREEN}✓ Service contains new cache update method${NC}"
else
    echo -e "${RED}✗ Service missing cache update method${NC}"
fi

echo ""

# Step 6: Summary
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                       SUMMARY                                  ║"
echo "╚════════════════════════════════════════════════════════════════╝"

if [ "$HTTP_CODE" == "200" ]; then
    echo -e "${GREEN}✓ ALL CHECKS PASSED${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Start frontend: cd frontend && npm run dev"
    echo "2. Open http://localhost:5173"
    echo "3. Navigate to OPTIONS page"
    echo "4. Select NIFTY → Expiry → View prices"
    echo ""
    echo "Monitor backend logs for realtime updates:"
    echo "  tail -f backend.log | grep 'Updated'"
else
    echo -e "${RED}✗ CHECKS FAILED${NC}"
    echo ""
    echo "Troubleshooting steps:"
    echo "1. Verify credentials are set"
    echo "2. Check backend logs for errors"
    echo "3. Ensure DhanHQ API token is valid"
    echo "4. Restart backend with credentials set"
fi

echo ""
echo "For detailed documentation, see:"
echo "  - QUICK_START_GUIDE.md"
echo "  - BACKEND_FIX_STATUS.md"
echo "  - IMPLEMENTATION_COMPLETE.md"

