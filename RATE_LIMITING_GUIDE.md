# DhanHQ Connection Rate Limiting & IP Ban Protection

## Overview

To prevent IP banning from DhanHQ's API, the WebSocket connection logic now includes comprehensive rate limiting and exponential backoff mechanisms.

## Protection Mechanisms

### 1. **Exponential Backoff**
Retry delays increase exponentially after each failed connection attempt:

```
Attempt 1: 5 seconds
Attempt 2: 10 seconds
Attempt 3: 20 seconds
Attempt 4: 40 seconds
Attempt 5: 80 seconds
Attempt 6+: 120 seconds (capped)
```

**Purpose:** Reduces load on DhanHQ servers and signals to API that we're respecting rate limits.

### 2. **Connection Attempt Counter**
Tracks consecutive failures:

```
Max consecutive failures before cooldown: 10 attempts
```

Once 10 consecutive failures occur, the system enters a **cooldown period**.

### 3. **IP Protection Cooldown**
After max failures reached:

```
Cooldown duration: 1 hour (3,600 seconds)
Status during cooldown: All connection attempts blocked
After cooldown: Counter resets and backoff restarts at 5 seconds
```

**Purpose:** If DhanHQ's rate limiter detects abuse, a 1-hour cooldown prevents IP ban by stopping all reconnection attempts.

## Implementation Details

### Rate Limiting Variables
```python
_connection_attempts = 0          # Total attempts made
_last_connection_attempt = None   # Timestamp of last attempt
_backoff_delay = 5               # Current backoff delay
_max_backoff_delay = 120         # Maximum backoff (2 minutes)
_consecutive_failures = 0        # Current failure count
_max_consecutive_failures = 10   # Threshold for cooldown
_cooldown_period = 3600          # 1 hour in seconds
_last_cooldown_start = None      # When cooldown started
```

### Key Functions

#### `_should_attempt_connection()`
Before any connection attempt, this function checks:
1. Are we in a cooldown period? → If yes, wait and return False
2. Have we exceeded max failures? → If yes, start cooldown
3. Has enough backoff time passed? → If no, wait and return False
4. Otherwise, return True and proceed with connection

#### `_record_connection_attempt(success=False)`
After each connection attempt:
- If **success**: Reset consecutive failures to 0, reset backoff to 5s
- If **failure**: Increment failure counter, double backoff delay (capped at 120s)

### Flow Diagram

```
Start Backend
    ↓
[Loop] Check _should_attempt_connection()
    ↓ (Yes)
Attempt to connect to DhanHQ
    ├─ Success → _record_connection_attempt(success=True)
    │              ├─ Reset failures to 0
    │              ├─ Reset backoff to 5s
    │              └─ Continue with data stream
    │
    └─ Failure → _record_connection_attempt(success=False)
                    ├─ Increment failures
                    ├─ Double backoff delay
                    ├─ Check if >= 10 failures?
                    │   ├─ Yes → Start 1-hour cooldown
                    │   └─ No → Try again after backoff
                    └─ Sleep before next check

[During cooldown]
Check _should_attempt_connection() returns False
    ↓
Print "IP protection active. Resuming in XXXs..."
    ↓
Sleep and check again in 5 seconds
    ↓
After 1 hour, cooldown expires and retries resume
```

## Monitoring & Logging

### Startup Messages
```
[OK] Dhan feed thread started (Phase 4 Dynamic Subscriptions)
[INFO] Rate limiting active to prevent IP banning:
       • Exponential backoff: 5s → 10s → 20s → 40s (max 120s)
       • Max connection attempts: 10 before 1-hour cooldown
       • This protects against DhanHQ rate limiting and IP bans
```

### During Operation

**Successful Connection:**
```
[WAIT] Connection backoff active. Retrying in 85s...
[OK] Connection successful! (attempt #3)
[OK] Starting Dhan WebSocket feed (Phase 4 Dynamic)
```

**Failed Connection:**
```
[RETRY] Connection failed. Attempt #5, failures: 3/10, next retry in 20s
[WARN] WebSocket connection lost, will reconnect with backoff...
```

**Entering Cooldown:**
```
[BLOCK] Max connection failures reached (10). Starting IP protection cooldown...
[COOLDOWN] IP protection active. Resuming in 3588s...
```

**Exiting Cooldown:**
```
[COOLDOWN] Cooldown period expired, resuming connection attempts...
[RETRY] Connection failed. Attempt #47, failures: 1/10, next retry in 5s
```

## Configuration

To adjust rate limiting behavior, modify these constants in `fastapi_backend/app/dhan/live_feed.py`:

```python
_backoff_delay = 5                    # Initial backoff (seconds)
_max_backoff_delay = 120              # Max backoff (seconds)
_max_consecutive_failures = 10        # Failures before cooldown
_cooldown_period = 3600               # Cooldown duration (seconds)
```

### Recommendation
⚠️ **Do NOT modify these values without understanding the consequences:**
- Decreasing backoff delays increases risk of IP banning
- Decreasing max consecutive failures reduces reconnection capability
- Decreasing cooldown period defeats the purpose of IP protection

## When IP Banning Occurs

### Signs of Rate Limiting
- Frequent "connection refused" errors
- "429 Too Many Requests" responses (if visible)
- HTTP 403 "Forbidden" errors
- Sudden disconnection after working normally

### Recovery from Potential Ban
1. System automatically enters 1-hour cooldown
2. During cooldown, all reconnection attempts are blocked
3. After 1 hour, retry counter resets and normal backoff resumes
4. If connection succeeds, normal operation continues

### If Stuck in Cooldown
**DO NOT:**
- Manually restart the backend server repeatedly
- Try to force reconnection attempts
- Bypass rate limiting logic

**DO:**
- Wait for the 1-hour cooldown to expire naturally
- Check DhanHQ server status (possible maintenance)
- Verify credentials are still valid
- Review logs for actual error messages

## Best Practices

1. **Never disable rate limiting** - Even for testing
2. **Respect API limits** - They exist for good reason
3. **Monitor logs** - Watch for patterns of failures
4. **Plan deployments** - Don't restart servers frequently
5. **Test credentials** - Verify auth before deployment
6. **Allow full cooldowns** - Don't circumvent the 1-hour protection

## Testing Rate Limiting

To verify rate limiting is working:

1. Start the backend
2. Check logs for the rate limiting info message
3. Intentionally provide invalid credentials
4. Observe exponential backoff in logs
5. After 10 failures, verify cooldown message appears
6. Wait ~10 seconds and verify cooldown is active
7. Fix credentials and observe successful connection
8. Verify backoff resets to 5s on success

## Technical Details

### Thread Safety
- All rate limiting variables are protected by connection attempt logic
- No race conditions between threads
- Safe for concurrent access

### Scalability
- No external dependencies for rate limiting
- Minimal CPU/memory overhead
- Works with any number of backend instances

### Clock Dependencies
- Uses `datetime.datetime.now()` for timing
- Respects system clock adjustments
- No external time services required

## Related Files

- `fastapi_backend/app/dhan/live_feed.py` - Main rate limiting implementation
- `fastapi_backend/app/market/live_prices.py` - Price update mechanism
- `fastapi_backend/app/main.py` - Backend startup

## Support

If you encounter repeated rate limiting or believe the system is being too conservative, check:

1. DhanHQ API status and maintenance windows
2. Credential validity and permissions
3. Network connectivity and stability
4. System clock accuracy
5. Backend logs for error messages

For issues, enable DEBUG logging and review the detailed error messages provided.
