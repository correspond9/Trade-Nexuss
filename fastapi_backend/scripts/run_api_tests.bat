@echo off
echo -----API TEST START-----
curl -s http://127.0.0.1:8000/api/v2/test
echo.
echo -----ADD WATCHLIST-----
echo Forcing markets open (NSE,BSE,MCX)...
curl -s -X POST "http://127.0.0.1:8000/api/v2/admin/market/force" -H "Content-Type: application/json" -d "{\"exchange\":\"NSE\",\"state\":\"open\"}"
echo.
curl -s -X POST "http://127.0.0.1:8000/api/v2/admin/market/force" -H "Content-Type: application/json" -d "{\"exchange\":\"BSE\",\"state\":\"open\"}"
echo.
curl -s -X POST "http://127.0.0.1:8000/api/v2/admin/market/force" -H "Content-Type: application/json" -d "{\"exchange\":\"MCX\",\"state\":\"open\"}"
echo.
echo Updating dashboard prices for liquidity...
curl -s -X POST "http://127.0.0.1:8000/api/v2/admin/price/update" -H "Content-Type: application/json" -d "{\"symbol\":\"NIFTY\",\"price\":18000}"
echo.
curl -s -X POST "http://127.0.0.1:8000/api/v2/admin/price/update" -H "Content-Type: application/json" -d "{\"symbol\":\"BANKNIFTY\",\"price\":43000}"
echo.
curl -s -X POST "http://127.0.0.1:8000/api/v2/admin/price/update" -H "Content-Type: application/json" -d "{\"symbol\":\"SENSEX\",\"price\":72000}"
echo.
curl -s -X POST "http://127.0.0.1:8000/api/v2/admin/price/update" -H "Content-Type: application/json" -d "{\"symbol\":\"CRUDEOIL\",\"price\":6100}"
echo.
curl -s -X POST "http://127.0.0.1:8000/api/v2/admin/price/update" -H "Content-Type: application/json" -d "{\"symbol\":\"RELIANCE\",\"price\":2300}"

echo -----ADD WATCHLIST-----
curl -s -X POST "http://127.0.0.1:8000/api/v2/watchlist/add" -H "Content-Type: application/json" -d "{\"user_id\":1,\"symbol\":\"NIFTY\",\"expiry\":\"26FEB2026\",\"instrument_type\":\"INDEX_OPTION\",\"underlying_ltp\":18000}"
echo.

echo -----ORDER 1: RELIANCE (EQUITY)-----
echo Seeding market depth for RELIANCE (equity)
curl -s -X POST "http://127.0.0.1:8000/api/v2/admin/market/depth" -H "Content-Type: application/json" -d "{\"symbol\":\"RELIANCE\",\"depth\":{\"bids\":[{\"price\":2300,\"qty\":100}],\"asks\":[{\"price\":2301,\"qty\":100}]}}"
curl -s -X POST "http://127.0.0.1:8000/api/v2/trading/orders" -H "Content-Type: application/json" -d "{\"user_id\":1,\"symbol\":\"RELIANCE\",\"exchange_segment\":\"NSE_EQ\",\"transaction_type\":\"BUY\",\"quantity\":1,\"order_type\":\"MARKET\",\"product_type\":\"MIS\"}"
echo.

echo -----ORDER 2: RELIANCE OPTION (NSE_FNO)-----
echo Seeding market depth for RELIANCE option symbol used in test
curl -s -X POST "http://127.0.0.1:8000/api/v2/admin/market/depth" -H "Content-Type: application/json" -d "{\"symbol\":\"RELIANCE 26FEB2026 3300 CE\",\"depth\":{\"bids\":[{\"price\":1.0,\"qty\":100}],\"asks\":[{\"price\":1.5,\"qty\":100}]}}"
curl -s -X POST "http://127.0.0.1:8000/api/v2/trading/orders" -H "Content-Type: application/json" -d "{\"user_id\":1,\"symbol\":\"RELIANCE 26FEB2026 3300 CE\",\"exchange_segment\":\"NSE_FNO\",\"transaction_type\":\"BUY\",\"quantity\":1,\"order_type\":\"MARKET\",\"product_type\":\"MIS\"}"
echo.

echo -----ORDER 3: SENSEX OPTION (BSE_FNO)-----
echo Seeding market depth for SENSEX option used in test
curl -s -X POST "http://127.0.0.1:8000/api/v2/admin/market/depth" -H "Content-Type: application/json" -d "{\"symbol\":\"SENSEX 12FEB2026 84000 PE\",\"depth\":{\"bids\":[{\"price\":10,\"qty\":50}],\"asks\":[{\"price\":11,\"qty\":50}]}}"
curl -s -X POST "http://127.0.0.1:8000/api/v2/trading/orders" -H "Content-Type: application/json" -d "{\"user_id\":1,\"symbol\":\"SENSEX 12FEB2026 84000 PE\",\"exchange_segment\":\"BSE_FNO\",\"transaction_type\":\"BUY\",\"quantity\":1,\"order_type\":\"MARKET\",\"product_type\":\"MIS\"}"
echo.

echo -----ORDER 4: MCX FUTURE (CRUDEOIL)-----
echo Seeding market depth for CRUDEOIL future
curl -s -X POST "http://127.0.0.1:8000/api/v2/admin/market/depth" -H "Content-Type: application/json" -d "{\"symbol\":\"CRUDEOIL\",\"depth\":{\"bids\":[{\"price\":6100,\"qty\":10}],\"asks\":[{\"price\":6105,\"qty\":10}]}}"
curl -s -X POST "http://127.0.0.1:8000/api/v2/trading/orders" -H "Content-Type: application/json" -d "{\"user_id\":1,\"symbol\":\"CRUDEOIL\",\"exchange_segment\":\"MCX_COMM\",\"transaction_type\":\"BUY\",\"quantity\":1,\"order_type\":\"MARKET\",\"product_type\":\"MIS\"}"
echo.

echo -----ORDER 5: MCX OPTION (CRUDEOIL)-----
echo Seeding market depth for CRUDEOIL option used in test
curl -s -X POST "http://127.0.0.1:8000/api/v2/admin/market/depth" -H "Content-Type: application/json" -d "{\"symbol\":\"CRUDEOIL 26FEB2026 6000 CE\",\"depth\":{\"bids\":[{\"price\":5,\"qty\":20}],\"asks\":[{\"price\":6,\"qty\":20}]}}"
curl -s -X POST "http://127.0.0.1:8000/api/v2/trading/orders" -H "Content-Type: application/json" -d "{\"user_id\":1,\"symbol\":\"CRUDEOIL 26FEB2026 6000 CE\",\"exchange_segment\":\"MCX_COMM\",\"transaction_type\":\"BUY\",\"quantity\":1,\"order_type\":\"MARKET\",\"product_type\":\"MIS\"}"
echo.
echo -----LIST ORDERS-----
curl -s http://127.0.0.1:8000/api/v2/trading/orders?user_id=1
echo.
echo -----API TEST END-----
pause
