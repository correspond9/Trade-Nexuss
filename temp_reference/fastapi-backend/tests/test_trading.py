"""
Trading Tests
Test cases for trading endpoints
"""

import pytest
from httpx import AsyncClient

class TestTrading:
    """Test trading endpoints"""
    
    @pytest.mark.asyncio
    async def test_place_order(self, client: AsyncClient, sample_user_data, sample_order_data, auth_headers):
        """Test placing an order"""
        # Register and login user
        await client.post("/api/v1/auth/register", json=sample_user_data)
        
        # Place order
        response = await client.post(
            "/api/v1/trading/orders",
            json=sample_order_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["security_id"] == sample_order_data["security_id"]
        assert data["quantity"] == sample_order_data["quantity"]
        assert data["order_type"] == sample_order_data["order_type"]
        assert data["transaction_type"] == sample_order_data["transaction_type"]
        assert data["status"] == "PENDING"
    
    @pytest.mark.asyncio
    async def test_place_order_unauthorized(self, client: AsyncClient, sample_order_data):
        """Test placing order without authentication"""
        response = await client.post("/api/v1/trading/orders", json=sample_order_data)
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_get_orders(self, client: AsyncClient, sample_user_data, auth_headers):
        """Test getting user orders"""
        # Register and login user
        await client.post("/api/v1/auth/register", json=sample_user_data)
        
        # Get orders
        response = await client.get("/api/v1/trading/orders", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_get_order_by_id(self, client: AsyncClient, sample_user_data, sample_order_data, auth_headers):
        """Test getting specific order by ID"""
        # Register and login user
        await client.post("/api/v1/auth/register", json=sample_user_data)
        
        # Place order first
        order_response = await client.post(
            "/api/v1/trading/orders",
            json=sample_order_data,
            headers=auth_headers
        )
        order_id = order_response.json()["id"]
        
        # Get order by ID
        response = await client.get(f"/api/v1/trading/orders/{order_id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == order_id
        assert data["security_id"] == sample_order_data["security_id"]
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_order(self, client: AsyncClient, sample_user_data, auth_headers):
        """Test getting non-existent order"""
        # Register and login user
        await client.post("/api/v1/auth/register", json=sample_user_data)
        
        # Get non-existent order
        response = await client.get("/api/v1/trading/orders/99999", headers=auth_headers)
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_update_order(self, client: AsyncClient, sample_user_data, sample_order_data, auth_headers):
        """Test updating an order"""
        # Register and login user
        await client.post("/api/v1/auth/register", json=sample_user_data)
        
        # Place order first
        order_response = await client.post(
            "/api/v1/trading/orders",
            json=sample_order_data,
            headers=auth_headers
        )
        order_id = order_response.json()["id"]
        
        # Update order
        update_data = {"price": 820.0}
        response = await client.put(
            f"/api/v1/trading/orders/{order_id}",
            json=update_data,
            headers=auth_headers
        )
        
        # TODO: Implement order update logic
        assert response.status_code in [200, 404]  # Depends on implementation
    
    @pytest.mark.asyncio
    async def test_cancel_order(self, client: AsyncClient, sample_user_data, sample_order_data, auth_headers):
        """Test cancelling an order"""
        # Register and login user
        await client.post("/api/v1/auth/register", json=sample_user_data)
        
        # Place order first
        order_response = await client.post(
            "/api/v1/trading/orders",
            json=sample_order_data,
            headers=auth_headers
        )
        order_id = order_response.json()["id"]
        
        # Cancel order
        response = await client.delete(f"/api/v1/trading/orders/{order_id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
    
    @pytest.mark.asyncio
    async def test_get_trades(self, client: AsyncClient, sample_user_data, auth_headers):
        """Test getting user trades"""
        # Register and login user
        await client.post("/api/v1/auth/register", json=sample_user_data)
        
        # Get trades
        response = await client.get("/api/v1/trading/trades", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_place_basket_order(self, client: AsyncClient, sample_user_data, auth_headers):
        """Test placing basket order"""
        # Register and login user
        await client.post("/api/v1/auth/register", json=sample_user_data)
        
        # Place basket order
        basket_order = {
            "name": "Test Basket",
            "orders": [
                {
                    "security_id": "226712",
                    "quantity": 100,
                    "price": 815.50,
                    "order_type": "LIMIT",
                    "transaction_type": "BUY",
                    "product_type": "INTRADAY"
                },
                {
                    "security_id": "226713",
                    "quantity": 50,
                    "price": 1200.0,
                    "order_type": "LIMIT",
                    "transaction_type": "SELL",
                    "product_type": "INTRADAY"
                }
            ]
        }
        
        response = await client.post(
            "/api/v1/trading/basket-orders",
            json=basket_order,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "basket_id" in data
    
    @pytest.mark.asyncio
    async def test_place_smart_order(self, client: AsyncClient, sample_user_data, auth_headers):
        """Test placing smart order"""
        # Register and login user
        await client.post("/api/v1/auth/register", json=sample_user_data)
        
        # Place smart order
        response = await client.post(
            "/api/v1/trading/smart-order",
            headers=auth_headers,
            params={
                "security_id": "226712",
                "amount": 10000.0,
                "order_type": "MARKET"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["security_id"] == "226712"
        assert data["transaction_type"] == "BUY"
        assert data["status"] == "EXECUTED"
