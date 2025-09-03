import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  RefreshControl,
  Dimensions,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { useNavigation } from '@react-navigation/native';
import { StackNavigationProp } from '@react-navigation/stack';
import { RootStackParamList, SymbolData, WebSocketMessage } from '../types';
import { apiService } from '../services/api';
import { useAuth } from '../context/AuthContext';

type DashboardNavigationProp = StackNavigationProp<RootStackParamList>;

const { width } = Dimensions.get('window');

interface CryptoCard {
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

const DashboardScreen: React.FC = () => {
  const navigation = useNavigation<DashboardNavigationProp>();
  const [cryptoData, setCryptoData] = useState<{ [key: string]: CryptoCard }>({});
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<'connected' | 'disconnected'>('disconnected');
  const wsRef = useRef<WebSocket | null>(null);
  const { user } = useAuth();

  const symbols = ['BTC', 'ETH', 'XRP', 'BNB', 'ADA', 'SOL', 'DOT', 'POL', 'AVAX', 'LINK'];

  useEffect(() => {
    initializeData();
    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const initializeData = async () => {
    // Initialize with default data
    const initialData: { [key: string]: CryptoCard } = {};
    symbols.forEach(symbol => {
      const symbolConfig: { [key: string]: any } = {
        BTC: { symbol: 'BTCUSDT', display_name: 'Bitcoin', precision: 2, strategy_type: 'quality_over_quantity' },
        ETH: { symbol: 'ETHUSDT', display_name: 'Ethereum', precision: 2, strategy_type: 'trend_momentum' },
        XRP: { symbol: 'XRPUSDT', display_name: 'Ripple', precision: 4, strategy_type: 'volatility_breakout' },
        BNB: { symbol: 'BNBUSDT', display_name: 'Binance Coin', precision: 2, strategy_type: 'quality_over_quantity' },
        ADA: { symbol: 'ADAUSDT', display_name: 'Cardano', precision: 4, strategy_type: 'trend_momentum' },
        SOL: { symbol: 'SOLUSDT', display_name: 'Solana', precision: 2, strategy_type: 'volatility_breakout' },
        DOT: { symbol: 'DOTUSDT', display_name: 'Polkadot', precision: 3, strategy_type: 'signal_rich' },
        POL: { symbol: 'POLUSDT', display_name: 'Polygon', precision: 4, strategy_type: 'trend_following' },
        AVAX: { symbol: 'AVAXUSDT', display_name: 'Avalanche', precision: 3, strategy_type: 'mean_reversion' },
        LINK: { symbol: 'LINKUSDT', display_name: 'Chainlink', precision: 3, strategy_type: 'signal_rich' },
      };

      const config = symbolConfig[symbol];
      initialData[symbol] = {
        symbol,
        display_name: config.display_name,
        price: 0,
        signal: 'NEUTRAL',
        indicators: { RSI: 0, MACD: 0, BB_UPPER: 0, BB_LOWER: 0 },
        timestamp: new Date().toISOString(),
        strategy_type: config.strategy_type,
      };
    });
    setCryptoData(initialData);
  };

  const connectWebSocket = () => {
    try {
      const ws = apiService.createWebSocketConnection();
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('WebSocket connected successfully');
        setConnectionStatus('connected');
      };

      ws.onmessage = (event) => {
        try {
          console.log('WebSocket message received:', event.data);
          const message: WebSocketMessage = JSON.parse(event.data);
          handleWebSocketMessage(message);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected');
        setConnectionStatus('disconnected');
        // Attempt to reconnect after 5 seconds
        setTimeout(() => {
          console.log('Attempting to reconnect WebSocket...');
          connectWebSocket();
        }, 5000);
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setConnectionStatus('disconnected');
      };
    } catch (error) {
      console.error('Error connecting WebSocket:', error);
      setConnectionStatus('disconnected');
    }
  };

  const handleWebSocketMessage = (message: WebSocketMessage) => {
    if (message.type === 'symbol_update' && message.symbol && message.data) {
      setCryptoData(prev => ({
        ...prev,
        [message.symbol!]: {
          ...prev[message.symbol!],
          ...message.data,
        },
      }));
    }
  };

  const onRefresh = async () => {
    setIsRefreshing(true);
    try {
      await initializeData();
      if (wsRef.current?.readyState !== WebSocket.OPEN) {
        connectWebSocket();
      }
    } catch (error) {
      console.error('Error refreshing data:', error);
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleStrategyTest = (symbol: string, displayName: string) => {
    navigation.navigate('StrategyTest', { symbol, displayName });
  };

  const formatPrice = (price: number, precision: number = 2): string => {
    if (price === 0) return '$0.00';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: precision,
      maximumFractionDigits: Math.max(precision, 8),
    }).format(price);
  };

  const getSignalColor = (signal: string): string => {
    switch (signal) {
      case 'BUY': return '#10b981';
      case 'SELL': return '#ef4444';
      default: return '#6b7280';
    }
  };

  const renderCryptoCard = (symbol: string, data: CryptoCard) => (
    <View key={symbol} style={styles.cryptoCard}>
      <View style={styles.cardHeader}>
        <View>
          <Text style={styles.cryptoName}>{data.display_name} ({symbol})</Text>
          <Text style={styles.price}>{formatPrice(data.price)}</Text>
        </View>
        <View style={[styles.signalBadge, { backgroundColor: getSignalColor(data.signal) }]}>
          <Text style={styles.signalText}>{data.signal}</Text>
        </View>
      </View>

      <View style={styles.indicatorsGrid}>
        <View style={styles.indicator}>
          <Text style={styles.indicatorLabel}>RSI</Text>
          <Text style={styles.indicatorValue}>{data.indicators.RSI.toFixed(2)}</Text>
        </View>
        <View style={styles.indicator}>
          <Text style={styles.indicatorLabel}>MACD</Text>
          <Text style={styles.indicatorValue}>{data.indicators.MACD.toFixed(2)}</Text>
        </View>
        <View style={styles.indicator}>
          <Text style={styles.indicatorLabel}>BB Upper</Text>
          <Text style={styles.indicatorValue}>{data.indicators.BB_UPPER.toFixed(2)}</Text>
        </View>
        <View style={styles.indicator}>
          <Text style={styles.indicatorLabel}>BB Lower</Text>
          <Text style={styles.indicatorValue}>{data.indicators.BB_LOWER.toFixed(2)}</Text>
        </View>
      </View>

      <TouchableOpacity
        style={styles.strategyButton}
        onPress={() => handleStrategyTest(symbol, data.display_name)}
      >
        <Text style={styles.strategyButtonText}>📈 Strateji Test</Text>
      </TouchableOpacity>

      <Text style={styles.lastUpdate}>
        Son güncelleme: {new Date(data.timestamp).toLocaleTimeString('tr-TR')}
      </Text>
    </View>
  );

  return (
    <LinearGradient
      colors={['#667eea', '#764ba2']}
      style={styles.container}
    >
      <View style={styles.header}>
        <View>
          <Text style={styles.title}>🚀 Multi-Symbol Trading Dashboard</Text>
          <Text style={styles.subtitle}>Real-time cryptocurrency analysis</Text>
        </View>
        
        <View style={styles.userSection}>
          {user ? (
            <Text style={styles.userInfo}>{user.first_name} {user.last_name}</Text>
          ) : (
            <TouchableOpacity 
              style={styles.loginButton}
              onPress={() => navigation.navigate('AuthStack')}
            >
              <Text style={styles.loginButtonText}>👤 Giriş</Text>
            </TouchableOpacity>
          )}
        </View>
      </View>

      <View style={[
        styles.connectionStatus,
        { backgroundColor: connectionStatus === 'connected' ? '#10b981' : '#ef4444' }
      ]}>
        <Text style={styles.connectionText}>
          {connectionStatus === 'connected' ? '🟢 Bağlandı' : '🔴 Bağlantı Kesildi'}
        </Text>
      </View>

      <ScrollView
        style={styles.scrollView}
        refreshControl={
          <RefreshControl refreshing={isRefreshing} onRefresh={onRefresh} />
        }
      >
        <View style={styles.cryptoGrid}>
          {symbols.map(symbol => renderCryptoCard(symbol, cryptoData[symbol]))}
        </View>
      </ScrollView>
    </LinearGradient>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingTop: 60,
    paddingBottom: 20,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: 'white',
  },
  subtitle: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.8)',
    marginTop: 4,
  },
  userSection: {
    alignItems: 'flex-end',
  },
  userInfo: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
  loginButton: {
    backgroundColor: 'rgba(255,255,255,0.2)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 15,
  },
  loginButtonText: {
    color: 'white',
    fontSize: 14,
    fontWeight: '600',
  },
  connectionStatus: {
    position: 'absolute',
    top: 60,
    right: 20,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 15,
    zIndex: 10,
  },
  connectionText: {
    color: 'white',
    fontSize: 12,
    fontWeight: '600',
  },
  scrollView: {
    flex: 1,
    paddingHorizontal: 20,
  },
  cryptoGrid: {
    paddingBottom: 20,
  },
  cryptoCard: {
    backgroundColor: 'rgba(255, 255, 255, 0.95)',
    borderRadius: 15,
    padding: 20,
    marginBottom: 15,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 5,
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
  },
  cryptoName: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
  },
  price: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#2563eb',
    marginTop: 4,
  },
  signalBadge: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 15,
  },
  signalText: {
    color: 'white',
    fontSize: 12,
    fontWeight: '600',
  },
  indicatorsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    marginBottom: 15,
  },
  indicator: {
    backgroundColor: '#f8fafc',
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderRadius: 10,
    width: '48%',
    marginBottom: 8,
    alignItems: 'center',
  },
  indicatorLabel: {
    fontSize: 12,
    color: '#64748b',
    marginBottom: 4,
  },
  indicatorValue: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1e293b',
  },
  strategyButton: {
    backgroundColor: '#667eea',
    borderRadius: 10,
    paddingVertical: 12,
    alignItems: 'center',
    marginBottom: 10,
  },
  strategyButtonText: {
    color: 'white',
    fontSize: 14,
    fontWeight: '600',
  },
  lastUpdate: {
    fontSize: 12,
    color: '#64748b',
    textAlign: 'center',
  },
});

export default DashboardScreen;