# 🚀 Automatic Credential Loading & Deployment Guide

## Overview

The system now supports **automatic credential loading from environment variables** on startup. This eliminates the need for manual admin input and is perfect for VPS/cloud deployments.

---

## ✅ Implementation Complete

### What's Implemented:
- ✅ Auto-credential loading module (`app/storage/auto_credentials.py`)
- ✅ Environment variable support for both auth modes
- ✅ Automatic .env file detection
- ✅ CORS updated for port 5174
- ✅ Integrated into startup sequence
- ✅ No manual UI input required

---

## 🔧 Deployment Configuration

### Mode B (STATIC_IP) - Production Default

Set these environment variables:

```bash
DHAN_CLIENT_ID=your_dhan_client_id
DHAN_API_KEY=your_dhan_api_key
DHAN_API_SECRET=your_dhan_api_secret
```

### Mode A (DAILY_TOKEN) - Fallback/Development

Set these environment variables:

```bash
DHAN_CLIENT_ID=your_dhan_client_id
DHAN_ACCESS_TOKEN=your_dhan_access_token
```

### Other Required Variables:

```bash
API_HOST=0.0.0.0
API_PORT=8000
DATABASE_URL=sqlite:///./trading_terminal.db
VITE_API_URL=http://localhost:8000/api/v2
```

---

## 📋 Local Development Setup

1. **Create `.env` file** in project root:
   ```
   DHAN_CLIENT_ID=your_id
   DHAN_API_KEY=your_key
   DHAN_API_SECRET=your_secret
   API_HOST=0.0.0.0
   API_PORT=8000
   DATABASE_URL=sqlite:///./trading_terminal.db
   VITE_API_URL=http://localhost:8000/api/v2
   ```

2. **Start backend** - credentials auto-load:
   ```bash
   cd fastapi_backend
   python -m uvicorn app.main:app --reload --port 8000
   ```

3. **Start frontend** - connects to auto-loaded credentials:
   ```bash
   cd frontend
   npm run dev
   ```

---

## ☁️ VPS/Cloud Deployment

### Docker Environment Variables:

```dockerfile
ENV DHAN_CLIENT_ID=your_client_id
ENV DHAN_API_KEY=your_api_key
ENV DHAN_API_SECRET=your_api_secret
ENV API_HOST=0.0.0.0
ENV API_PORT=8000
ENV DATABASE_URL=sqlite:///./trading_terminal.db
```

### Kubernetes/Container Orchestration:

```yaml
env:
  - name: DHAN_CLIENT_ID
    valueFrom:
      secretKeyRef:
        name: dhan-credentials
        key: client_id
  - name: DHAN_API_KEY
    valueFrom:
      secretKeyRef:
        name: dhan-credentials
        key: api_key
  - name: DHAN_API_SECRET
    valueFrom:
      secretKeyRef:
        name: dhan-credentials
        key: api_secret
```

### GitHub Actions / CI-CD:

```yaml
env:
  DHAN_CLIENT_ID: ${{ secrets.DHAN_CLIENT_ID }}
  DHAN_API_KEY: ${{ secrets.DHAN_API_KEY }}
  DHAN_API_SECRET: ${{ secrets.DHAN_API_SECRET }}
```

---

## 🔄 Startup Flow

When backend starts:

```
1. Load .env file (if exists)
2. Initialize database
3. Auto-load credentials from environment
   ├─ Mode B (STATIC_IP) - if DHAN_CLIENT_ID + DHAN_API_KEY + DHAN_API_SECRET set
   └─ Mode A (DAILY_TOKEN) - if DHAN_CLIENT_ID + DHAN_ACCESS_TOKEN set
4. Save credentials to database
5. Load instrument registry
6. Start WebSocket feed (triggers automatically)
7. System ready
```

---

## ✨ Key Features

- **Automatic**: No manual admin input needed
- **Flexible**: Supports both Mode A and Mode B
- **Secure**: Credentials passed via environment (not in code)
- **Production-Ready**: Perfect for Docker, K8s, VPS
- **Fallback**: Falls back gracefully if no credentials found
- **Multi-Source**: Checks .env, environment variables, OS environment

---

## 🐛 Troubleshooting

### Credentials Not Loading

Check logs during startup:
```
[STARTUP] Loaded .env from: /path/to/.env
[STARTUP] Found Mode B (STATIC_IP) credentials in environment
[STARTUP] ✓ Mode B (STATIC_IP) credentials auto-loaded
```

If not found:
```
[STARTUP] ⚠ No DhanHQ credentials found in environment variables
[STARTUP]   Set environment variables:
[STARTUP]   - Mode B: DHAN_CLIENT_ID, DHAN_API_KEY, DHAN_API_SECRET
[STARTUP]   - Mode A: DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN
```

### WebSocket Not Connecting

Check:
1. Credentials are valid
2. Network connectivity to `wss://api-feed.dhan.co`
3. Backend logs for connection errors
4. Firewall rules for WebSocket port 443

---

## 📝 Files Modified

- ✅ `app/main.py` - Added auto-credential loading to startup
- ✅ `app/storage/auto_credentials.py` - New auto-load module
- ✅ `.env` - Configuration file
- ✅ `.env.example` - Template for reference

---

**Version**: 1.0  
**Date**: February 3, 2026  
**Status**: Production Ready ✅
