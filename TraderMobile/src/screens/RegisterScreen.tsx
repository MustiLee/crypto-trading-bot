import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Alert,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { useAuth } from '../context/AuthContext';
import { StackNavigationProp } from '@react-navigation/stack';
import { AuthStackParamList } from '../types';

type RegisterScreenNavigationProp = StackNavigationProp<AuthStackParamList, 'Register'>;

interface Props {
  navigation: RegisterScreenNavigationProp;
}

const RegisterScreen: React.FC<Props> = ({ navigation }) => {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    first_name: '',
    last_name: '',
    phone: '',
    telegram_id: '',
  });
  const [isLoading, setIsLoading] = useState(false);
  const { register } = useAuth();

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const validateForm = (): boolean => {
    const { email, password, confirmPassword, first_name, last_name } = formData;
    
    if (!email.trim() || !password.trim() || !first_name.trim() || !last_name.trim()) {
      Alert.alert('Hata', 'Zorunlu alanları doldurunuz.');
      return false;
    }

    if (password !== confirmPassword) {
      Alert.alert('Hata', 'Şifreler eşleşmiyor.');
      return false;
    }

    if (password.length < 8) {
      Alert.alert('Hata', 'Şifre en az 8 karakter olmalıdır.');
      return false;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      Alert.alert('Hata', 'Geçerli bir email adresi giriniz.');
      return false;
    }

    return true;
  };

  const handleRegister = async () => {
    if (!validateForm()) return;

    setIsLoading(true);
    try {
      const { email, password, first_name, last_name, phone, telegram_id } = formData;
      const result = await register({
        email: email.trim(),
        password,
        first_name: first_name.trim(),
        last_name: last_name.trim(),
        phone: phone.trim() || undefined,
        telegram_id: telegram_id.trim() || undefined,
      });

      if (result.success) {
        Alert.alert(
          'Başarılı',
          result.message,
          [{ text: 'Tamam', onPress: () => navigation.navigate('Login') }]
        );
      } else {
        Alert.alert('Hata', result.message);
      }
    } catch (error) {
      Alert.alert('Hata', 'Kayıt olurken bir hata oluştu.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <LinearGradient
      colors={['#667eea', '#764ba2']}
      style={styles.container}
    >
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.keyboardContainer}
      >
        <ScrollView contentContainerStyle={styles.scrollContainer}>
          <View style={styles.formContainer}>
            <Text style={styles.title}>🚀 Trader Dashboard</Text>
            <Text style={styles.subtitle}>Yeni hesap oluşturun</Text>

            <View style={styles.row}>
              <View style={[styles.inputContainer, styles.halfWidth]}>
                <Text style={styles.inputLabel}>Ad *</Text>
                <TextInput
                  style={styles.input}
                  value={formData.first_name}
                  onChangeText={(value) => handleInputChange('first_name', value)}
                  placeholder="Adınız"
                  placeholderTextColor="#999"
                />
              </View>
              <View style={[styles.inputContainer, styles.halfWidth]}>
                <Text style={styles.inputLabel}>Soyad *</Text>
                <TextInput
                  style={styles.input}
                  value={formData.last_name}
                  onChangeText={(value) => handleInputChange('last_name', value)}
                  placeholder="Soyadınız"
                  placeholderTextColor="#999"
                />
              </View>
            </View>

            <View style={styles.inputContainer}>
              <Text style={styles.inputLabel}>Email *</Text>
              <TextInput
                style={styles.input}
                value={formData.email}
                onChangeText={(value) => handleInputChange('email', value)}
                placeholder="Email adresinizi giriniz"
                placeholderTextColor="#999"
                keyboardType="email-address"
                autoCapitalize="none"
                autoComplete="email"
              />
            </View>

            <View style={styles.inputContainer}>
              <Text style={styles.inputLabel}>Şifre *</Text>
              <TextInput
                style={styles.input}
                value={formData.password}
                onChangeText={(value) => handleInputChange('password', value)}
                placeholder="Şifrenizi giriniz (min. 8 karakter)"
                placeholderTextColor="#999"
                secureTextEntry
                autoComplete="new-password"
              />
            </View>

            <View style={styles.inputContainer}>
              <Text style={styles.inputLabel}>Şifre Tekrar *</Text>
              <TextInput
                style={styles.input}
                value={formData.confirmPassword}
                onChangeText={(value) => handleInputChange('confirmPassword', value)}
                placeholder="Şifrenizi tekrar giriniz"
                placeholderTextColor="#999"
                secureTextEntry
                autoComplete="new-password"
              />
            </View>

            <View style={styles.inputContainer}>
              <Text style={styles.inputLabel}>Telefon</Text>
              <TextInput
                style={styles.input}
                value={formData.phone}
                onChangeText={(value) => handleInputChange('phone', value)}
                placeholder="Telefon numaranız (opsiyonel)"
                placeholderTextColor="#999"
                keyboardType="phone-pad"
              />
            </View>

            <View style={styles.inputContainer}>
              <Text style={styles.inputLabel}>Telegram ID</Text>
              <TextInput
                style={styles.input}
                value={formData.telegram_id}
                onChangeText={(value) => handleInputChange('telegram_id', value)}
                placeholder="Telegram kullanıcı adınız (opsiyonel)"
                placeholderTextColor="#999"
                autoCapitalize="none"
              />
            </View>

            <TouchableOpacity
              style={[styles.registerButton, isLoading && styles.disabledButton]}
              onPress={handleRegister}
              disabled={isLoading}
            >
              <Text style={styles.registerButtonText}>
                {isLoading ? 'Kayıt oluşturuluyor...' : 'Kayıt Ol'}
              </Text>
            </TouchableOpacity>

            <View style={styles.loginContainer}>
              <Text style={styles.loginText}>Zaten hesabınız var mı? </Text>
              <TouchableOpacity onPress={() => navigation.navigate('Login')}>
                <Text style={styles.loginLink}>Giriş yapın</Text>
              </TouchableOpacity>
            </View>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </LinearGradient>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  keyboardContainer: {
    flex: 1,
  },
  scrollContainer: {
    flexGrow: 1,
    justifyContent: 'center',
    padding: 20,
  },
  formContainer: {
    backgroundColor: 'rgba(255, 255, 255, 0.95)',
    borderRadius: 20,
    padding: 30,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.3,
    shadowRadius: 20,
    elevation: 10,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 10,
    color: '#333',
  },
  subtitle: {
    fontSize: 16,
    textAlign: 'center',
    color: '#666',
    marginBottom: 30,
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  inputContainer: {
    marginBottom: 20,
  },
  halfWidth: {
    width: '48%',
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
    padding: 15,
    fontSize: 16,
    borderWidth: 1,
    borderColor: '#e2e8f0',
  },
  registerButton: {
    backgroundColor: '#667eea',
    borderRadius: 12,
    padding: 15,
    alignItems: 'center',
    marginTop: 10,
  },
  disabledButton: {
    backgroundColor: '#ccc',
  },
  registerButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
  loginContainer: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 20,
  },
  loginText: {
    color: '#666',
    fontSize: 14,
  },
  loginLink: {
    color: '#667eea',
    fontSize: 14,
    fontWeight: '600',
  },
});

export default RegisterScreen;