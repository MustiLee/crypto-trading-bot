import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, Alert, KeyboardAvoidingView, Platform, ScrollView } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { StackNavigationProp } from '@react-navigation/stack';
import { AuthStackParamList } from '../types';
import { apiService } from '../services/api';

type Nav = StackNavigationProp<AuthStackParamList, 'ForgotPasswordStart'>;

interface Props { navigation: Nav }

const ForgotPasswordStart: React.FC<Props> = ({ navigation }) => {
  const [email, setEmail] = useState('');
  // Phone field removed: only email is required for reset
  const [loading, setLoading] = useState(false);

  const handleContinue = async () => {
    if (!email.trim()) {
      Alert.alert('Hata', 'Lütfen email adresini giriniz.');
      return;
    }
    try {
      setLoading(true);
      const res = await apiService.requestPasswordReset(email.trim());
      if (res.success !== false) {
        navigation.navigate('ForgotPasswordVerify', { email: email.trim() });
      } else {
        Alert.alert('Uyarı', res.message || 'İşlem gerçekleştirilemedi');
      }
    } catch (e: any) {
      Alert.alert('Hata', e?.message || 'İşlem başarısız');
    } finally {
      setLoading(false);
    }
  };

  return (
    <LinearGradient colors={["#667eea", "#764ba2"]} style={styles.container}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={{ flex: 1 }}>
        <ScrollView contentContainerStyle={styles.content}>
          <View style={styles.card}>
            <Text style={styles.title}>Şifremi Unuttum</Text>
            <Text style={styles.subtitle}>Lütfen email adresinizi giriniz</Text>

            <Text style={styles.label}>Email</Text>
            <TextInput style={styles.input} value={email} onChangeText={setEmail} autoCapitalize='none' keyboardType='email-address' placeholder='Email' />

            {/* Telefon alanı kaldırıldı: sadece email ile doğrulama */}

            <TouchableOpacity style={styles.button} onPress={handleContinue} disabled={loading}>
              <Text style={styles.buttonText}>{loading ? 'Gönderiliyor...' : 'Devam'}</Text>
            </TouchableOpacity>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </LinearGradient>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: { flexGrow: 1, justifyContent: 'center', padding: 20 },
  card: { backgroundColor: 'rgba(255,255,255,0.95)', borderRadius: 16, padding: 20 },
  title: { fontSize: 22, fontWeight: '700', color: '#333', marginBottom: 6, textAlign: 'center' },
  subtitle: { fontSize: 14, color: '#666', marginBottom: 16, textAlign: 'center' },
  label: { fontSize: 13, color: '#333', fontWeight: '600', marginTop: 8, marginBottom: 6 },
  input: { backgroundColor: '#f8fafc', borderRadius: 10, padding: 12, borderWidth: 1, borderColor: '#e2e8f0' },
  button: { backgroundColor: '#667eea', borderRadius: 10, padding: 14, alignItems: 'center', marginTop: 16 },
  buttonText: { color: '#fff', fontWeight: '700' },
});

export default ForgotPasswordStart;
