import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { RouteProp, useRoute, useNavigation } from '@react-navigation/native';
import { StackNavigationProp } from '@react-navigation/stack';
import { RootStackParamList, BacktestResult, StrategyConfig } from '../types';
import { apiService } from '../services/api';
import { useAuth } from '../context/AuthContext';

type StrategyTestRouteProp = RouteProp<RootStackParamList, 'StrategyTest'>;
type StrategyTestNavigationProp = StackNavigationProp<RootStackParamList, 'StrategyTest'>;

const StrategyTestScreen: React.FC = () => {
  const route = useRoute<StrategyTestRouteProp>();
  const navigation = useNavigation<StrategyTestNavigationProp>();
  const { symbol, displayName } = route.params;

  const [strategyName, setStrategyName] = useState(`${displayName} Strategy`);
  const [description, setDescription] = useState('');
  const [parameters, setParameters] = useState({
    bb_period: '20',
    bb_std: '2.0',
    macd_fast: '12',
    macd_slow: '26',
    macd_signal: '9',
    rsi_period: '14',
    rsi_overbought: '70',
    rsi_oversold: '30',
    position_size: '0.1',
    stop_loss: '0.02',
    take_profit: '0.04',
  });
  
  const [isLoading, setIsLoading] = useState(false);
  const [backtestResult, setBacktestResult] = useState<BacktestResult | null>(null);

  const handleParameterChange = (key: string, value: string) => {
    setParameters(prev => ({ ...prev, [key]: value }));
  };

  const validateParameters = (): boolean => {
    const requiredParams = ['bb_period', 'bb_std', 'macd_fast', 'macd_slow', 'macd_signal', 'rsi_period'];
    
    for (const param of requiredParams) {
      const value = parameters[param as keyof typeof parameters];
      if (!value || isNaN(Number(value)) || Number(value) <= 0) {
        Alert.alert('Hata', `${param} geçerli bir sayı olmalıdır.`);
        return false;
      }
    }

    if (Number(parameters.macd_fast) >= Number(parameters.macd_slow)) {
      Alert.alert('Hata', 'MACD hızlı periyot, yavaş periyottan küçük olmalıdır.');
      return false;
    }

    return true;
  };

  const handleTestStrategy = async () => {
    if (!validateParameters()) return;

    setIsLoading(true);
    try {
      // For demo purposes - simulate backtest results
      // In production, this would call the API
      const mockResult: BacktestResult = {
        total_return: Math.random() * 0.4 - 0.1, // -10% to +30%
        sharpe_ratio: Math.random() * 2 + 0.5, // 0.5 to 2.5
        max_drawdown: Math.random() * 0.3, // 0% to 30%
        win_rate: Math.random() * 0.4 + 0.5, // 50% to 90%
        total_trades: Math.floor(Math.random() * 100) + 20, // 20 to 120
        start_date: '2024-01-01',
        end_date: '2024-12-31',
        final_portfolio_value: 10000 + Math.random() * 5000,
        equity_curve: []
      };

      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      setBacktestResult(mockResult);

    } catch (error) {
      console.error('Strategy test error:', error);
      Alert.alert('Hata', 'Strateji testi sırasında bir hata oluştu.');
    } finally {
      setIsLoading(false);
    }
  };

  const { user } = useAuth();

  const handleSaveStrategy = async () => {
    if (!backtestResult) return;
    
    if (!user) {
      Alert.alert(
        'Giriş Gerekli',
        'Strateji kaydetmek için giriş yapmanız gerekiyor.',
        [
          { text: 'İptal', style: 'cancel' },
          {
            text: 'Giriş Yap',
            onPress: () => navigation.navigate('AuthStack'),
          },
        ]
      );
      return;
    }

    Alert.alert(
      'Strateji Kaydet',
      'Bu stratejiyi aktif hale getirmek istiyor musunuz?',
      [
        { text: 'İptal', style: 'cancel' },
        {
          text: 'Kaydet ve Aktifleştir',
          onPress: async () => {
            try {
              // In a real implementation, you'd call the API
              Alert.alert(
                'Başarılı',
                'Strateji kaydedildi ve aktifleştirildi.',
                [{ text: 'Tamam', onPress: () => navigation.goBack() }]
              );
            } catch (error) {
              Alert.alert('Hata', 'Strateji kaydedilirken bir hata oluştu.');
            }
          },
        },
      ]
    );
  };

  const renderParameterInput = (key: string, label: string, placeholder: string) => (
    <View key={key} style={styles.inputContainer}>
      <Text style={styles.inputLabel}>{label}</Text>
      <TextInput
        style={styles.input}
        value={parameters[key as keyof typeof parameters]}
        onChangeText={(value) => handleParameterChange(key, value)}
        placeholder={placeholder}
        placeholderTextColor="#999"
        keyboardType="numeric"
      />
    </View>
  );

  const renderBacktestResult = () => {
    if (!backtestResult) return null;

    return (
      <View style={styles.resultContainer}>
        <Text style={styles.resultTitle}>📊 Backtest Sonuçları</Text>
        
        <View style={styles.resultGrid}>
          <View style={styles.resultCard}>
            <Text style={styles.resultLabel}>Toplam Getiri</Text>
            <Text style={[styles.resultValue, { color: backtestResult.total_return >= 0 ? '#10b981' : '#ef4444' }]}>
              {(backtestResult.total_return * 100).toFixed(2)}%
            </Text>
          </View>
          
          <View style={styles.resultCard}>
            <Text style={styles.resultLabel}>Sharpe Ratio</Text>
            <Text style={styles.resultValue}>{backtestResult.sharpe_ratio.toFixed(2)}</Text>
          </View>
          
          <View style={styles.resultCard}>
            <Text style={styles.resultLabel}>Maksimum Düşüş</Text>
            <Text style={[styles.resultValue, { color: '#ef4444' }]}>
              {(backtestResult.max_drawdown * 100).toFixed(2)}%
            </Text>
          </View>
          
          <View style={styles.resultCard}>
            <Text style={styles.resultLabel}>Kazanma Oranı</Text>
            <Text style={styles.resultValue}>{(backtestResult.win_rate * 100).toFixed(1)}%</Text>
          </View>
          
          <View style={styles.resultCard}>
            <Text style={styles.resultLabel}>Toplam İşlem</Text>
            <Text style={styles.resultValue}>{backtestResult.total_trades}</Text>
          </View>
          
          <View style={styles.resultCard}>
            <Text style={styles.resultLabel}>Final Değer</Text>
            <Text style={styles.resultValue}>
              ${backtestResult.final_portfolio_value.toLocaleString()}
            </Text>
          </View>
        </View>

        <TouchableOpacity style={styles.saveButton} onPress={handleSaveStrategy}>
          <Text style={styles.saveButtonText}>💾 Stratejiyi Kaydet ve Aktifleştir</Text>
        </TouchableOpacity>
      </View>
    );
  };

  return (
    <LinearGradient
      colors={['#667eea', '#764ba2']}
      style={styles.container}
    >
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backButton}>
          <Text style={styles.backButtonText}>← Geri</Text>
        </TouchableOpacity>
        <Text style={styles.title}>{displayName} Strateji Test</Text>
      </View>

      <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
        <View style={styles.formContainer}>
          <Text style={styles.sectionTitle}>Strateji Bilgileri</Text>
          
          <View style={styles.inputContainer}>
            <Text style={styles.inputLabel}>Strateji Adı</Text>
            <TextInput
              style={styles.input}
              value={strategyName}
              onChangeText={setStrategyName}
              placeholder="Strateji adını giriniz"
              placeholderTextColor="#999"
            />
          </View>

          <View style={styles.inputContainer}>
            <Text style={styles.inputLabel}>Açıklama</Text>
            <TextInput
              style={[styles.input, styles.textArea]}
              value={description}
              onChangeText={setDescription}
              placeholder="Strateji açıklaması (opsiyonel)"
              placeholderTextColor="#999"
              multiline
              numberOfLines={3}
            />
          </View>

          <Text style={styles.sectionTitle}>Teknik İndikatör Parametreleri</Text>

          <View style={styles.parameterGrid}>
            {renderParameterInput('bb_period', 'Bollinger Bands Periyot', '20')}
            {renderParameterInput('bb_std', 'Bollinger Bands Standart Sapma', '2.0')}
            {renderParameterInput('macd_fast', 'MACD Hızlı Periyot', '12')}
            {renderParameterInput('macd_slow', 'MACD Yavaş Periyot', '26')}
            {renderParameterInput('macd_signal', 'MACD Sinyal Periyot', '9')}
            {renderParameterInput('rsi_period', 'RSI Periyot', '14')}
            {renderParameterInput('rsi_overbought', 'RSI Aşırı Alım', '70')}
            {renderParameterInput('rsi_oversold', 'RSI Aşırı Satım', '30')}
          </View>

          <Text style={styles.sectionTitle}>Risk Yönetimi</Text>
          
          <View style={styles.parameterGrid}>
            {renderParameterInput('position_size', 'Pozisyon Büyüklüğü', '0.1')}
            {renderParameterInput('stop_loss', 'Stop Loss (%)', '2')}
            {renderParameterInput('take_profit', 'Take Profit (%)', '4')}
          </View>

          <TouchableOpacity
            style={[styles.testButton, isLoading && styles.disabledButton]}
            onPress={handleTestStrategy}
            disabled={isLoading}
          >
            {isLoading ? (
              <ActivityIndicator color="white" />
            ) : (
              <Text style={styles.testButtonText}>🧪 Stratejiyi Test Et</Text>
            )}
          </TouchableOpacity>

          {renderBacktestResult()}
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
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingTop: 60,
    paddingBottom: 20,
  },
  backButton: {
    marginRight: 15,
  },
  backButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
  title: {
    color: 'white',
    fontSize: 20,
    fontWeight: 'bold',
  },
  content: {
    flex: 1,
    paddingHorizontal: 20,
  },
  formContainer: {
    backgroundColor: 'rgba(255, 255, 255, 0.95)',
    borderRadius: 20,
    padding: 25,
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 15,
    marginTop: 10,
  },
  inputContainer: {
    marginBottom: 15,
  },
  inputLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    marginBottom: 8,
  },
  input: {
    backgroundColor: '#f8fafc',
    borderRadius: 12,
    padding: 12,
    fontSize: 16,
    borderWidth: 1,
    borderColor: '#e2e8f0',
  },
  textArea: {
    height: 80,
    textAlignVertical: 'top',
  },
  parameterGrid: {
    marginBottom: 20,
  },
  testButton: {
    backgroundColor: '#667eea',
    borderRadius: 12,
    padding: 15,
    alignItems: 'center',
    marginTop: 20,
  },
  disabledButton: {
    backgroundColor: '#ccc',
  },
  testButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
  resultContainer: {
    marginTop: 30,
    paddingTop: 20,
    borderTopWidth: 1,
    borderTopColor: '#e2e8f0',
  },
  resultTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 20,
    textAlign: 'center',
  },
  resultGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    marginBottom: 20,
  },
  resultCard: {
    backgroundColor: '#f8fafc',
    borderRadius: 10,
    padding: 15,
    width: '48%',
    marginBottom: 10,
    alignItems: 'center',
  },
  resultLabel: {
    fontSize: 12,
    color: '#64748b',
    marginBottom: 5,
    textAlign: 'center',
  },
  resultValue: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#1e293b',
    textAlign: 'center',
  },
  saveButton: {
    backgroundColor: '#10b981',
    borderRadius: 12,
    padding: 15,
    alignItems: 'center',
  },
  saveButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
});

export default StrategyTestScreen;