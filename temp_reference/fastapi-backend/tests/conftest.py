"""
Test Configuration
Configuration for pytest and test suite
"""

import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import get_db, Base
from app.config import settings

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Create test session factory
TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="function")
async def db_session():
    """Create a fresh database session for each test."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with TestSessionLocal() as session:
        yield session
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture(scope="function")
async def client(db_session):
    """Create a test client with database dependency override."""
    def override_get_db():
        return db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()

@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "email": "test@example.com",
        "username": "testuser",
        "password": "TestPassword123!",
        "full_name": "Test User"
    }

@pytest.fixture
def sample_order_data():
    """Sample order data for testing."""
    return {
        "security_id": "226712",
        "quantity": 100,
        "price": 815.50,
        "order_type": "LIMIT",
        "transaction_type": "BUY",
        "product_type": "INTRADAY"
    }

@pytest.fixture
def auth_headers():
    """Sample authorization headers."""
    return {
        "Authorization": "Bearer test_token"
    }

@pytest.fixture
def mock_market_data():
    """Mock market data for testing."""
    return {
        "security_id": "226712",
        "last_price": 815.50,
        "bid_price": 815.00,
        "ask_price": 816.00,
        "volume": 50000,
        "timestamp": "2024-01-01T10:00:00Z"
    }

# Test configuration
pytest_plugins = []

# Disable logging during tests
import logging
logging.disable(logging.CRITICAL)
