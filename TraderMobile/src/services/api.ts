import AsyncStorage from '@react-native-async-storage/async-storage';
import { User, UserSession, StrategyConfig, BacktestResult } from '../types';

const API_BASE_URL = 'http://localhost:8000';
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
      const error = await response.text();
      throw new Error(error || `HTTP Error: ${response.status}`);
    }
    return await response.json();
  }

  // Authentication APIs
  async login(email: string, password: string): Promise<UserSession> {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: await this.getHeaders(),
      body: JSON.stringify({ email, password }),
    });

    const session = await this.handleResponse<UserSession>(response);
    
    // Store session data
    this.sessionToken = session.session_token;
    await AsyncStorage.setItem(STORAGE_KEYS.SESSION_TOKEN, session.session_token);
    await AsyncStorage.setItem(STORAGE_KEYS.USER_DATA, JSON.stringify(session.user));
    
    return session;
  }

  async register(userData: {
    email: string;
    password: string;
    first_name: string;
    last_name: string;
    phone?: string;
    telegram_id?: string;
  }): Promise<{ success: boolean; message: string }> {
    const response = await fetch(`${API_BASE_URL}/auth/register`, {
      method: 'POST',
      headers: await this.getHeaders(),
      body: JSON.stringify(userData),
    });

    return await this.handleResponse(response);
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
    const protocol = API_BASE_URL.startsWith('https') ? 'wss' : 'ws';
    const wsUrl = `${protocol}${API_BASE_URL.substring(API_BASE_URL.indexOf('://'))}/ws`;
    return new WebSocket(wsUrl);
  }
}

export const apiService = new ApiService();