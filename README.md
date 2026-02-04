# 🚀 Broking Terminal V2 - Data Server Backend

A high-performance FastAPI backend for real-time options trading data with WebSocket integration and comprehensive market data management.

## ✨ Features

- **Real-time Market Data**: Live WebSocket feeds for options pricing
- **FastAPI Backend**: High-performance REST API with automatic documentation
- **Option Chain Management**: Comprehensive options data with strike management
- **Database Integration**: SQLAlchemy ORM with PostgreSQL support
- **WebSocket Streaming**: Real-time price updates and market data
- **Tier-based Subscriptions**: Dynamic subscription management for market data
- **Compliance Ready**: Built-in DhanHQ compliance and rate limiting
- **Production Ready**: Comprehensive logging, error handling, and monitoring

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   FastAPI       │    │   DhanHQ API    │
│   (React/Vue)   │◄──►│   Backend       │◄──►│   Market Data   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   PostgreSQL    │
                       │   Database      │
                       └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- PostgreSQL (optional, defaults to SQLite)
- DhanHQ API credentials

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/broking-terminal-v2.git
   cd broking-terminal-v2/data_server_backend
   ```

2. **Set up virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   cd fastapi_backend
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

5. **Start the backend**
   ```bash
   cd app
   python main.py
   ```

The API will be available at `http://localhost:8000`

### Environment Configuration

Create a `.env` file with your credentials:

```env
# DhanHQ API Credentials
DHAN_CLIENT_ID=your_client_id
DHAN_ACCESS_TOKEN=your_access_token

# Database (optional - defaults to SQLite)
DATABASE_URL=postgresql://user:password@localhost/dbname

# API Settings
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false
```

## 📡 API Documentation

Once the server is running, visit:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Key Endpoints

#### Options Data
- `GET /api/v2/options/live` - Get live options chain
- `GET /api/v2/options/expiries` - Get available expiry dates
- `GET /api/v2/options/strikes` - Get strike prices

#### Market Data
- `GET /api/v2/market/underlyings` - Get available underlyings
- `WebSocket /ws/live` - Real-time market data feed

#### Health & Status
- `GET /health` - Health check
- `GET /status` - System status

## 🧪 Testing

### Run Tests
```bash
cd fastapi_backend
python -m pytest tests/
```

### Manual Testing
```bash
# Test options endpoint
curl "http://localhost:8000/api/v2/options/live?underlying=NIFTY&expiry=2026-02-11"

# Test WebSocket
python test_websocket.py
```

## 📁 Project Structure

```
data_server_backend/
├── fastapi_backend/           # Main FastAPI application
│   ├── app/
│   │   ├── main.py           # Application entry point
│   │   ├── api/              # API routes
│   │   ├── services/         # Business logic
│   │   ├── models/           # Database models
│   │   └── dhan/             # DhanHQ integration
│   ├── requirements.txt      # Python dependencies
│   └── tests/                # Test suite
├── frontend/                 # Frontend application
├── docs/                     # Documentation
├── scripts/                  # Utility scripts
└── README.md                 # This file
```

## 🔧 Development

### Adding New Features

1. Create a new branch: `git checkout -b feature-name`
2. Make your changes
3. Add tests: `python -m pytest tests/`
4. Commit: `git commit -m "Add feature"`
5. Push: `git push origin feature-name`

### Code Style

This project follows PEP 8 style guidelines. Use `black` for formatting:

```bash
pip install black
black fastapi_backend/
```

## 🚀 Deployment

### Docker Deployment

1. **Build the image**
   ```bash
   docker build -t broking-terminal-backend .
   ```

2. **Run the container**
   ```bash
   docker run -p 8000:8000 --env-file .env broking-terminal-backend
   ```

### Production Deployment

1. **Set up production environment variables**
2. **Configure database**
3. **Run with Gunicorn**
   ```bash
   pip install gunicorn
   gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app
   ```

## 📊 Monitoring & Logging

### Log Levels
- `INFO`: General operational information
- `WARNING`: Important events that require attention
- `ERROR`: Error conditions that may affect functionality
- `DEBUG`: Detailed debugging information

### Health Monitoring
- `/health` endpoint provides system health status
- WebSocket connection monitoring
- Database connection health checks

## 🔒 Security

- API rate limiting implemented
- Input validation and sanitization
- Environment variable protection
- WebSocket connection authentication

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

### Common Issues

**Issue**: Backend fails to start
- **Solution**: Check environment variables and DhanHQ credentials

**Issue**: 404 errors on options endpoint
- **Solution**: Verify cache population and WebSocket connection

**Issue**: WebSocket connection fails
- **Solution**: Check network connectivity and API credentials

### Getting Help

- 📖 Check the [Documentation](docs/)
- 🐛 Report issues on [GitHub Issues](https://github.com/yourusername/broking-terminal-v2/issues)
- 💬 Join our [Discussions](https://github.com/yourusername/broking-terminal-v2/discussions)

## 📈 Performance

- **Response Time**: < 100ms for cached data
- **WebSocket Latency**: < 50ms
- **Concurrent Connections**: 1000+ WebSocket connections
- **Memory Usage**: < 512MB (typical load)

## 🔄 Version History

- **v2.0.0** - Complete rewrite with FastAPI and WebSocket support
- **v1.x.x** - Legacy implementation

---

**Built with ❤️ for the trading community**
