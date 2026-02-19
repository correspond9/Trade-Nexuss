# 🚀 VPS Deployment Guide - Broking Terminal V2

## ✅ Simple Change Workflow (GitHub + Coolify)

This arrangement works well:
1. Share change requests in plain language.
2. Implement and review code changes on GitHub.
3. Redeploy manually from your Hostinger Coolify panel.

## Quick Setup (5 minutes)

### Prerequisites
- Ubuntu 20.04+ or CentOS 8+ VPS
- Docker & Docker Compose installed
- Domain name (optional but recommended)

### Step 1: Install Docker
```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### Step 2: Clone Repository
```bash
git clone <your-repo-url>
cd Broking_Terminal_V2/data_server_backend
```

### Step 3: Configure Environment
```bash
# Copy production template
cp .env.production .env

# Edit with your actual values
nano .env
```

**Required changes in `.env`:**
- `POSTGRES_PASSWORD` - Set secure database password
- `DHAN_CLIENT_ID`, `DHAN_API_KEY`, `DHAN_API_SECRET` - Your DhanHQ credentials
- `SECRET_KEY` - Generate secure secret: `openssl rand -hex 32`
- `VITE_API_URL` - Set to your domain: `https://your-domain.com/api`

### Step 4: Setup SSL (Optional but Recommended)
```bash
# Create SSL directory
mkdir -p ssl

# Option A: Use Let's Encrypt (if you have a domain)
sudo apt install certbot
sudo certbot certonly --standalone -d your-domain.com
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ssl/cert.pem
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem ssl/key.pem

# Option B: Generate self-signed certificate (for testing)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/key.pem \
  -out ssl/cert.pem
```

### Step 5: Deploy
```bash
# Make deploy script executable
chmod +x scripts/deploy.sh

# Run deployment
./scripts/deploy.sh
```

### Step 6: Verify Deployment
```bash
# Check containers
docker-compose -f docker-compose.prod.yml ps

# Check logs
docker-compose -f docker-compose.prod.yml logs -f backend

# Test health endpoint
curl -k https://localhost/health
```

## Advanced Configuration

### Domain Setup
1. Point your domain A record to your VPS IP
2. Update `VITE_API_URL` in `.env` to use your domain
3. Restart containers: `docker-compose -f docker-compose.prod.yml restart`

### Firewall Setup
```bash
# Ubuntu UFW
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable

# CentOS/RHEL
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### Monitoring
```bash
# View real-time logs
docker-compose -f docker-compose.prod.yml logs -f

# Check resource usage
docker stats

# Backup database
docker-compose -f docker-compose.prod.yml exec db pg_dump -U postgres trading_terminal > backup_$(date +%Y%m%d).sql
```

## Troubleshooting

### Common Issues

**Container won't start:**
```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs backend

# Rebuild containers
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d
```

**Database connection errors:**
- Verify `POSTGRES_PASSWORD` matches in both `.env` and docker-compose
- Check if database container is running: `docker-compose -f docker-compose.prod.yml ps db`

**WebSocket not connecting:**
- Check DhanHQ credentials are valid
- Verify firewall allows outbound connections to `wss://api-feed.dhan.co`
- Check backend logs for WebSocket errors

**SSL certificate issues:**
- Verify certificate files exist in `ssl/` directory
- Check file permissions: `chmod 600 ssl/*`
- Test with curl: `curl -v https://your-domain.com`

### Performance Tuning

**Increase resources:**
Edit `docker-compose.prod.yml` and adjust:
```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 1G
```

**Enable caching:**
```bash
# Add Redis caching (already included)
# Configure in backend via environment variables
CACHE_TTL=300
CACHE_MAX_SIZE=10000
```

## Security Checklist

- [ ] Change default passwords
- [ ] Use SSL certificates
- [ ] Set up firewall
- [ ] Regular backups
- [ ] Monitor logs
- [ ] Keep Docker updated
- [ ] Use environment variables for secrets

## Maintenance

**Weekly tasks:**
```bash
# Update containers
git pull
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d

# Backup database
./scripts/backup.sh

# Clean up old images
docker image prune -f
```

**Monthly tasks:**
```bash
# Update system
sudo apt update && sudo apt upgrade

# Check logs size
du -sh logs/

# Rotate logs if needed
docker-compose -f docker-compose.prod.yml restart
```

## Support

If you encounter issues:
1. Check logs: `docker-compose -f docker-compose.prod.yml logs`
2. Verify environment variables in `.env`
3. Ensure all ports are open
4. Check DhanHQ API status

## URLs After Deployment

- API: `https://your-domain.com/api`
- Documentation: `https://your-domain.com/docs`
- Health Check: `https://your-domain.com/health`
- WebSocket: `wss://your-domain.com/ws`
