# Dhan v2 — All Data/WebSocket Rate Limitations (Trading APIs Excluded)

_Last updated: 2026-02-18_

## Scope
This document includes only **Data APIs**, **Quote APIs**, and **WebSocket market-data** constraints from official Dhan v2 docs.
It excludes trading/order API rate limits.

## 1) Global Limits from Dhan v2 Introduction
Source: https://dhanhq.co/docs/v2/#rate-limit

### Rate Limit Table (official categories)
| Rate Limit | Order APIs | Data APIs | Quote APIs | Non Trading APIs |
|---|---:|---:|---:|---:|
| per second | 10 | 5 | 1 | 20 |
| per minute | 250 | - | Unlimited | Unlimited |
| per hour | 1000 | - | Unlimited | Unlimited |
| per day | 7000 | 100000 | Unlimited | Unlimited |

### Applicable (non-trading) from the above table
- **Data APIs**: 5 requests/second, 100000/day
- **Quote APIs**: 1 request/second, unlimited minute/hour/day
- **Non Trading APIs**: 20 requests/second, unlimited minute/hour/day

> Note: “Order Modifications are capped at 25 modifications/order” is trading-related and not part of this document’s scope.

## 2) Market Quote API Limits
Source: https://dhanhq.co/docs/v2/market-quote/

Endpoints:
- `POST /marketfeed/ltp`
- `POST /marketfeed/ohlc`
- `POST /marketfeed/quote`

Documented constraints:
- Up to **1000 instruments in a single API request**
- **1 request per second**

## 3) Option Chain API Limits
Source: https://dhanhq.co/docs/v2/option-chain/

Endpoints:
- `POST /optionchain`
- `POST /optionchain/expirylist`

Documented constraints:
- **1 unique request every 3 seconds**
- Docs clarification: can fetch different underlyings/expiries concurrently within this policy boundary

## 4) Live Market Feed (WebSocket) Limits
Source: https://dhanhq.co/docs/v2/live-market-feed/

Endpoint:
- `wss://api-feed.dhan.co?version=2&token=...&clientId=...&authType=2`

Documented constraints:
- Up to **5 WebSocket connections per user**
- Up to **5000 instruments per connection**
- Up to **100 instruments per subscribe JSON message** (send multiple messages as needed)
- Server ping every **10 seconds**
- If no pong response for **>40 seconds**, connection is closed by server
- If more than 5 websockets are established, first socket can be disconnected with code **805**

## 5) Full Market Depth (WebSocket) Limits
Source: https://dhanhq.co/docs/v2/full-market-depth/

Endpoints:
- 20 level: `wss://depth-api-feed.dhan.co/twentydepth?token=...&clientId=...&authType=2`
- 200 level: `wss://full-depth-api.dhan.co/twohundreddepth?token=...&clientId=...&authType=2`

Documented constraints:
- **20 level depth**: up to **50 instruments per connection**
- **200 level depth**: only **1 instrument per connection**
- Keepalive behavior: ping every 10s, close after >40s without pong
- Excess websocket behavior references same disconnect rule with code 805 when exceeding 5 sockets

## 6) Historical & Expired Options Data Payload Constraints
These are request-data window constraints (not explicit RPS limits), but operationally important.

### Historical Data
Source: https://dhanhq.co/docs/v2/historical-data/
- Intraday endpoint (`POST /charts/intraday`): can poll only **90 days** at once per request

### Expired Options Data
Source: https://dhanhq.co/docs/v2/expired-options-data/
- Rolling options endpoint (`POST /charts/rollingoption`): can fetch up to **30 days** in a single API call

## 7) Release Notes Context (Data APIs)
Source: https://dhanhq.co/docs/v2/releases/
- v2.2 notes mention increased Data API limits and align with intro table values (notably 5/sec for Data APIs and 100000/day)
- v2.5 notes mention Option Chain rate-limit improvements and current 1 unique request/3s behavior

---

## Practical Usage Notes for System Design
- Treat **global table limits** as base ceilings.
- Where endpoint page specifies tighter limits (e.g., Market Quote 1 rps, Option Chain 1 unique/3s), apply tighter endpoint-specific control.
- For websockets, design sharding around:
  - max 5 sockets/user,
  - instrument caps per socket,
  - batched subscribe messages (100 per message for live feed).
