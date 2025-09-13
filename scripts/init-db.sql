-- Initialize Android Container Platform Database

-- Create database if it doesn't exist
-- Note: This should be run by postgres user or superuser

-- Create schemas for different services
CREATE SCHEMA IF NOT EXISTS identity;
CREATE SCHEMA IF NOT EXISTS location;
CREATE SCHEMA IF NOT EXISTS network;
CREATE SCHEMA IF NOT EXISTS lifecycle;
CREATE SCHEMA IF NOT EXISTS api_gateway;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_device_identities_instance_id ON device_identities(instance_id);
CREATE INDEX IF NOT EXISTS idx_device_identities_imei ON device_identities(imei);
CREATE INDEX IF NOT EXISTS idx_device_identities_serial ON device_identities(serial_number);
CREATE INDEX IF NOT EXISTS idx_device_identities_created_at ON device_identities(created_at);

CREATE INDEX IF NOT EXISTS idx_location_data_instance_id ON location_data(instance_id);
CREATE INDEX IF NOT EXISTS idx_location_data_timestamp ON location_data(timestamp);

CREATE INDEX IF NOT EXISTS idx_network_configs_instance_id ON network_configs(instance_id);
CREATE INDEX IF NOT EXISTS idx_proxy_configs_type ON proxy_configs(proxy_type);
CREATE INDEX IF NOT EXISTS idx_proxy_configs_country ON proxy_configs(country);

CREATE INDEX IF NOT EXISTS idx_android_instances_status ON android_instances(status);
CREATE INDEX IF NOT EXISTS idx_android_instances_created_at ON android_instances(created_at);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);

-- Insert default admin user (password: admin123)
-- Hash generated with bcrypt
INSERT INTO users (id, username, email, password_hash, is_active, is_admin) 
VALUES (
    'admin_user_001',
    'admin',
    'admin@androidplatform.local',
    '$2b$12$LQv3c1yqBw1uK9mfT0eR7.sS4vTQNsKbv9yZ8w9OZ8z9z8z9z8z9z',
    true,
    true
) ON CONFLICT (username) DO NOTHING;

-- Insert default regular user (password: user123)
INSERT INTO users (id, username, email, password_hash, is_active, is_admin)
VALUES (
    'regular_user_001', 
    'demo',
    'demo@androidplatform.local',
    '$2b$12$KQv3c1yqBw1uK9mfT0eR7.sS4vTQNsKbv9yZ8w9OZ8z9z8z9z8z9z',
    true,
    false
) ON CONFLICT (username) DO NOTHING;

-- Create function to cleanup old records
CREATE OR REPLACE FUNCTION cleanup_old_records()
RETURNS void AS $$
BEGIN
    -- Clean up old location data (older than 30 days)
    DELETE FROM location_data 
    WHERE timestamp < NOW() - INTERVAL '30 days';
    
    -- Clean up old rate limit logs (older than 7 days)
    DELETE FROM rate_limit_logs 
    WHERE timestamp < NOW() - INTERVAL '7 days';
    
    -- Clean up inactive instances (stopped for more than 7 days)
    DELETE FROM android_instances 
    WHERE status = 'stopped' 
    AND stopped_at < NOW() - INTERVAL '7 days';
    
    -- Clean up old proxy check data
    UPDATE proxy_configs 
    SET is_working = false 
    WHERE last_checked < NOW() - INTERVAL '1 hour';
    
END;
$$ LANGUAGE plpgsql;

-- Create a scheduled job to run cleanup (requires pg_cron extension)
-- This would typically be set up by a DBA
-- SELECT cron.schedule('cleanup-old-records', '0 2 * * *', 'SELECT cleanup_old_records();');

-- Grant permissions
GRANT USAGE ON SCHEMA public TO acp_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO acp_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO acp_user;