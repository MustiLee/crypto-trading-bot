export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  phone?: string;
  telegram_id?: string;
  is_active: boolean;
  is_email_verified: boolean;
  last_login?: string;
  created_at: string;
}

export interface UserSession {
  session_token: string;
  user: User;
  expires_at: string;
}

export interface SymbolData {
  symbol: string;
  display_name: string;
  price: number;
  signal: 'BUY' | 'SELL' | 'NEUTRAL';
  indicators: {
    RSI: number;
    MACD: number;
    BB_UPPER: number;
    BB_LOWER: number;
  };
  timestamp: string;
  strategy_type: string;
}

export interface StrategyConfig {
  name: string;
  description?: string;
  parameters: {
    [key: string]: number | string | boolean;
  };
}

export interface BacktestResult {
  total_return: number;
  sharpe_ratio: number;
  max_drawdown: number;
  win_rate: number;
  total_trades: number;
  start_date: string;
  end_date: string;
  final_portfolio_value: number;
  equity_curve: Array<{
    date: string;
    value: number;
  }>;
}

export interface WebSocketMessage {
  type: 'symbol_update' | 'connection_status' | 'error';
  symbol?: string;
  data?: SymbolData;
  message?: string;
}

export type RootStackParamList = {
  AuthStack: undefined;
  MainTabs: undefined;
  StrategyTest: {
    symbol: string;
    displayName: string;
  };
};

export type AuthStackParamList = {
  Login: undefined;
  Register: undefined;
};

export type MainTabParamList = {
  Dashboard: undefined;
  Profile: undefined;
  Strategies: undefined;
};