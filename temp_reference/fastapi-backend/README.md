# FastAPI Backend for Trading Terminal

## Overview
This is the complete FastAPI backend for the Trading Terminal application, providing REST APIs and WebSocket support for real-time trading operations.

## Features
- **Authentication**: JWT-based authentication with role-based access control
- **Trading APIs**: Complete order management, position tracking, portfolio management
- **Market Data**: Real-time market data with WebSocket streaming
- **Admin Panel**: User management, system monitoring, configuration
- **Dhan Integration**: Full integration with DhanHQ trading platform
- **Rate Limiting**: Built-in rate limiting and security middleware
- **Async Support**: Full async/await support for high performance

## Quick Start

### Prerequisites
- Python 3.8+
- SQLite database

### Installation
```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run the application
python main.py
```

### Access Points
- **API Documentation**: http://localhost:5000/docs
- **ReDoc Documentation**: http://localhost:5000/redoc
- **Health Check**: http://localhost:5000/api/v1/health
- **Root Endpoint**: http://localhost:5000/

## Project Structure
```
fastapi-backend/
├── app/
│   ├── models/          # Database models
│   ├── routers/         # API endpoints
│   ├── services/        # Business logic
│   ├── middleware/      # Custom middleware
│   ├── utils/           # Utilities
│   ├── config.py        # Configuration
│   ├── database.py      # Database setup
│   └── dependencies.py  # Dependencies
├── tests/               # Test suite
├── requirements.txt     # Dependencies
├── .env                # Environment variables
└── main.py             # Application entry point
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/register` - User registration
- `GET /api/v1/auth/me` - Get current user

### Trading
- `POST /api/v1/trading/orders` - Place order
- `GET /api/v1/trading/orders` - Get orders
- `DELETE /api/v1/trading/orders/{id}` - Cancel order

### Market Data
- `GET /api/v1/market/instruments/{exchange}` - Get instruments
- `GET /api/v1/market/quote/{security_id}` - Get quote
- `WebSocket /api/v1/ws/market-data` - Real-time market data

### Portfolio
- `GET /api/v1/portfolio/positions` - Get positions
- `GET /api/v1/portfolio/holdings` - Get holdings
- `GET /api/v1/portfolio/balance` - Get balance

### Admin
- `GET /api/v1/admin/users` - User management
- `GET /api/v1/admin/stats` - System statistics

## Configuration

### Environment Variables
- `SECRET_KEY`: JWT secret key
- `DATABASE_URL`: Database connection string
- `DEBUG`: Enable debug mode
- `CORS_ORIGINS`: Allowed CORS origins

### Database
The application uses SQLite with async support. The database file is located at `./databases/trading_terminal.db`.

## Development

### Running Tests
```bash
pytest
```

### Code Style
Follow PEP 8 guidelines. Use Black for code formatting.

## Deployment

### Docker
```bash
docker build -t trading-terminal-api .
docker run -p 5000:5000 trading-terminal-api
```

### Production
- Use a production-grade database (PostgreSQL recommended)
- Set up proper SSL certificates
- Configure reverse proxy (nginx recommended)
- Set up monitoring and logging

## Security

- JWT-based authentication
- Rate limiting
- CORS protection
- Input validation with Pydantic
- SQL injection prevention with SQLAlchemy

## Support

For issues and questions, please refer to the project documentation or create an issue in the project repository.
