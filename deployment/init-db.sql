-- Initialize trader database schema

-- Create database if not exists (this runs automatically with POSTGRES_DB)
-- Database: trader_db

-- Market data table for OHLCV candle data
CREATE TABLE IF NOT EXISTS market_data (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    open DECIMAL(20,8) NOT NULL,
    high DECIMAL(20,8) NOT NULL,
    low DECIMAL(20,8) NOT NULL,
    close DECIMAL(20,8) NOT NULL,
    volume DECIMAL(20,8) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(symbol, timeframe, timestamp)
);

-- Technical indicators table
CREATE TABLE IF NOT EXISTS indicators (
    id SERIAL PRIMARY KEY,
    market_data_id INTEGER REFERENCES market_data(id) ON DELETE CASCADE,
    rsi DECIMAL(10,4),
    macd DECIMAL(10,4),
    macd_signal DECIMAL(10,4),
    macd_histogram DECIMAL(10,4),
    bb_upper DECIMAL(20,8),
    bb_middle DECIMAL(20,8),
    bb_lower DECIMAL(20,8),
    atr DECIMAL(10,4),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(market_data_id)
);

-- Trading signals table
CREATE TABLE IF NOT EXISTS signals (
    id SERIAL PRIMARY KEY,
    market_data_id INTEGER REFERENCES market_data(id) ON DELETE CASCADE,
    signal_type VARCHAR(10) NOT NULL CHECK (signal_type IN ('BUY', 'SELL', 'NEUTRAL')),
    signal_strength DECIMAL(5,2),
    strategy_name VARCHAR(50) DEFAULT 'realistic1',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_market_data_symbol_timeframe_timestamp ON market_data(symbol, timeframe, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_market_data_timestamp ON market_data(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_signals_created_at ON signals(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_signals_market_data_id ON signals(market_data_id);
CREATE INDEX IF NOT EXISTS idx_indicators_market_data_id ON indicators(market_data_id);

-- Grant permissions to trader user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO trader;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO trader;

-- User management tables

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(254) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    phone VARCHAR(20),
    telegram_id VARCHAR(50),
    is_active BOOLEAN DEFAULT FALSE,
    is_email_verified BOOLEAN DEFAULT FALSE,
    email_verification_token VARCHAR(255),
    email_verification_expires TIMESTAMP WITH TIME ZONE,
    password_reset_token VARCHAR(255),
    password_reset_expires TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE
);

-- Create index on email for faster lookups
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Create user_sessions table
CREATE TABLE IF NOT EXISTS user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    user_agent TEXT,
    ip_address VARCHAR(45)
);

-- Create index on session_token for faster lookups
CREATE INDEX IF NOT EXISTS idx_user_sessions_token ON user_sessions(session_token);

-- Create email_verifications table for temporary storage of verification codes
CREATE TABLE IF NOT EXISTS email_verifications (
    email VARCHAR(254) PRIMARY KEY,
    verification_code VARCHAR(10) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create temp_registrations table for temporary user data during registration
CREATE TABLE IF NOT EXISTS temp_registrations (
    email VARCHAR(254) PRIMARY KEY,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create custom_strategies table
CREATE TABLE IF NOT EXISTS custom_strategies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    strategy_config TEXT NOT NULL, -- JSON stored as text
    backtest_results TEXT, -- JSON stored as text
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indicator_configs table
CREATE TABLE IF NOT EXISTS indicator_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    bb_period INTEGER DEFAULT 20,
    bb_std FLOAT DEFAULT 2.0,
    macd_fast INTEGER DEFAULT 12,
    macd_slow INTEGER DEFAULT 26,
    macd_signal INTEGER DEFAULT 9,
    rsi_period INTEGER DEFAULT 14,
    rsi_overbought FLOAT DEFAULT 70.0,
    rsi_oversold FLOAT DEFAULT 30.0,
    ema_short INTEGER DEFAULT 20,
    ema_long INTEGER DEFAULT 50,
    ema_trend INTEGER DEFAULT 200,
    atr_period INTEGER DEFAULT 14,
    use_volume_indicators BOOLEAN DEFAULT TRUE,
    use_volatility_indicators BOOLEAN DEFAULT TRUE,
    use_momentum_indicators BOOLEAN DEFAULT TRUE,
    use_trend_indicators BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_default BOOLEAN DEFAULT FALSE
);

-- Create function to update updated_at timestamp automatically
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers to automatically update updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_custom_strategies_updated_at BEFORE UPDATE ON custom_strategies 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_indicator_configs_updated_at BEFORE UPDATE ON indicator_configs 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert a test user (optional, for development)
INSERT INTO users (
    email, 
    password_hash, 
    first_name, 
    last_name, 
    is_active, 
    is_email_verified
) 
VALUES (
    'test@example.com',
    'scrypt:32768:8:1$VjwKXnQAYAjFELdJ$5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8', -- password: 'testpass123'
    'Test',
    'User',
    TRUE,
    TRUE
) ON CONFLICT (email) DO NOTHING;

-- Display table info
\dt