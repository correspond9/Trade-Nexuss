-- Credentials Database Schema
-- Dedicated database for storing Dhan API credentials and other sensitive configurations

-- Create credentials database
-- This will be stored as: credentials.db

-- Table for Dhan API credentials
CREATE TABLE IF NOT EXISTS dhan_credentials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    credential_type TEXT NOT NULL CHECK (credential_type IN ('STATIC_IP', 'DAILY_TOKEN')),
    client_id TEXT,
    api_key TEXT,
    api_secret TEXT,
    authorization_token TEXT,
    expiry_time DATETIME,
    is_active BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT,
    last_used_at DATETIME,
    
    -- Ensure only one credential type is active at a time
    CONSTRAINT unique_active_credential_type UNIQUE (credential_type) 
    WHERE is_active = 1
);

-- Table for credential usage logs
CREATE TABLE IF NOT EXISTS credential_usage_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    credential_id INTEGER NOT NULL,
    usage_type TEXT NOT NULL,
    success BOOLEAN DEFAULT 1,
    error_message TEXT,
    used_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (credential_id) REFERENCES dhan_credentials(id) ON DELETE CASCADE
);

-- Table for API configuration settings
CREATE TABLE IF NOT EXISTS api_configurations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_key TEXT UNIQUE NOT NULL,
    config_value TEXT,
    config_type TEXT DEFAULT 'string',
    description TEXT,
    is_encrypted BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_by TEXT
);

-- Insert default API configurations
INSERT OR IGNORE INTO api_configurations (config_key, config_value, config_type, description) VALUES
('dhan_ws_url', 'wss://api-feed.dhan.co', 'string', 'Dhan WebSocket API URL'),
('dhan_api_version', '2', 'string', 'Dhan API version'),
('max_reconnect_attempts', '5', 'integer', 'Maximum WebSocket reconnection attempts'),
('credential_auto_refresh', 'true', 'boolean', 'Auto-refresh daily tokens'),
('rate_limit_quotes', '1', 'integer', 'Rate limit: quotes per second'),
('rate_limit_data', '5', 'integer', 'Rate limit: data requests per second');

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_dhan_credentials_type ON dhan_credentials(credential_type);
CREATE INDEX IF NOT EXISTS idx_dhan_credentials_active ON dhan_credentials(is_active);
CREATE INDEX IF NOT EXISTS idx_credential_usage_logs_credential_id ON credential_usage_logs(credential_id);
CREATE INDEX IF NOT EXISTS idx_credential_usage_logs_used_at ON credential_usage_logs(used_at);
CREATE INDEX IF NOT EXISTS idx_api_configurations_key ON api_configurations(config_key);

-- Create trigger to update updated_at timestamp
CREATE TRIGGER IF NOT EXISTS update_dhan_credentials_timestamp 
    AFTER UPDATE ON dhan_credentials
    FOR EACH ROW
BEGIN
    UPDATE dhan_credentials SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_api_configurations_timestamp 
    AFTER UPDATE ON api_configurations
    FOR EACH ROW
BEGIN
    UPDATE api_configurations SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Create view for active credentials
CREATE VIEW IF NOT EXISTS active_dhan_credentials AS
SELECT 
    id,
    credential_type,
    client_id,
    api_key,
    -- Never expose api_secret in views
    '' as api_secret_masked,
    authorization_token,
    expiry_time,
    created_at,
    updated_at,
    created_by,
    last_used_at,
    CASE 
        WHEN expiry_time > datetime('now') THEN 'valid'
        WHEN expiry_time <= datetime('now') THEN 'expired'
        ELSE 'no_expiry'
    END as status
FROM dhan_credentials 
WHERE is_active = 1;
