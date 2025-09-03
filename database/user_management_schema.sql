-- User Management Database Schema for Cryptocurrency Trading Bot
-- This file contains the database schema for user management functionality

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(254) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    phone VARCHAR(20),
    telegram_id VARCHAR(50),
    
    -- Account status
    is_active BOOLEAN DEFAULT FALSE,
    is_email_verified BOOLEAN DEFAULT FALSE,
    email_verification_token VARCHAR(255),
    email_verification_expires TIMESTAMPTZ,
    
    -- Password reset
    password_reset_token VARCHAR(255),
    password_reset_expires TIMESTAMPTZ,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMPTZ
);

-- User sessions table
CREATE TABLE IF NOT EXISTS user_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    user_agent TEXT,
    ip_address VARCHAR(45)
);

-- Custom trading strategies table
CREATE TABLE IF NOT EXISTS custom_strategies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    
    -- Strategy configuration stored as JSON
    strategy_config TEXT NOT NULL,
    
    -- Performance tracking
    backtest_results TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Custom indicator configurations table
CREATE TABLE IF NOT EXISTS indicator_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    
    -- Bollinger Bands parameters
    bb_period INTEGER DEFAULT 20 CHECK (bb_period >= 5 AND bb_period <= 50),
    bb_std DECIMAL(4,2) DEFAULT 2.0 CHECK (bb_std >= 1.0 AND bb_std <= 3.5),
    
    -- MACD parameters
    macd_fast INTEGER DEFAULT 12 CHECK (macd_fast >= 3 AND macd_fast <= 20),
    macd_slow INTEGER DEFAULT 26 CHECK (macd_slow >= 15 AND macd_slow <= 50),
    macd_signal INTEGER DEFAULT 9 CHECK (macd_signal >= 3 AND macd_signal <= 15),
    
    -- RSI parameters
    rsi_period INTEGER DEFAULT 14 CHECK (rsi_period >= 3 AND rsi_period <= 30),
    rsi_overbought DECIMAL(5,2) DEFAULT 70.0 CHECK (rsi_overbought >= 55.0 AND rsi_overbought <= 90.0),
    rsi_oversold DECIMAL(5,2) DEFAULT 30.0 CHECK (rsi_oversold >= 10.0 AND rsi_oversold <= 45.0),
    
    -- EMA parameters
    ema_short INTEGER DEFAULT 20 CHECK (ema_short >= 3 AND ema_short <= 50),
    ema_long INTEGER DEFAULT 50 CHECK (ema_long >= 20 AND ema_long <= 200),
    ema_trend INTEGER DEFAULT 200 CHECK (ema_trend >= 50 AND ema_trend <= 500),
    
    -- ATR parameters
    atr_period INTEGER DEFAULT 14 CHECK (atr_period >= 5 AND atr_period <= 30),
    
    -- Advanced indicators toggles
    use_volume_indicators BOOLEAN DEFAULT TRUE,
    use_volatility_indicators BOOLEAN DEFAULT TRUE,
    use_momentum_indicators BOOLEAN DEFAULT TRUE,
    use_trend_indicators BOOLEAN DEFAULT TRUE,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    is_default BOOLEAN DEFAULT FALSE,
    
    -- Constraints
    CONSTRAINT valid_macd_periods CHECK (macd_fast < macd_slow),
    CONSTRAINT valid_rsi_levels CHECK (rsi_oversold < rsi_overbought),
    CONSTRAINT valid_ema_periods CHECK (ema_short < ema_long AND ema_long < ema_trend)
);

-- User portfolio tracking (optional extension)
CREATE TABLE IF NOT EXISTS user_portfolios (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    
    -- Position information
    quantity DECIMAL(20,8) DEFAULT 0,
    avg_price DECIMAL(20,8) DEFAULT 0,
    total_invested DECIMAL(20,2) DEFAULT 0,
    current_value DECIMAL(20,2) DEFAULT 0,
    unrealized_pnl DECIMAL(20,2) DEFAULT 0,
    
    -- Strategy used
    strategy_id UUID REFERENCES custom_strategies(id),
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(user_id, symbol)
);

