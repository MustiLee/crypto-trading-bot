import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform } from 'react-native';
import { API_BASE_URL, WS_BASE_URL } from '../config';
import { User, UserSession, StrategyConfig, BacktestResult } from '../types';

// API base URL is configured via app.json extra; falls back to localhost

const STORAGE_KEYS = {
  SESSION_TOKEN: 'session_token',
  USER_DATA: 'user_data',
  SYMBOLS_CONFIG: 'symbols_config_v1',
};

class ApiService {
  private sessionToken: string | null = null;

  async initialize() {
    this.sessionToken = await AsyncStorage.getItem(STORAGE_KEYS.SESSION_TOKEN);
  }

  private async getHeaders(): Promise<HeadersInit> {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };

    if (this.sessionToken) {
      headers['Authorization'] = `Bearer ${this.sessionToken}`;
    }

    return headers;
  }

  private async handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
      let message: string = `HTTP Error: ${response.status}`;
      let code: string | undefined;
      try {
        const errorData = await response.json();
        const detail = errorData?.detail || errorData;
        if (typeof detail === 'object') {
          message = detail.message || message;
          code = detail.code;
        } else if (typeof detail === 'string') {
          message = detail;
        }
      } catch {
        const txt = await response.text();
        if (txt) message = txt;
      }
      const err: any = new Error(message);
      err.code = code;
      err.status = response.status;
      throw err;
    }
    return await response.json();
  }

  // Authentication APIs
  async login(email: string, password: string): Promise<UserSession> {
    console.log('Login attempt:', email);
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email,
          password
        }),
      });

      const session = await this.handleResponse<UserSession>(response);
      
      // Store session data
      this.sessionToken = session.session_token;
      await AsyncStorage.setItem(STORAGE_KEYS.SESSION_TOKEN, session.session_token);
      await AsyncStorage.setItem(STORAGE_KEYS.USER_DATA, JSON.stringify(session.user));
      
      console.log('Login successful');
      return session;
    } catch (error) {
      console.error('Login error:', error);
      throw error instanceof Error ? error : new Error('Giriş sırasında bir hata oluştu.');
    }
  }

  async register(userData: {
    email: string;
    password: string;
    first_name: string;
    last_name: string;
    phone?: string;
    telegram_id?: string;
  }): Promise<{ success: boolean; message: string }> {
    console.log('Register attempt:', userData.email);
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: userData.email,
          password: userData.password,
          first_name: userData.first_name,
          last_name: userData.last_name,
          phone: userData.phone || ''
        }),
      });

      const result = await this.handleResponse(response);
      return result;
    } catch (error) {
      console.error('Registration error:', error);
      return {
        success: false,
        message: error instanceof Error ? error.message : 'Kayıt sırasında bir hata oluştu.'
      };
    }
  }

  async verifyEmail(email: string, verificationCode: string): Promise<{ success: boolean; message: string }> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/verify-email`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          email, 
          verification_code: verificationCode 
        }),
      });

      const result = await this.handleResponse(response);
      return result;
    } catch (error) {
      console.error('Verify email error:', error);
      return {
        success: false,
        message: error instanceof Error ? error.message : 'Doğrulama sırasında bir hata oluştu.'
      };
    }
  }

  async resendVerificationCode(email: string): Promise<{ success: boolean; message: string }> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/resend-verification`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
      });

      const result = await this.handleResponse(response);
      return result;
    } catch (error) {
      console.error('Resend verification error:', error);
      return {
        success: false,
        message: error instanceof Error ? error.message : 'Kod gönderilirken bir hata oluştu.'
      };
    }
  }

  async logout(): Promise<void> {
    if (this.sessionToken) {
      try {
        await fetch(`${API_BASE_URL}/api/v1/auth/logout`, {
          method: 'POST',
          headers: await this.getHeaders(),
        });
      } catch (error) {
        console.warn('Logout API call failed:', error);
      }
    }

    // Clear local storage
    this.sessionToken = null;
    await AsyncStorage.multiRemove([STORAGE_KEYS.SESSION_TOKEN, STORAGE_KEYS.USER_DATA]);
  }

  // Profile update
  async updateProfile(partial: {
    first_name?: string;
    last_name?: string;
    phone?: string;
    telegram_id?: string;
  }): Promise<{ success: boolean; message: string }> {
    const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
      method: 'PUT',
      headers: await this.getHeaders(),
      body: JSON.stringify(partial),
    });
    return await this.handleResponse(response);
  }

  // Password reset flow
  async requestPasswordReset(email: string): Promise<{ success: boolean; message: string }> {
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/request-password-reset`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    });
    return await this.handleResponse(response);
  }

  async verifyPasswordReset(email: string, code: string): Promise<{ success: boolean; message: string }> {
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/verify-password-reset`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, verification_code: code }),
    });
    return await this.handleResponse(response);
  }

  async resetPassword(email: string, newPassword: string): Promise<{ success: boolean; message: string }> {
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/reset-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, new_password: newPassword }),
    });
    return await this.handleResponse(response);
  }

  async getCurrentUser(): Promise<User | null> {
    const userData = await AsyncStorage.getItem(STORAGE_KEYS.USER_DATA);
    if (!userData || !this.sessionToken) {
      return null;
    }

    try {
      // Verify session is still valid
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
        headers: await this.getHeaders(),
      });

      if (response.ok) {
        return JSON.parse(userData);
      } else {
        // Session expired, clear storage
        await this.logout();
        return null;
      }
    } catch (error) {
      console.error('Error verifying session:', error);
      return null;
    }
  }

  // Strategy APIs
  async createStrategy(strategy: StrategyConfig): Promise<{ success: boolean; message: string; strategy_id?: string }> {
    const response = await fetch(`${API_BASE_URL}/api/v1/strategies/create`, {
      method: 'POST',
      headers: await this.getHeaders(),
      body: JSON.stringify(strategy),
    });

    return await this.handleResponse(response);
  }

  async testStrategy(strategyId: string, symbol: string): Promise<BacktestResult> {
    const response = await fetch(`${API_BASE_URL}/api/v1/strategies/${strategyId}/test`, {
      method: 'POST',
      headers: await this.getHeaders(),
      body: JSON.stringify({ symbol }),
    });

    return await this.handleResponse(response);
  }

  async getUserStrategies(): Promise<StrategyConfig[]> {
    const response = await fetch(`${API_BASE_URL}/api/v1/strategies/my-strategies`, {
      headers: await this.getHeaders(),
    });

    return await this.handleResponse(response);
  }

  async activateStrategy(strategyId: string): Promise<{ success: boolean; message: string }> {
    const response = await fetch(`${API_BASE_URL}/api/v1/strategies/${strategyId}/activate`, {
      method: 'POST',
      headers: await this.getHeaders(),
    });

    return await this.handleResponse(response);
  }

  // Get real-time market data from dashboard
  async getMarketData(): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/api/symbols`);
    return await this.handleResponse(response);
  }

  // Get current price for a specific symbol from dashboard
  async getCurrentPrice(symbol: string): Promise<{ price: number; change: number } | null> {
    try {
      // First try to get from dashboard WebSocket data via REST endpoint
      const marketResponse = await fetch(`${API_BASE_URL}/api/signals/${symbol.replace('USDT', '')}`);
      if (marketResponse.ok) {
        const data = await marketResponse.json();
        // If we have recent signal data with price info
        if (data.signals && data.signals.length > 0) {
          const latestSignal = data.signals[0];
          return {
            price: latestSignal.price || 0,
            change: latestSignal.change || 0
          };
        }
      }
      
      // Fallback: try to connect to WebSocket for live data
      // This is a simplified approach - in production you'd maintain a persistent connection
      return null;
    } catch (error) {
      console.warn('Failed to get current price from dashboard:', error);
      return null;
    }
  }

  // Dashboard APIs
  async getSymbolData(): Promise<{ [symbol: string]: any }> {
    const response = await fetch(`${API_BASE_URL}/dashboard/symbols`, {
      headers: await this.getHeaders(),
    });

    return await this.handleResponse(response);
  }

  async getSymbolsConfig(): Promise<{ symbols: Record<string, any>; interval: string }> {
    const response = await fetch(`${API_BASE_URL}/api/symbols`, {
      headers: await this.getHeaders(),
    });
    return await this.handleResponse(response);
  }

  async getSymbolsCached(maxAgeMs: number = 5 * 60 * 1000): Promise<{ symbols: Record<string, any>; interval: string } | null> {
    try {
      const cached = await AsyncStorage.getItem(STORAGE_KEYS.SYMBOLS_CONFIG);
      if (cached) {
        const parsed = JSON.parse(cached);
        const ts = parsed?.__ts as number | undefined;
        if (ts && Date.now() - ts < maxAgeMs && parsed?.symbols) {
          return { symbols: parsed.symbols, interval: parsed.interval };
        }
      }
    } catch {}

    try {
      const fresh = await this.getSymbolsConfig();
      await AsyncStorage.setItem(
        STORAGE_KEYS.SYMBOLS_CONFIG,
        JSON.stringify({ ...fresh, __ts: Date.now() })
      );
      return fresh;
    } catch (e) {
      console.warn('Failed to fetch symbols config:', e);
      return null;
    }
  }

  // User Layout Preferences APIs
  async getUserLayoutPreferences(): Promise<{ asset_order?: string[] }> {
    const response = await fetch(`${API_BASE_URL}/api/v1/user/layout-preferences`, {
      headers: await this.getHeaders(),
    });

    return await this.handleResponse(response);
  }

  async saveUserLayoutPreferences(preferences: { asset_order: string[] }): Promise<{ success: boolean }> {
    const response = await fetch(`${API_BASE_URL}/api/v1/user/layout-preferences`, {
      method: 'POST',
      headers: await this.getHeaders(),
      body: JSON.stringify(preferences),
    });

    return await this.handleResponse(response);
  }

  // WebSocket connection
  createWebSocketConnection(): WebSocket {
    // Get appropriate WebSocket URL based on platform
    const base = WS_BASE_URL;
    const url = this.sessionToken ? `${base}?token=${encodeURIComponent(this.sessionToken)}` : base;
    console.log('Connecting to WebSocket:', url);
    return new WebSocket(url);
  }
}

export const apiService = new ApiService();
