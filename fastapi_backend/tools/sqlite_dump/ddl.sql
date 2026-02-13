CREATE TABLE IF NOT EXISTS "users" (
  "id" SERIAL PRIMARY KEY,
  "username" VARCHAR,
  "role" VARCHAR,
  "active" BOOLEAN,
  "created_at" TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "wallets" (
  "id" SERIAL PRIMARY KEY,
  "user_id" INTEGER,
  "balance" DOUBLE PRECISION,
  "updated_at" TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "ledger" (
  "id" SERIAL PRIMARY KEY,
  "user_id" INTEGER,
  "amount" DOUBLE PRECISION,
  "reason" VARCHAR,
  "timestamp" TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "notifications" (
  "id" SERIAL PRIMARY KEY,
  "message" VARCHAR,
  "read" BOOLEAN,
  "timestamp" TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "dhan_credentials" (
  "id" SERIAL PRIMARY KEY,
  "client_id" VARCHAR,
  "api_key" VARCHAR,
  "api_secret" VARCHAR,
  "auth_token" VARCHAR,
  "daily_token" VARCHAR,
  "auth_mode" VARCHAR,
  "is_default" BOOLEAN DEFAULT false,
  "last_updated" TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "watchlist" (
  "id" SERIAL PRIMARY KEY,
  "user_id" INTEGER,
  "symbol" VARCHAR NOT NULL,
  "expiry_date" VARCHAR NOT NULL,
  "instrument_type" VARCHAR NOT NULL,
  "added_at" TIMESTAMP,
  "added_order" INTEGER
);

CREATE TABLE IF NOT EXISTS "subscriptions" (
  "id" SERIAL PRIMARY KEY,
  "instrument_token" VARCHAR NOT NULL,
  "symbol" VARCHAR NOT NULL,
  "expiry_date" VARCHAR,
  "strike_price" DOUBLE PRECISION,
  "option_type" VARCHAR,
  "tier" VARCHAR NOT NULL,
  "subscribed_at" TIMESTAMP,
  "ws_connection_id" INTEGER,
  "active" BOOLEAN
);

CREATE TABLE IF NOT EXISTS "atm_cache" (
  "id" SERIAL PRIMARY KEY,
  "underlying_symbol" VARCHAR NOT NULL,
  "current_ltp" DOUBLE PRECISION NOT NULL,
  "atm_strike" DOUBLE PRECISION NOT NULL,
  "strike_step" DOUBLE PRECISION NOT NULL,
  "cached_at" TIMESTAMP,
  "generated_strikes" TEXT
);

CREATE TABLE IF NOT EXISTS "subscription_log" (
  "id" SERIAL PRIMARY KEY,
  "action" VARCHAR NOT NULL,
  "instrument_token" VARCHAR,
  "reason" VARCHAR,
  "timestamp" TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "brokerage_plans" (
  "id" SERIAL PRIMARY KEY,
  "name" VARCHAR NOT NULL,
  "flat_fee" DOUBLE PRECISION,
  "percent_fee" DOUBLE PRECISION,
  "max_fee" DOUBLE PRECISION,
  "created_at" TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "user_accounts" (
  "id" SERIAL PRIMARY KEY,
  "username" VARCHAR NOT NULL,
  "email" VARCHAR,
  "role" VARCHAR,
  "status" VARCHAR,
  "allowed_segments" VARCHAR,
  "wallet_balance" DOUBLE PRECISION,
  "brokerage_plan_id" INTEGER,
  "created_at" TIMESTAMP,
  "updated_at" TIMESTAMP,
  "password_salt" VARCHAR,
  "password_hash" VARCHAR,
  "mobile" VARCHAR,
  "user_id" VARCHAR,
  "require_password_reset" BOOLEAN DEFAULT false,
  "margin_multiplier" DOUBLE PRECISION DEFAULT 5.0
);

CREATE TABLE IF NOT EXISTS "margin_accounts" (
  "id" SERIAL PRIMARY KEY,
  "user_id" INTEGER NOT NULL,
  "available_margin" DOUBLE PRECISION,
  "used_margin" DOUBLE PRECISION,
  "updated_at" TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "mock_positions" (
  "id" SERIAL PRIMARY KEY,
  "user_id" INTEGER NOT NULL,
  "symbol" VARCHAR NOT NULL,
  "exchange_segment" VARCHAR,
  "product_type" VARCHAR,
  "quantity" INTEGER,
  "avg_price" DOUBLE PRECISION,
  "realized_pnl" DOUBLE PRECISION,
  "status" VARCHAR,
  "created_at" TIMESTAMP,
  "updated_at" TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "ledger_entries" (
  "id" SERIAL PRIMARY KEY,
  "user_id" INTEGER NOT NULL,
  "entry_type" VARCHAR NOT NULL,
  "credit" DOUBLE PRECISION,
  "debit" DOUBLE PRECISION,
  "balance" DOUBLE PRECISION,
  "remarks" TEXT,
  "created_at" TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "mock_baskets" (
  "id" SERIAL PRIMARY KEY,
  "user_id" INTEGER NOT NULL,
  "name" VARCHAR NOT NULL,
  "status" VARCHAR,
  "created_at" TIMESTAMP,
  "updated_at" TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "mock_orders" (
  "id" SERIAL PRIMARY KEY,
  "user_id" INTEGER NOT NULL,
  "symbol" VARCHAR NOT NULL,
  "security_id" VARCHAR,
  "exchange_segment" VARCHAR,
  "transaction_type" VARCHAR NOT NULL,
  "quantity" INTEGER NOT NULL,
  "filled_qty" INTEGER,
  "order_type" VARCHAR,
  "product_type" VARCHAR,
  "price" DOUBLE PRECISION,
  "trigger_price" DOUBLE PRECISION,
  "status" VARCHAR,
  "basket_id" INTEGER,
  "is_super" BOOLEAN,
  "target_price" DOUBLE PRECISION,
  "stop_loss_price" DOUBLE PRECISION,
  "trailing_jump" DOUBLE PRECISION,
  "remarks" TEXT,
  "created_at" TIMESTAMP,
  "updated_at" TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "mock_basket_legs" (
  "id" SERIAL PRIMARY KEY,
  "basket_id" INTEGER NOT NULL,
  "symbol" VARCHAR NOT NULL,
  "security_id" VARCHAR,
  "exchange_segment" VARCHAR,
  "transaction_type" VARCHAR NOT NULL,
  "quantity" INTEGER NOT NULL,
  "order_type" VARCHAR,
  "product_type" VARCHAR,
  "price" DOUBLE PRECISION,
  "created_at" TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "mock_trades" (
  "id" SERIAL PRIMARY KEY,
  "order_id" INTEGER NOT NULL,
  "user_id" INTEGER NOT NULL,
  "price" DOUBLE PRECISION NOT NULL,
  "qty" INTEGER NOT NULL,
  "created_at" TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "execution_events" (
  "id" SERIAL PRIMARY KEY,
  "order_id" INTEGER,
  "user_id" INTEGER,
  "symbol" VARCHAR NOT NULL,
  "event_type" VARCHAR NOT NULL,
  "decision_time_price" DOUBLE PRECISION,
  "fill_price" DOUBLE PRECISION,
  "fill_quantity" INTEGER,
  "reason" VARCHAR,
  "latency_ms" INTEGER,
  "slippage" DOUBLE PRECISION,
  "created_at" TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "pnl_snapshots" (
  "id" SERIAL PRIMARY KEY,
  "user_id" INTEGER NOT NULL,
  "realized_pnl" DOUBLE PRECISION,
  "mtm" DOUBLE PRECISION,
  "total_pnl" DOUBLE PRECISION,
  "created_at" TIMESTAMP
);