-- User trading activity log
CREATE TABLE IF NOT EXISTS user_trading_activity (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    
    -- Trade information
    action VARCHAR(10) NOT NULL CHECK (action IN ('BUY', 'SELL')),
    quantity DECIMAL(20,8) NOT NULL,
    price DECIMAL(20,8) NOT NULL,
    total_amount DECIMAL(20,2) NOT NULL,
    fees DECIMAL(20,2) DEFAULT 0,
    
    -- Strategy and signal information
    strategy_id UUID REFERENCES custom_strategies(id),
    signal_strength DECIMAL(5,2),
    
    -- Metadata
    executed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

-- Indexes for performance optimization
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_verification_token ON users(email_verification_token);
CREATE INDEX IF NOT EXISTS idx_users_reset_token ON users(password_reset_token);
CREATE INDEX IF NOT EXISTS idx_user_sessions_token ON user_sessions(session_token);
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_expires ON user_sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_custom_strategies_user_id ON custom_strategies(user_id);
CREATE INDEX IF NOT EXISTS idx_custom_strategies_active ON custom_strategies(user_id, is_active);
CREATE INDEX IF NOT EXISTS idx_indicator_configs_user_id ON indicator_configs(user_id);
CREATE INDEX IF NOT EXISTS idx_indicator_configs_default ON indicator_configs(user_id, is_default);
CREATE INDEX IF NOT EXISTS idx_user_portfolios_user_symbol ON user_portfolios(user_id, symbol);
CREATE INDEX IF NOT EXISTS idx_trading_activity_user_id ON user_trading_activity(user_id);
CREATE INDEX IF NOT EXISTS idx_trading_activity_symbol ON user_trading_activity(symbol);
CREATE INDEX IF NOT EXISTS idx_trading_activity_executed ON user_trading_activity(executed_at);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers to automatically update updated_at timestamps
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_custom_strategies_updated_at BEFORE UPDATE ON custom_strategies FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_indicator_configs_updated_at BEFORE UPDATE ON indicator_configs FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_user_portfolios_updated_at BEFORE UPDATE ON user_portfolios FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to clean up expired sessions
CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM user_sessions WHERE expires_at < CURRENT_TIMESTAMP;
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to clean up expired tokens
CREATE OR REPLACE FUNCTION cleanup_expired_tokens()
RETURNS INTEGER AS $$
DECLARE
    updated_count INTEGER;
BEGIN
    UPDATE users 
    SET email_verification_token = NULL, 
        email_verification_expires = NULL
    WHERE email_verification_expires < CURRENT_TIMESTAMP
    AND email_verification_token IS NOT NULL;
    
    GET DIAGNOSTICS updated_count = ROW_COUNT;
    
    UPDATE users 
    SET password_reset_token = NULL, 
        password_reset_expires = NULL
    WHERE password_reset_expires < CURRENT_TIMESTAMP
    AND password_reset_token IS NOT NULL;
    
    RETURN updated_count;
END;
$$ LANGUAGE plpgsql;

-- Create default admin user (for testing purposes - change password in production!)
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM users WHERE email = 'admin@trader.local') THEN
        INSERT INTO users (
            email, 
            password_hash, 
            first_name, 
            last_name, 
            is_active, 
            is_email_verified
        ) VALUES (
            'admin@trader.local',
            'pbkdf2:sha256:260000$G8fzHXrJ$8c1f0c6e1a2d3b4c5d6e7f8g9h0i1j2k3l4m5n6o7p8q9r0s1t2u3v4w5x6y7z8',  -- password: admin123
            'Admin',
            'User',
            TRUE,
            TRUE
        );
        
        -- Create default indicator config for admin user
        INSERT INTO indicator_configs (
            user_id,
            name,
            is_default
        ) SELECT 
            id,
            'Default Configuration',
            TRUE
        FROM users 
        WHERE email = 'admin@trader.local';
    END IF;
END $$;

-- Comments for documentation
COMMENT ON TABLE users IS 'User accounts for the cryptocurrency trading bot';
COMMENT ON TABLE user_sessions IS 'Active user sessions for authentication';
COMMENT ON TABLE custom_strategies IS 'User-defined custom trading strategies';
COMMENT ON TABLE indicator_configs IS 'User-defined indicator configurations';
COMMENT ON TABLE user_portfolios IS 'User portfolio tracking (optional)';
COMMENT ON TABLE user_trading_activity IS 'Log of user trading activities';

COMMENT ON COLUMN users.email_verification_token IS 'Token for email verification, expires in 24 hours';
COMMENT ON COLUMN users.password_reset_token IS 'Token for password reset, expires in 1 hour';
COMMENT ON COLUMN custom_strategies.strategy_config IS 'JSON configuration for the trading strategy';
COMMENT ON COLUMN custom_strategies.backtest_results IS 'JSON results from strategy backtesting';
COMMENT ON COLUMN indicator_configs.is_default IS 'Whether this is the user''s default indicator configuration';

-- Sample data for testing (optional - remove in production)
INSERT INTO users (email, password_hash, first_name, last_name, is_active, is_email_verified) 
VALUES ('test@trader.local', 'pbkdf2:sha256:260000$testuser$abc123def456', 'Test', 'User', TRUE, TRUE)
ON CONFLICT (email) DO NOTHING;

-- Create a sample strategy for the test user
DO $$
DECLARE
    test_user_id UUID;
BEGIN
    SELECT id INTO test_user_id FROM users WHERE email = 'test@trader.local';
    
    IF test_user_id IS NOT NULL THEN
        INSERT INTO custom_strategies (
            user_id,
            name,
            description,
            strategy_config
        ) VALUES (
            test_user_id,
            'Sample Conservative Strategy',
            'A conservative trading strategy with safe parameters',
            '{"strategy_type": "quality_over_quantity", "indicators": {"bollinger_bands": {"period": 20, "std_dev": 2.0}, "macd": {"fast": 12, "slow": 26, "signal": 9}, "rsi": {"period": 14}}, "risk_management": {"position_size_pct": 0.05}}'
        );
        
        INSERT INTO indicator_configs (
            user_id,
            name,
            is_default
        ) VALUES (
            test_user_id,
            'Conservative Settings',
            TRUE
        );
    END IF;
END $$;