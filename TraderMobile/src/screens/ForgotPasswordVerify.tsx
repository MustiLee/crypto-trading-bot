import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, Alert, KeyboardAvoidingView, Platform, ScrollView } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { StackNavigationProp } from '@react-navigation/stack';
import { AuthStackParamList } from '../types';
import { RouteProp } from '@react-navigation/native';
import { apiService } from '../services/api';

type Nav = StackNavigationProp<AuthStackParamList, 'ForgotPasswordVerify'>;
type Route = RouteProp<AuthStackParamList, 'ForgotPasswordVerify'>;

interface Props { navigation: Nav; route: Route }

const ForgotPasswordVerify: React.FC<Props> = ({ navigation, route }) => {
  const { email } = route.params;
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);

  const handleVerify = async () => {
    if (!code || code.length !== 6) {
      Alert.alert('Hata', '6 haneli doğrulama kodunu giriniz.');
      return;
    }
    try {
      setLoading(true);
      const res = await apiService.verifyPasswordReset(email, code);
      if (res.success !== false) {
        navigation.navigate('ResetPassword', { email });
      } else {
        Alert.alert('Hata', res.message || 'Doğrulama başarısız');
      }
    } catch (e: any) {
      Alert.alert('Hata', e?.message || 'Doğrulama başarısız');
    } finally {
      setLoading(false);
    }
  };

  return (
    <LinearGradient colors={["#667eea", "#764ba2"]} style={styles.container}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={{ flex: 1 }}>
        <ScrollView contentContainerStyle={styles.content}>
          <View style={styles.card}>
            <Text style={styles.title}>Doğrulama</Text>
            <Text style={styles.subtitle}>Lütfen size gönderilen doğrulama kodunu giriniz</Text>

            <Text style={styles.label}>Doğrulama Kodu</Text>
            <TextInput
              style={styles.input}
              value={code}
              onChangeText={setCode}
              placeholder='000000'
              keyboardType='number-pad'
              maxLength={6}
            />

            <TouchableOpacity style={styles.button} onPress={handleVerify} disabled={loading}>
              <Text style={styles.buttonText}>{loading ? 'Kontrol ediliyor...' : 'Doğrula'}</Text>
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

export default ForgotPasswordVerify;

