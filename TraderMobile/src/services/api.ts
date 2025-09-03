import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform } from 'react-native';
import { User, UserSession, StrategyConfig, BacktestResult } from '../types';

// Get the appropriate base URL based on platform
const getApiBaseUrl = () => {
  if (Platform.OS === 'web') {
    // For web development, use localhost
    return 'http://localhost:8000';
  } else {
    // For mobile (Expo Go), use local IP address
    return 'http://192.168.68.103:8000';
  }
};

const API_BASE_URL = getApiBaseUrl();

const STORAGE_KEYS = {
  SESSION_TOKEN: 'session_token',
  USER_DATA: 'user_data',
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
      let error: string;
      try {
        const errorData = await response.json();
        error = errorData.detail || errorData.message || `HTTP Error: ${response.status}`;
      } catch {
        error = await response.text() || `HTTP Error: ${response.status}`;
      }
      console.error('API Error:', error);
      throw new Error(error);
    }
    return await response.json();
  }

  // Authentication APIs
  async login(email: string, password: string): Promise<UserSession> {
    console.log('Login attempt:', email);
    
    // Mock login for demo - check against test user
    if (email === 'test@example.com' && password === 'testpass123') {
      const mockSession: UserSession = {
        session_token: 'mock-token-' + Date.now(),
        user: {
          id: 'mock-user-id',
          email: 'test@example.com',
          first_name: 'Test',
          last_name: 'User',
          phone: null,
          telegram_id: null,
          is_active: true,
          is_email_verified: true,
          last_login: new Date().toISOString(),
          created_at: new Date().toISOString()
        },
        expires_at: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString()
      };
      
      // Store session data
      this.sessionToken = mockSession.session_token;
      await AsyncStorage.setItem(STORAGE_KEYS.SESSION_TOKEN, mockSession.session_token);
      await AsyncStorage.setItem(STORAGE_KEYS.USER_DATA, JSON.stringify(mockSession.user));
      
      console.log('Mock login successful');
      return mockSession;
    }
    
    throw new Error('Invalid email or password');
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
      const response = await fetch(`${API_BASE_URL}/auth/register`, {
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
      const response = await fetch(`${API_BASE_URL}/auth/verify-email`, {
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
      console.error('Email verification error:', error);
      return {
        success: false,
        message: error instanceof Error ? error.message : 'Doğrulama sırasında bir hata oluştu.'
      };
    }
  }

  async resendVerificationCode(email: string): Promise<{ success: boolean; message: string }> {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/resend-verification`, {
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
        await fetch(`${API_BASE_URL}/auth/logout`, {
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

  async getCurrentUser(): Promise<User | null> {
    const userData = await AsyncStorage.getItem(STORAGE_KEYS.USER_DATA);
    if (!userData || !this.sessionToken) {
      return null;
    }

    try {
      // Verify session is still valid
      const response = await fetch(`${API_BASE_URL}/auth/me`, {
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
    const response = await fetch(`${API_BASE_URL}/strategies/create`, {
      method: 'POST',
      headers: await this.getHeaders(),
      body: JSON.stringify(strategy),
    });

    return await this.handleResponse(response);
  }

  async testStrategy(strategyId: string, symbol: string): Promise<BacktestResult> {
    const response = await fetch(`${API_BASE_URL}/strategies/${strategyId}/test`, {
      method: 'POST',
      headers: await this.getHeaders(),
      body: JSON.stringify({ symbol }),
    });

    return await this.handleResponse(response);
  }

  async getUserStrategies(): Promise<StrategyConfig[]> {
    const response = await fetch(`${API_BASE_URL}/strategies/my-strategies`, {
      headers: await this.getHeaders(),
    });

    return await this.handleResponse(response);
  }

  async activateStrategy(strategyId: string): Promise<{ success: boolean; message: string }> {
    const response = await fetch(`${API_BASE_URL}/strategies/${strategyId}/activate`, {
      method: 'POST',
      headers: await this.getHeaders(),
    });

    return await this.handleResponse(response);
  }

  // Dashboard APIs
  async getSymbolData(): Promise<{ [symbol: string]: any }> {
    const response = await fetch(`${API_BASE_URL}/dashboard/symbols`, {
      headers: await this.getHeaders(),
    });

    return await this.handleResponse(response);
  }

  // WebSocket connection
  createWebSocketConnection(): WebSocket {
    // Get appropriate WebSocket URL based on platform
    const getWebSocketUrl = () => {
      if (Platform.OS === 'web') {
        return 'ws://localhost:8000/ws';
      } else {
        return 'ws://192.168.68.103:8000/ws';
      }
    };
    
    const base = getWebSocketUrl();
    const url = this.sessionToken ? `${base}?token=${encodeURIComponent(this.sessionToken)}` : base;
    console.log('Connecting to WebSocket:', url);
    return new WebSocket(url);
  }
}

export const apiService = new ApiService();
