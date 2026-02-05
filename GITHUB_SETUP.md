# 🚀 GitHub Repository Setup Guide

This guide will help you set up your GitHub repository and deploy the Trade-Nexuss Backend.

## 📋 Prerequisites

- Git installed and configured
- GitHub account
- Docker installed (for deployment)
- DhanHQ API credentials

## 🔧 Step 1: Create GitHub Repository

1. **Go to GitHub**: https://github.com
2. **Create New Repository**:
   - Click "+" → "New repository"
   - Repository name: `Trade-Nexuss`
   - Description: `High-performance FastAPI backend for real-time options trading data`
   - Visibility: Choose Public or Private
   - Don't initialize with README (we already have one)
   - Don't add .gitignore (we already have one)
   - Don't add license (we'll add one later)

## 🔧 Step 2: Connect Local Repository

```bash
# Add remote repository (replace YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/Trade-Nexuss.git

# Push to GitHub
git push -u origin main
```

## 🔧 Step 3: Configure GitHub Repository

### Add Repository Description
Go to repository settings → About and add:
```
🚀 High-performance FastAPI backend for real-time options trading data with WebSocket integration and comprehensive market data management.
```

### Add Topics
Add these topics to your repository:
- `fastapi`
- `trading`
- `options`
- `websocket`
- `market-data`
- `python`
- `docker`
- `financial-api`

### Enable Features
In repository settings:
- ✅ Enable Issues
- ✅ Enable Projects
- ✅ Enable Wiki
- ✅ Enable Discussions
- ✅ Enable Actions (for CI/CD)

## 🔧 Step 4: Set up GitHub Actions

Create `.github/workflows/ci.yml`:

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        cd fastapi_backend
        pip install -r requirements.txt
    
    - name: Run tests
      run: |
        cd fastapi_backend
        python -m pytest tests/ -v
    
    - name: Run linting
      run: |
        cd fastapi_backend
        pip install flake8
        flake8 app/ --count --select=E9,F63,F7,F82 --show-source --statistics

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Build Docker image
      run: docker build -t broking-terminal-backend .
    
    - name: Run security scan
      run: |
        docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
          -v $PWD:/tmp/.cache/ aquasec/trivy:latest image \
          --exit-code 0 --no-progress --format table \
          broking-terminal-backend
```

## 🔧 Step 5: Deploy to Production

### Option 1: Docker Compose (Recommended)

```bash
# Copy environment template
cp .env.example .env.production

# Edit .env.production with your production credentials
nano .env.production

# Run deployment script
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

### Option 2: Manual Docker

```bash
# Build image
docker build -t broking-terminal-backend .

# Run container
docker run -d \
  --name broking-terminal \
  -p 8000:8000 \
  --env-file .env.production \
  --restart unless-stopped \
  broking-terminal-backend
```

### Option 3: Cloud Deployment

#### AWS ECS
1. Create ECR repository
2. Push Docker image
3. Create ECS task definition
4. Deploy ECS service

#### Google Cloud Run
```bash
# Build and tag
gcloud builds submit --tag gcr.io/PROJECT-ID/broking-terminal

# Deploy
gcloud run deploy broking-terminal \
  --image gcr.io/PROJECT-ID/broking-terminal \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

#### Azure Container Instances
```bash
# Create resource group
az group create --name broking-terminal-rg --location eastus

# Deploy container
az container create \
  --resource-group broking-terminal-rg \
  --name broking-terminal \
  --image broking-terminal-backend:latest \
  --dns-name-label broking-terminal-unique \
  --ports 8000
```

## 🔧 Step 6: Configure DNS and SSL

### Using Nginx (included in docker-compose)
1. Get SSL certificates (Let's Encrypt recommended)
2. Place certificates in `ssl/` directory
3. Update `nginx.prod.conf` with your domain

### Cloudflare (Easy Setup)
1. Sign up for Cloudflare
2. Add your domain
3. Point DNS to your server IP
4. Enable SSL/TLS
5. Set up Page Rules for API endpoints

## 🔧 Step 7: Monitoring and Logging

### Health Checks
- `GET /health` - Basic health check
- `GET /status` - Detailed system status

### Log Monitoring
```bash
# View logs
docker-compose logs -f backend

# View specific service logs
docker-compose logs -f db
docker-compose logs -f nginx
```

### Metrics (if enabled)
- Prometheus metrics on port 9090
- Grafana dashboard setup available

## 🔧 Step 8: Security Configuration

### Environment Variables
- Never commit `.env` files
- Use GitHub Secrets for sensitive data
- Rotate API keys regularly

### Firewall Rules
```bash
# Allow only necessary ports
ufw allow 22    # SSH
ufw allow 80    # HTTP
ufw allow 443   # HTTPS
ufw enable
```

### Rate Limiting
- Built-in rate limiting configured
- Adjust limits in environment variables

## 🔧 Step 9: Backup and Recovery

### Database Backups
```bash
# Create backup
docker-compose exec db pg_dump -U postgres trading_terminal > backup.sql

# Restore backup
docker-compose exec -T db psql -U postgres trading_terminal < backup.sql
```

### Automated Backups
Add to crontab:
```bash
0 2 * * * /path/to/backup-script.sh
```

## 🔧 Step 10: Performance Optimization

### Database Optimization
- Add indexes for frequently queried columns
- Configure connection pooling
- Monitor slow queries

### Caching
- Redis configured for session storage
- Consider CDN for static assets

### Load Balancing
- Use multiple backend instances
- Configure load balancer health checks

## 🎯 Production Checklist

- [ ] GitHub repository created and pushed
- [ ] Environment variables configured
- [ ] Docker containers running
- [ ] SSL certificates installed
- [ ] DNS configured
- [ ] Health checks passing
- [ ] Monitoring enabled
- [ ] Backup strategy implemented
- [ ] Security hardening completed
- [ ] Performance testing completed

## 🆘 Troubleshooting

### Common Issues

**Container won't start**
```bash
# Check logs
docker-compose logs backend

# Check environment
docker-compose config
```

**Database connection failed**
```bash
# Check database status
docker-compose exec db pg_isready

# Test connection
docker-compose exec backend python -c "from app.database import engine; print(engine.execute('SELECT 1').scalar())"
```

**WebSocket not working**
```bash
# Check WebSocket endpoint
curl -i -N -H "Connection: Upgrade" \
     -H "Upgrade: websocket" \
     -H "Sec-WebSocket-Key: test" \
     -H "Sec-WebSocket-Version: 13" \
     http://localhost:8000/ws/live
```

## 📞 Support

- 📖 Check the main [README.md](README.md)
- 🐛 Report issues on GitHub Issues
- 💬 Join GitHub Discussions
- 📧 Email support for enterprise customers

---

**🎉 Congratulations! Your Trade-Nexuss Backend is now deployed!**
