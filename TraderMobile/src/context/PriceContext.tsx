import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import Constants from 'expo-constants';

interface PriceData {
  [symbol: string]: {
    price: number;
    change: number;
    timestamp: string;
  };
}

interface PriceContextType {
  prices: PriceData;
  isConnected: boolean;
  getPrice: (symbol: string) => { price: number; change: number } | null;
}

const PriceContext = createContext<PriceContextType>({
  prices: {},
  isConnected: false,
  getPrice: () => null,
});

export const usePrices = () => useContext(PriceContext);

interface PriceProviderProps {
  children: ReactNode;
}

export const PriceProvider: React.FC<PriceProviderProps> = ({ children }) => {
  const [prices, setPrices] = useState<PriceData>({});
  const [isConnected, setIsConnected] = useState(false);
  const [ws, setWs] = useState<WebSocket | null>(null);

  const WS_BASE_URL = Constants.expoConfig?.extra?.WS_BASE_URL || 'ws://localhost:8000/ws';

  useEffect(() => {
    let websocket: WebSocket | null = null;
    let reconnectTimer: NodeJS.Timeout | null = null;
    let pingInterval: NodeJS.Timeout | null = null;

    const connect = () => {
      try {
        console.log('Connecting to dashboard WebSocket:', WS_BASE_URL);
        websocket = new WebSocket(WS_BASE_URL);

        websocket.onopen = () => {
          console.log('Connected to dashboard WebSocket');
          setIsConnected(true);
          
          // Send ping every 30 seconds to keep connection alive
          pingInterval = setInterval(() => {
            if (websocket?.readyState === WebSocket.OPEN) {
              websocket.send(JSON.stringify({ type: 'ping' }));
              console.log('Sent WebSocket ping');
            }
          }, 30000);
        };

        websocket.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            console.log('Received WebSocket message:', data);
            
            // Handle the actual message format from multi_symbol_dashboard
            if (data.type === 'symbol_update' && data.symbol && data.data) {
              const symbol = data.symbol; // Already clean symbol key (BTC, ETH, etc.)
              const messageData = data.data;
              
              if (symbol && messageData.price) {
                console.log(`Updating price for ${symbol}: $${messageData.price}`);
                setPrices(prev => ({
                  ...prev,
                  [symbol]: {
                    price: messageData.price,
                    change: messageData.change || 0,
                    timestamp: messageData.timestamp || new Date().toISOString(),
                  }
                }));
              }
            }
            
            // Legacy format support (if needed)
            if (data.type === 'price_update' || data.type === 'signal_update') {
              const symbol = data.symbol?.replace('USDT', '') || '';
              if (symbol && data.price) {
                setPrices(prev => ({
                  ...prev,
                  [symbol]: {
                    price: data.price,
                    change: data.change || 0,
                    timestamp: data.timestamp || new Date().toISOString(),
                  }
                }));
              }
            }
            
            // Handle batch updates
            if (data.type === 'multi_symbol_update' && data.symbols) {
              const updates: PriceData = {};
              Object.keys(data.symbols).forEach(symbol => {
                const symbolData = data.symbols[symbol];
                if (symbolData.price) {
                  updates[symbol] = {
                    price: symbolData.price,
                    change: symbolData.change || 0,
                    timestamp: symbolData.timestamp || new Date().toISOString(),
                  };
                }
              });
              setPrices(prev => ({ ...prev, ...updates }));
            }
          } catch (error) {
            console.warn('Error parsing WebSocket message:', error);
          }
        };

        websocket.onclose = (event) => {
          console.log('Dashboard WebSocket closed:', event.code, event.reason);
          setIsConnected(false);
          
          if (pingInterval) {
            clearInterval(pingInterval);
            pingInterval = null;
          }
          
          // Attempt to reconnect after 5 seconds
          if (!reconnectTimer) {
            reconnectTimer = setTimeout(() => {
              reconnectTimer = null;
              connect();
            }, 5000);
          }
        };

        websocket.onerror = (error) => {
          console.error('Dashboard WebSocket error:', error);
          setIsConnected(false);
        };

        setWs(websocket);
      } catch (error) {
        console.error('Failed to create WebSocket connection:', error);
        // Retry connection after 5 seconds
        if (!reconnectTimer) {
          reconnectTimer = setTimeout(() => {
            reconnectTimer = null;
            connect();
          }, 5000);
        }
      }
    };

    connect();

    return () => {
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
      }
      if (pingInterval) {
        clearInterval(pingInterval);
      }
      if (websocket) {
        websocket.close();
      }
    };
  }, [WS_BASE_URL]);

  const getPrice = (symbol: string): { price: number; change: number } | null => {
    // Remove USDT suffix if present to match our price data keys
    const cleanSymbol = symbol.replace('USDT', '');
    const priceData = prices[cleanSymbol];
    
    console.log(`Looking for price data for symbol: "${symbol}" -> cleaned: "${cleanSymbol}"`);
    console.log('Available price data:', Object.keys(prices));
    console.log(`Price data for ${cleanSymbol}:`, priceData);
    
    if (priceData) {
      return {
        price: priceData.price,
        change: priceData.change,
      };
    }
    
    return null;
  };

  return (
    <PriceContext.Provider value={{ prices, isConnected, getPrice }}>
      {children}
    </PriceContext.Provider>
  );
};