import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  RefreshControl,
  Modal,
  TextInput,
  Alert,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { useAuth } from '../context/AuthContext';
import { useNavigation, useFocusEffect } from '@react-navigation/native';
import { StackNavigationProp } from '@react-navigation/stack';
import { RootStackParamList } from '../types';
import { apiService } from '../services/api';

type StrategiesNavigationProp = StackNavigationProp<RootStackParamList>;

interface Strategy {
  id: string;
  name: string;
  description: string;
  type: 'general' | 'custom';
  symbol?: string;
  performance?: {
    totalReturn: number;
    winRate: number;
    maxDrawdown: number;
  };
  isActive: boolean;
  createdAt: string;
}

interface StrategyTemplate {
  id: string;
  name: string;
  description: string;
  emoji: string;
  difficulty: 'Kolay' | 'Orta' | 'İleri';
  timeframe: string;
}

const StrategiesScreen: React.FC = () => {
  const { user } = useAuth();
  const navigation = useNavigation<StrategiesNavigationProp>();
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<StrategyTemplate | null>(null);
  const [strategyName, setStrategyName] = useState('');
  const [strategyDescription, setStrategyDescription] = useState('');
  const [selectedAsset, setSelectedAsset] = useState('BTCUSDT');

  const strategyTemplates: StrategyTemplate[] = [
    {
      id: 'bb_macd',
      name: 'Bollinger Bands + MACD',
      description: 'BB bantları ve MACD sinyallerini kombine eden klasik strateji',
      emoji: '📊',
      difficulty: 'Kolay',
      timeframe: '5m-15m'
    },
    {
      id: 'rsi_ema',
      name: 'RSI + EMA Crossover',
      description: 'RSI momentum ve EMA trend takibi kombinasyonu',
      emoji: '📈',
      difficulty: 'Orta',
      timeframe: '15m-1h'
    },
    {
      id: 'volume_breakout',
      name: 'Volume Breakout',
      description: 'Hacim artışı ile desteklenen fiyat kırılımları',
      emoji: '🚀',
      difficulty: 'İleri',
      timeframe: '1h-4h'
    },
    {
      id: 'trend_following',
      name: 'Trend Following',
      description: 'Uzun vadeli trend takip stratejisi',
      emoji: '📍',
      difficulty: 'Orta',
      timeframe: '4h-1d'
    },
  ];

  const assets = [
    { symbol: 'BTCUSDT', name: 'Bitcoin', emoji: '₿' },
    { symbol: 'ETHUSDT', name: 'Ethereum', emoji: '⟠' },
    { symbol: 'BNBUSDT', name: 'Binance Coin', emoji: '🟡' },
    { symbol: 'XRPUSDT', name: 'XRP', emoji: '💧' },
    { symbol: 'ADAUSDT', name: 'Cardano', emoji: '🔷' },
    { symbol: 'SOLUSDT', name: 'Solana', emoji: '🌟' },
    { symbol: 'DOTUSDT', name: 'Polkadot', emoji: '🔴' },
    { symbol: 'POLUSDT', name: 'Polygon', emoji: '🟣' },
    { symbol: 'AVAXUSDT', name: 'Avalanche', emoji: '🔺' },
    { symbol: 'LINKUSDT', name: 'Chainlink', emoji: '🔗' },
  ];

  // Mock data for existing strategies
  const mockStrategies: Strategy[] = [
    {
      id: '1',
      name: 'Bitcoin BB-MACD',
      description: 'Bollinger Bands ve MACD kombinasyonu ile BTC ticareti',
      type: 'custom',
      symbol: 'BTCUSDT',
      performance: {
        totalReturn: 23.5,
        winRate: 68.2,
        maxDrawdown: -8.1
      },
      isActive: true,
      createdAt: '2025-01-08T10:30:00Z'
    },
    {
      id: '2', 
      name: 'ETH Trend Follower',
      description: 'Ethereum için trend takip stratejisi',
      type: 'custom',
      symbol: 'ETHUSDT',
      performance: {
        totalReturn: 15.8,
        winRate: 71.4,
        maxDrawdown: -12.3
      },
      isActive: false,
      createdAt: '2025-01-07T14:15:00Z'
    }
  ];

  // Load strategies on component mount
  useEffect(() => {
    loadStrategies();
  }, [user]);

  // Refresh strategies when screen comes into focus (e.g., after creating a new strategy)
  useFocusEffect(
    useCallback(() => {
      if (user) {
        loadStrategies();
      }
    }, [user])
  );

  const loadStrategies = async () => {
    if (!user) {
      setStrategies([]);
      return;
    }

    try {
      const result = await apiService.getUserStrategies();
      if (result.success && result.data) {
        // Convert API response to Strategy interface format
        const apiStrategies = result.data.map((strategy: any) => ({
          id: strategy.id,
          name: strategy.name,
          description: strategy.description || 'Açıklama yok',
          type: 'custom' as const,
          isActive: strategy.is_active,
          createdAt: strategy.created_at,
          performance: {
            totalReturn: Math.random() * 20 - 5, // Mock performance data
            winRate: Math.random() * 40 + 50,
            maxDrawdown: Math.random() * 10 + 5
          }
        }));
        setStrategies(apiStrategies);
      } else {
        console.error('Failed to load strategies:', result.message);
        setStrategies([]);
      }
    } catch (error) {
      console.error('Error loading strategies:', error);
      setStrategies([]);
    }
  };

  const onRefresh = async () => {
    setIsRefreshing(true);
    await loadStrategies();
    setIsRefreshing(false);
  };

  const handleCreateStrategy = () => {
    if (!user) {
      Alert.alert('Giriş Gerekli', 'Strateji oluşturmak için giriş yapmalısınız.');
      return;
    }
    setShowCreateModal(true);
  };

  const handleTemplateSelect = (template: StrategyTemplate) => {
    setSelectedTemplate(template);
    setStrategyName(`${template.name} - ${assets.find(a => a.symbol === selectedAsset)?.name}`);
    setStrategyDescription(template.description);
  };

  const handleStrategySubmit = () => {
    if (!strategyName.trim()) {
      Alert.alert('Hata', 'Lütfen strateji adı girin.');
      return;
    }

    // Navigate to strategy test screen with parameters
    const selectedAssetData = assets.find(a => a.symbol === selectedAsset);
    navigation.navigate('StrategyTest', {
      symbol: selectedAsset,
      displayName: selectedAssetData?.name || 'Kripto Para',
    });

    setShowCreateModal(false);
    resetModal();
  };

  const resetModal = () => {
    setSelectedTemplate(null);
    setStrategyName('');
    setStrategyDescription('');
    setSelectedAsset('BTCUSDT');
  };

  const handleStrategyTest = (strategy: Strategy) => {
    if (strategy.symbol) {
      const asset = assets.find(a => a.symbol === strategy.symbol);
      navigation.navigate('StrategyTest', {
        symbol: strategy.symbol,
        displayName: asset?.name || 'Kripto Para',
      });
    }
  };

  const getPerformanceColor = (value: number) => {
    if (value > 0) return '#10b981';
    if (value < -10) return '#ef4444';
    return '#f59e0b';
  };

  const renderStrategyCard = (strategy: Strategy) => (
    <View key={strategy.id} style={styles.strategyCard}>
      <View style={styles.strategyHeader}>
        <View>
          <Text style={styles.strategyName}>{strategy.name}</Text>
          <Text style={styles.strategyDescription}>{strategy.description}</Text>
          {strategy.symbol && (
            <Text style={styles.strategySymbol}>
              {assets.find(a => a.symbol === strategy.symbol)?.emoji} {strategy.symbol}
            </Text>
          )}
        </View>
        <View style={[
          styles.statusBadge,
          { backgroundColor: strategy.isActive ? '#10b981' : '#6b7280' }
        ]}>
          <Text style={styles.statusText}>
            {strategy.isActive ? 'Aktif' : 'Pasif'}
          </Text>
        </View>
      </View>

      {strategy.performance && (
        <View style={styles.performanceSection}>
          <View style={styles.performanceGrid}>
            <View style={styles.performanceItem}>
              <Text style={styles.performanceLabel}>Toplam Getiri</Text>
              <Text style={[
                styles.performanceValue,
                { color: getPerformanceColor(strategy.performance.totalReturn) }
              ]}>
                {strategy.performance.totalReturn > 0 ? '+' : ''}{strategy.performance.totalReturn.toFixed(1)}%
              </Text>
            </View>
            <View style={styles.performanceItem}>
              <Text style={styles.performanceLabel}>Kazanç Oranı</Text>
              <Text style={styles.performanceValue}>
                {strategy.performance.winRate.toFixed(1)}%
              </Text>
            </View>
            <View style={styles.performanceItem}>
              <Text style={styles.performanceLabel}>Max Düşüş</Text>
              <Text style={[
                styles.performanceValue,
                { color: getPerformanceColor(strategy.performance.maxDrawdown) }
              ]}>
                {strategy.performance.maxDrawdown.toFixed(1)}%
              </Text>
            </View>
          </View>
        </View>
      )}

      <View style={styles.strategyActions}>
        <TouchableOpacity
          style={styles.testButton}
          onPress={() => handleStrategyTest(strategy)}
        >
          <Text style={styles.testButtonText}>🧪 Test Et</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[
            styles.toggleButton,
            { backgroundColor: strategy.isActive ? '#ef4444' : '#10b981' }
          ]}
        >
          <Text style={styles.toggleButtonText}>
            {strategy.isActive ? '⏸ Durdur' : '▶️ Başlat'}
          </Text>
        </TouchableOpacity>
      </View>
    </View>
  );

  const renderTemplateCard = (template: StrategyTemplate) => (
    <TouchableOpacity
      key={template.id}
      style={[
        styles.templateCard,
        selectedTemplate?.id === template.id && styles.templateCardSelected
      ]}
      onPress={() => handleTemplateSelect(template)}
    >
      <View style={styles.templateHeader}>
        <Text style={styles.templateEmoji}>{template.emoji}</Text>
        <View style={styles.difficultyBadge}>
          <Text style={styles.difficultyText}>{template.difficulty}</Text>
        </View>
      </View>
      <Text style={styles.templateName}>{template.name}</Text>
      <Text style={styles.templateDescription}>{template.description}</Text>
      <Text style={styles.templateTimeframe}>⏱ {template.timeframe}</Text>
    </TouchableOpacity>
  );

  return (
    <LinearGradient
      colors={['#667eea', '#764ba2']}
      style={styles.container}
    >
      <View style={styles.header}>
        <View>
          <Text style={styles.title}>📈 Stratejilerim</Text>
          <Text style={styles.subtitle}>Trading stratejileri ve performans</Text>
        </View>
        
        <View style={styles.userSection}>
          {user ? (
            <TouchableOpacity 
              style={styles.profileButton}
              onPress={() => navigation.navigate('MainTabs', { screen: 'Profile' })}
            >
              <Text style={styles.profileButtonText}>👤 {user.first_name}</Text>
            </TouchableOpacity>
          ) : (
            <TouchableOpacity 
              style={styles.loginButton}
              onPress={() => navigation.navigate('AuthStack', { screen: 'Login', params: { returnTo: 'Strategies' } })}
            >
              <Text style={styles.loginButtonText}>👤 Giriş</Text>
            </TouchableOpacity>
          )}
        </View>
      </View>

      <ScrollView
        style={styles.scrollView}
        refreshControl={
          <RefreshControl refreshing={isRefreshing} onRefresh={onRefresh} tintColor="white" />
        }
        showsVerticalScrollIndicator={false}
      >
        {/* Create New Strategy Button */}
        <TouchableOpacity
          style={styles.createButton}
          onPress={handleCreateStrategy}
        >
          <Text style={styles.createButtonText}>➕ Yeni Strateji Oluştur</Text>
        </TouchableOpacity>

        {/* Custom Strategies Section */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Özel Stratejilerim</Text>
          {strategies.length === 0 ? (
            <View style={styles.emptyState}>
              <Text style={styles.emptyText}>
                Henüz özel stratejiniz yok.{'\n'}Yukarıdaki butona tıklayarak ilk stratejinizi oluşturun!
              </Text>
            </View>
          ) : (
            strategies.map(renderStrategyCard)
          )}
        </View>

        {/* General Strategies Section */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Genel Stratejiler</Text>
          <Text style={styles.sectionSubtitle}>Hazır şablonlar ile hızla başlayın</Text>
          
          {strategyTemplates.map((template) => (
            <View key={template.id} style={styles.strategyCard}>
              <View style={styles.strategyHeader}>
                <View>
                  <Text style={styles.strategyName}>
                    {template.emoji} {template.name}
                  </Text>
                  <Text style={styles.strategyDescription}>{template.description}</Text>
                </View>
                <View style={styles.difficultyBadge}>
                  <Text style={styles.difficultyText}>{template.difficulty}</Text>
                </View>
              </View>
              
              <View style={styles.templateInfo}>
                <Text style={styles.templateTimeframe}>⏱ Zaman: {template.timeframe}</Text>
              </View>

              <TouchableOpacity
                style={styles.useTemplateButton}
                onPress={() => {
                  setSelectedTemplate(template);
                  handleCreateStrategy();
                }}
              >
                <Text style={styles.useTemplateButtonText}>🚀 Bu Şablonu Kullan</Text>
              </TouchableOpacity>
            </View>
          ))}
        </View>
      </ScrollView>

      {/* Create Strategy Modal */}
      <Modal
        visible={showCreateModal}
        animationType="slide"
        presentationStyle="pageSheet"
        onRequestClose={() => {
          setShowCreateModal(false);
          resetModal();
        }}
      >
        <View style={styles.modalContainer}>
          <View style={styles.modalHeader}>
            <TouchableOpacity
              onPress={() => {
                setShowCreateModal(false);
                resetModal();
              }}
            >
              <Text style={styles.modalCloseButton}>✕</Text>
            </TouchableOpacity>
            <Text style={styles.modalTitle}>Yeni Strateji</Text>
            <View style={{ width: 24 }} />
          </View>

          <ScrollView style={styles.modalContent}>
            {!selectedTemplate && (
              <View>
                <Text style={styles.modalSectionTitle}>Strateji Şablonu Seçin</Text>
                <View style={styles.templatesGrid}>
                  {strategyTemplates.map(renderTemplateCard)}
                </View>
              </View>
            )}

            {selectedTemplate && (
              <View>
                <Text style={styles.modalSectionTitle}>Strateji Detayları</Text>
                
                <View style={styles.inputGroup}>
                  <Text style={styles.inputLabel}>Varlık Seçin</Text>
                  <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.assetSelector}>
                    {assets.map((asset) => (
                      <TouchableOpacity
                        key={asset.symbol}
                        style={[
                          styles.assetItem,
                          selectedAsset === asset.symbol && styles.assetItemSelected
                        ]}
                        onPress={() => setSelectedAsset(asset.symbol)}
                      >
                        <Text style={styles.assetEmoji}>{asset.emoji}</Text>
                        <Text style={[
                          styles.assetName,
                          selectedAsset === asset.symbol && styles.assetNameSelected
                        ]}>
                          {asset.name}
                        </Text>
                      </TouchableOpacity>
                    ))}
                  </ScrollView>
                </View>

                <View style={styles.inputGroup}>
                  <Text style={styles.inputLabel}>Strateji Adı</Text>
                  <TextInput
                    style={styles.textInput}
                    value={strategyName}
                    onChangeText={setStrategyName}
                    placeholder="Stratejinize bir ad verin"
                    placeholderTextColor="#999"
                  />
                </View>

                <View style={styles.inputGroup}>
                  <Text style={styles.inputLabel}>Açıklama (Opsiyonel)</Text>
                  <TextInput
                    style={[styles.textInput, styles.textArea]}
                    value={strategyDescription}
                    onChangeText={setStrategyDescription}
                    placeholder="Strateji hakkında kısa açıklama"
                    placeholderTextColor="#999"
                    multiline
                    numberOfLines={3}
                  />
                </View>

                <TouchableOpacity
                  style={styles.submitButton}
                  onPress={handleStrategySubmit}
                >
                  <Text style={styles.submitButtonText}>🚀 Stratejiyi Test Et</Text>
                </TouchableOpacity>
              </View>
            )}
          </ScrollView>
        </View>
      </Modal>

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
    fontSize: 28,
    fontWeight: 'bold',
    color: 'white',
  },
  subtitle: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.8)',
    marginTop: 4,
  },
  scrollView: {
    flex: 1,
    paddingHorizontal: 20,
  },
  createButton: {
    backgroundColor: 'rgba(255,255,255,0.9)',
    borderRadius: 15,
    padding: 16,
    alignItems: 'center',
    marginBottom: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  createButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#667eea',
  },
  section: {
    marginBottom: 30,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: 'white',
    marginBottom: 5,
  },
  sectionSubtitle: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.7)',
    marginBottom: 15,
  },
  strategyCard: {
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
  strategyHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 15,
  },
  strategyName: {
    fontSize: 18,
    fontWeight: '700',
    color: '#333',
    marginBottom: 4,
  },
  strategyDescription: {
    fontSize: 14,
    color: '#666',
    lineHeight: 20,
    marginBottom: 8,
  },
  strategySymbol: {
    fontSize: 12,
    color: '#888',
    fontWeight: '500',
  },
  statusBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
  },
  statusText: {
    color: 'white',
    fontSize: 12,
    fontWeight: '600',
  },
  performanceSection: {
    marginBottom: 15,
    padding: 12,
    backgroundColor: '#f8fafc',
    borderRadius: 10,
  },
  performanceGrid: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  performanceItem: {
    alignItems: 'center',
    flex: 1,
  },
  performanceLabel: {
    fontSize: 10,
    color: '#666',
    marginBottom: 4,
  },
  performanceValue: {
    fontSize: 16,
    fontWeight: '700',
    color: '#333',
  },
  strategyActions: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: 10,
  },
  testButton: {
    flex: 1,
    backgroundColor: '#667eea',
    borderRadius: 10,
    padding: 12,
    alignItems: 'center',
  },
  testButtonText: {
    color: 'white',
    fontSize: 14,
    fontWeight: '600',
  },
  toggleButton: {
    flex: 1,
    borderRadius: 10,
    padding: 12,
    alignItems: 'center',
  },
  toggleButtonText: {
    color: 'white',
    fontSize: 14,
    fontWeight: '600',
  },
  emptyState: {
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
    borderRadius: 15,
    padding: 30,
    alignItems: 'center',
  },
  emptyText: {
    fontSize: 16,
    color: '#666',
    textAlign: 'center',
    lineHeight: 24,
  },
  templateInfo: {
    marginBottom: 12,
  },
  templateTimeframe: {
    fontSize: 12,
    color: '#888',
  },
  useTemplateButton: {
    backgroundColor: '#10b981',
    borderRadius: 10,
    padding: 12,
    alignItems: 'center',
  },
  useTemplateButtonText: {
    color: 'white',
    fontSize: 14,
    fontWeight: '600',
  },
  difficultyBadge: {
    backgroundColor: '#f59e0b',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
  },
  difficultyText: {
    color: 'white',
    fontSize: 12,
    fontWeight: '600',
  },
  // Modal Styles
  modalContainer: {
    flex: 1,
    backgroundColor: 'white',
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    paddingTop: 60,
    backgroundColor: '#f8fafc',
    borderBottomWidth: 1,
    borderBottomColor: '#e5e7eb',
  },
  modalCloseButton: {
    fontSize: 24,
    color: '#666',
    fontWeight: '600',
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#333',
  },
  modalContent: {
    flex: 1,
    padding: 20,
  },
  modalSectionTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#333',
    marginBottom: 15,
  },
  templatesGrid: {
    gap: 10,
    marginBottom: 20,
  },
  templateCard: {
    backgroundColor: '#f8fafc',
    borderRadius: 12,
    padding: 16,
    borderWidth: 2,
    borderColor: 'transparent',
  },
  templateCardSelected: {
    borderColor: '#667eea',
    backgroundColor: '#f0f4ff',
  },
  templateHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  templateEmoji: {
    fontSize: 24,
  },
  templateName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginBottom: 4,
  },
  inputGroup: {
    marginBottom: 20,
  },
  inputLabel: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginBottom: 8,
  },
  textInput: {
    backgroundColor: '#f8fafc',
    borderRadius: 10,
    padding: 12,
    fontSize: 16,
    color: '#333',
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  textArea: {
    height: 80,
    textAlignVertical: 'top',
  },
  assetSelector: {
    maxHeight: 80,
  },
  assetItem: {
    backgroundColor: '#f8fafc',
    borderRadius: 10,
    padding: 12,
    marginRight: 10,
    alignItems: 'center',
    minWidth: 80,
    borderWidth: 2,
    borderColor: 'transparent',
  },
  assetItemSelected: {
    borderColor: '#667eea',
    backgroundColor: '#f0f4ff',
  },
  assetEmoji: {
    fontSize: 20,
    marginBottom: 4,
  },
  assetName: {
    fontSize: 12,
    color: '#666',
    textAlign: 'center',
  },
  assetNameSelected: {
    color: '#667eea',
    fontWeight: '600',
  },
  submitButton: {
    backgroundColor: '#667eea',
    borderRadius: 15,
    padding: 16,
    alignItems: 'center',
    marginTop: 10,
  },
  submitButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
  userSection: {
    alignItems: 'flex-end',
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
  profileButton: {
    backgroundColor: 'rgba(255,255,255,0.2)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 15,
  },
  profileButtonText: {
    color: 'white',
    fontSize: 14,
    fontWeight: '600',
  },
});

export default StrategiesScreen;