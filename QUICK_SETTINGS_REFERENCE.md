# ⚡ Settings Locking - Quick Reference Card

## Daily 30-Second Startup

```bash
# 1. Get new 24h token from DhanHQ portal

# 2. One API call (that's it!):
curl -X POST http://localhost:8000/api/v2/credentials/save \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "11003537",
    "access_token": "YOUR_NEW_TOKEN_HERE",
    "auth_mode": "DAILY_TOKEN"
  }'

# Backend auto-restores everything and connects
```

## One-Time Setup (First Time)

```bash
# 1. Start backend with your first 24h token
# 2. Wait for live feed to connect successfully
# 3. Lock settings (one-time):

curl -X POST http://localhost:8000/api/v2/settings/lock

# Done! Now only step #2 above is needed every day
```

## Settings API Endpoints

```bash
# Check if locked
curl http://localhost:8000/api/v2/settings/status

# Lock current settings
curl -X POST http://localhost:8000/api/v2/settings/lock

# Unlock (if needed)
curl -X POST http://localhost:8000/api/v2/settings/unlock

# Manually save
curl -X POST http://localhost:8000/api/v2/settings/save

# Manually restore
curl -X POST http://localhost:8000/api/v2/settings/restore

# Delete all (⚠️ permanent)
curl -X POST http://localhost:8000/api/v2/settings/clear

# Get help
curl http://localhost:8000/api/v2/settings/instructions
```

## What Happens Automatically

When you enter new token via `/credentials/save`:

✅ Backend restores your client_id from saved settings
✅ Backend restores your auth_mode from saved settings  
✅ Backend restores your API keys from saved settings
✅ Backend updates with new daily token
✅ WebSocket feed connects automatically
✅ Live market data starts flowing
✅ All subscriptions restored

## Saved vs Not Saved

| Item | Saved? | Reason |
|------|--------|--------|
| Client ID | ✅ | Never changes |
| Auth mode | ✅ | Rarely changes |
| API keys | ✅ | Same for STATIC_IP mode |
| Daily token | ❌ | Expires in 24h |
| Auth token | ❌ | Temporary |

## Time Saved Per Day

**Before:** 2-3 hours of manual configuration  
**After:** 30 seconds (just entering new token)

**Saved:** 1.5-3 hours per day × 365 days = **550-1095 hours per year!**

## Files

- Settings: `fastapi_backend/config/settings.json`
- Backup: `fastapi_backend/config/settings.backup.json`
- Lock: `fastapi_backend/config/.settings_locked`

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Settings not restoring | Run `POST /api/v2/settings/lock` to enable |
| Want to change config | Run `POST /api/v2/settings/unlock`, reconfigure, lock again |
| Settings corrupted | Delete backup file, settings will be recreated |
| Clear everything | Run `POST /api/v2/settings/clear` |

---

**That's it! No more spending hours on daily configuration.** ⚡

See [SETTINGS_LOCKING_README.md](./SETTINGS_LOCKING_README.md) for full details.
