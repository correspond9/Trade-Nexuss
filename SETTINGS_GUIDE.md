# Settings Persistence Guide

## Overview
The settings persistence system saves your working configuration so you don't have to reconfigure everything daily. **Only the daily token needs to be refreshed every 24 hours.**

## First-Time Setup (5 minutes)

1. **Enter your credentials:**
   ```bash
   POST /api/v2/credentials/save
   {
     "client_id": "YOUR_CLIENT_ID",
     "access_token": "YOUR_24H_TOKEN",
     "auth_mode": "DAILY_TOKEN"
   }
   ```

2. **Verify the backend connects and live feed starts**
   - Watch the logs for `[OK] Connection successful`
   - Check that WebSocket feed is running

3. **Lock the settings (one-time):**
   ```bash
   POST /api/v2/settings/lock
   ```

4. **Done!** Your configuration is now saved.

## Daily Workflow (30 seconds)

Every day, simply:

1. **Get a fresh daily token from DhanHQ**

2. **Enter only the new token:**
   ```bash
   POST /api/v2/credentials/save
   {
     "client_id": "YOUR_CLIENT_ID",
     "access_token": "YOUR_NEW_24H_TOKEN",
     "auth_mode": "DAILY_TOKEN"
   }
   ```

3. **That's it!** Backend will:
   - Auto-restore your previous client_id and auth_mode
   - Connect to live feed automatically
   - Start processing market data

## Settings Management API

### Check Status
```bash
GET /api/v2/settings/status
```
Returns whether settings are locked and saved.

### Lock Settings
```bash
POST /api/v2/settings/lock
```
Enable auto-restoration on every startup (except daily token).

### Unlock Settings
```bash
POST /api/v2/settings/unlock
```
Disable auto-restoration.

### Manually Save
```bash
POST /api/v2/settings/save
```
Save current working configuration.

### Manually Restore
```bash
POST /api/v2/settings/restore
```
Restore saved settings from disk.

### Clear All Settings
```bash
POST /api/v2/settings/clear
```
⚠️ **WARNING:** Delete all saved settings. Cannot be undone.

## What Gets Saved

✅ **Saved (persisted):**
- Client ID
- Auth mode (DAILY_TOKEN or STATIC_IP)
- API key (if using STATIC_IP mode)
- API secret (if using STATIC_IP mode)
- Configuration state

❌ **NOT saved (for security):**
- Daily token (temporary, 24-hour validity)
- Auth token (temporary)

## File Locations

- **Settings file:** `fastapi_backend/config/settings.json`
- **Backup file:** `fastapi_backend/config/settings.backup.json`
- **Lock file:** `fastapi_backend/config/.settings_locked`

## Troubleshooting

### Settings not restoring on startup?
- Check if settings are locked: `GET /api/v2/settings/status`
- If not locked, run: `POST /api/v2/settings/lock`

### Want to remove saved settings?
- Run: `POST /api/v2/settings/clear`
- Then manually enter credentials again

### Backup corrupted?
- Delete `fastapi_backend/config/settings.backup.json`
- It will be recreated on next save

## Example cURL Commands

```bash
# Lock settings (one time setup)
curl -X POST http://localhost:8000/api/v2/settings/lock

# Check if locked
curl http://localhost:8000/api/v2/settings/status

# Daily token refresh
curl -X POST http://localhost:8000/api/v2/credentials/save \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "11003537",
    "access_token": "YOUR_NEW_24H_TOKEN",
    "auth_mode": "DAILY_TOKEN"
  }'

# View help
curl http://localhost:8000/api/v2/settings/instructions
```

## Benefits

✅ **Time Saved:** 2-3 hours per day  
✅ **Reliability:** Consistent startup behavior  
✅ **Security:** Tokens not saved to disk  
✅ **Flexibility:** Can unlock and reconfigure anytime  
✅ **Backup:** Previous settings always backed up  
