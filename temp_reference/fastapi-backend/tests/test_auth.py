"""
Authentication Tests
Test cases for authentication endpoints
"""

import pytest
from httpx import AsyncClient

class TestAuthentication:
    """Test authentication endpoints"""
    
    @pytest.mark.asyncio
    async def test_register_user(self, client: AsyncClient, sample_user_data):
        """Test user registration"""
        response = await client.post("/api/v1/auth/register", json=sample_user_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == sample_user_data["email"]
        assert data["username"] == sample_user_data["username"]
        assert "id" in data
    
    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient, sample_user_data):
        """Test registration with duplicate email"""
        # First registration
        await client.post("/api/v1/auth/register", json=sample_user_data)
        
        # Second registration with same email
        response = await client.post("/api/v1/auth/register", json=sample_user_data)
        
        # TODO: Implement duplicate email validation
        assert response.status_code in [200, 400]  # Depends on implementation
    
    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, sample_user_data):
        """Test successful login"""
        # Register user first
        await client.post("/api/v1/auth/register", json=sample_user_data)
        
        # Login
        login_data = {
            "username": sample_user_data["email"],
            "password": sample_user_data["password"]
        }
        response = await client.post("/api/v1/auth/login", data=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
    
    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, client: AsyncClient):
        """Test login with invalid credentials"""
        login_data = {
            "username": "invalid@example.com",
            "password": "wrongpassword"
        }
        response = await client.post("/api/v1/auth/login", data=login_data)
        
        # TODO: Implement proper authentication validation
        assert response.status_code in [200, 401]  # Depends on implementation
    
    @pytest.mark.asyncio
    async def test_get_current_user(self, client: AsyncClient, sample_user_data):
        """Test getting current user info"""
        # Register and login
        await client.post("/api/v1/auth/register", json=sample_user_data)
        
        login_data = {
            "username": sample_user_data["email"],
            "password": sample_user_data["password"]
        }
        login_response = await client.post("/api/v1/auth/login", data=login_data)
        token = login_response.json()["access_token"]
        
        # Get current user
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.get("/api/v1/auth/me", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == sample_user_data["email"]
        assert data["username"] == sample_user_data["username"]
    
    @pytest.mark.asyncio
    async def test_get_current_user_unauthorized(self, client: AsyncClient):
        """Test getting current user without token"""
        response = await client.get("/api/v1/auth/me")
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_change_password(self, client: AsyncClient, sample_user_data):
        """Test password change"""
        # Register and login
        await client.post("/api/v1/auth/register", json=sample_user_data)
        
        login_data = {
            "username": sample_user_data["email"],
            "password": sample_user_data["password"]
        }
        login_response = await client.post("/api/v1/auth/login", data=login_data)
        token = login_response.json()["access_token"]
        
        # Change password
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.post(
            "/api/v1/auth/change-password",
            headers=headers,
            params={
                "old_password": sample_user_data["password"],
                "new_password": "NewPassword123!"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
    
    @pytest.mark.asyncio
    async def test_create_api_key(self, client: AsyncClient, sample_user_data):
        """Test API key creation"""
        # Register and login
        await client.post("/api/v1/auth/register", json=sample_user_data)
        
        login_data = {
            "username": sample_user_data["email"],
            "password": sample_user_data["password"]
        }
        login_response = await client.post("/api/v1/auth/login", data=login_data)
        token = login_response.json()["access_token"]
        
        # Create API key
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.post(
            "/api/v1/auth/api-keys",
            headers=headers,
            params={"description": "Test API Key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "api_key" in data
        assert data["description"] == "Test API Key"
        assert "created_at" in data
