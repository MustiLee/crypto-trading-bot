import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, Alert, KeyboardAvoidingView, Platform, ScrollView } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { StackNavigationProp } from '@react-navigation/stack';
import { AuthStackParamList } from '../types';
import { RouteProp } from '@react-navigation/native';
import { apiService } from '../services/api';

type Nav = StackNavigationProp<AuthStackParamList, 'ResetPassword'>;
type Route = RouteProp<AuthStackParamList, 'ResetPassword'>;

interface Props { navigation: Nav; route: Route }

const ResetPasswordScreen: React.FC<Props> = ({ navigation, route }) => {
  const { email } = route.params;
  const [p1, setP1] = useState('');
  const [p2, setP2] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSave = async () => {
    if (!p1 || !p2) {
      Alert.alert('Hata', 'Lütfen tüm alanları doldurunuz.');
      return;
    }
    if (p1 !== p2) {
      Alert.alert('Hata', 'Şifreler eşleşmiyor.');
      return;
    }
    if (p1.length < 8) {
      Alert.alert('Hata', 'Şifre en az 8 karakter olmalıdır.');
      return;
    }
    try {
      setLoading(true);
      const res = await apiService.resetPassword(email, p1);
      if (res.success !== false) {
        Alert.alert('Başarılı', 'Şifreniz güncellendi. Giriş yapabilirsiniz.', [
          { text: 'Tamam', onPress: () => navigation.navigate('Login', { fromPasswordReset: true }) },
        ]);
      } else {
        Alert.alert('Hata', res.message || 'Şifre güncellenemedi');
      }
    } catch (e: any) {
      Alert.alert('Hata', e?.message || 'Şifre güncellenemedi');
    } finally {
      setLoading(false);
    }
  };

  return (
    <LinearGradient colors={["#667eea", "#764ba2"]} style={styles.container}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={{ flex: 1 }}>
        <ScrollView contentContainerStyle={styles.content}>
          <View style={styles.card}>
            <Text style={styles.title}>Yeni Şifre</Text>
            <Text style={styles.subtitle}>Lütfen yeni şifrenizi giriniz</Text>

            <Text style={styles.label}>Yeni Şifre</Text>
            <TextInput style={styles.input} value={p1} onChangeText={setP1} secureTextEntry placeholder='Yeni şifre' />

            <Text style={styles.label}>Yeni Şifre (Tekrar)</Text>
            <TextInput style={styles.input} value={p2} onChangeText={setP2} secureTextEntry placeholder='Yeni şifre (tekrar)' />

            <TouchableOpacity style={styles.button} onPress={handleSave} disabled={loading}>
              <Text style={styles.buttonText}>{loading ? 'Kaydediliyor...' : 'Kaydet'}</Text>
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

export default ResetPasswordScreen;
