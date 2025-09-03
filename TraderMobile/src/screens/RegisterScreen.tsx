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
  Modal,
  FlatList,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { useAuth } from '../context/AuthContext';
import { StackNavigationProp } from '@react-navigation/stack';
import { AuthStackParamList } from '../types';
import { countries, Country, validatePhoneNumber, formatPhoneNumber, validateEmail, generateEmailVerificationCode } from '../utils/countries';
import { apiService } from '../services/api';

type RegisterScreenNavigationProp = StackNavigationProp<AuthStackParamList, 'Register'>;

interface Props {
  navigation: RegisterScreenNavigationProp;
}

const RegisterScreen: React.FC<Props> = ({ navigation }) => {
  const [currentStep, setCurrentStep] = useState<'register' | 'verify'>('register');
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    first_name: '',
    last_name: '',
    phone: '',
  });
  const [selectedCountry, setSelectedCountry] = useState<Country>(countries[0]); // Default to Turkey
  const [showCountryPicker, setShowCountryPicker] = useState(false);
  const [verificationCode, setVerificationCode] = useState('');
  const [generatedCode, setGeneratedCode] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { register, login } = useAuth();

  const handleInputChange = (field: string, value: string) => {
    if (field === 'phone') {
      // Format phone number as user types
      const formatted = formatPhoneNumber(value, selectedCountry);
      setFormData(prev => ({ ...prev, [field]: formatted }));
    } else {
      setFormData(prev => ({ ...prev, [field]: value }));
    }
  };

  const validateForm = (): boolean => {
    const { email, password, confirmPassword, first_name, last_name, phone } = formData;
    
    if (!email.trim() || !password.trim() || !first_name.trim() || !last_name.trim() || !phone.trim()) {
      Alert.alert('Hata', 'Tüm alanlar zorunludur.');
      return false;
    }

    if (first_name.trim().length < 2 || last_name.trim().length < 2) {
      Alert.alert('Hata', 'Ad ve Soyad en az 2 karakter olmalıdır.');
      return false;
    }

    if (!validateEmail(email)) {
      Alert.alert('Hata', 'Geçerli bir email adresi giriniz.');
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

    const cleanPhone = phone.replace(/\D/g, '');
    if (!validatePhoneNumber(cleanPhone, selectedCountry)) {
      Alert.alert(
        'Hata', 
        `${selectedCountry.name} için geçerli bir telefon numarası giriniz.\nFormat: ${selectedCountry.phoneFormat}\nUzunluk: ${selectedCountry.phoneLength} rakam`
      );
      return false;
    }

    return true;
  };

  const handleSendVerification = async () => {
    if (!validateForm()) return;

    setIsLoading(true);
    try {
      const { email, password, first_name, last_name, phone } = formData;
      const cleanPhone = phone.replace(/\D/g, '');
      const fullPhone = selectedCountry.phoneCode + cleanPhone;
      
      const result = await register({
        email: email.trim(),
        password,
        first_name: first_name.trim(),
        last_name: last_name.trim(),
        phone: fullPhone,
      });

      if (result.success) {
        Alert.alert(
          '📧 Doğrulama Kodu Gönderildi',
          `${formData.email} adresine 6 haneli doğrulama kodu gönderildi.\n\nLütfen email kutunuzu (spam klasörünü de) kontrol edin ve kodu bir sonraki sayfada girin.`,
          [{ 
            text: 'Devam Et', 
            onPress: () => {
              console.log('Moving to verify step');
              setCurrentStep('verify');
            }
          }]
        );
      } else {
        console.error('Registration failed:', result);
        Alert.alert('Hata', result.message);
      }
      
    } catch (error) {
      console.error('Registration error:', error);
      Alert.alert('Hata', `Doğrulama kodu gönderilirken bir hata oluştu: ${error instanceof Error ? error.message : 'Bilinmeyen hata'}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerifyAndRegister = async () => {
    if (!verificationCode.trim()) {
      Alert.alert('Hata', 'Doğrulama kodunu giriniz.');
      return;
    }

    setIsLoading(true);
    try {
      // Call verify email API
      const result = await apiService.verifyEmail(formData.email, verificationCode);

      if (result.success) {
        // Verification successful, now auto-login the user
        const loginSuccess = await login(formData.email, formData.password);
        
        if (loginSuccess) {
          Alert.alert(
            'Başarılı',
            'Hesabınız başarıyla oluşturuldu ve giriş yapıldı!',
            [{ text: 'Tamam', onPress: () => {
              if (navigation.canGoBack()) {
                navigation.goBack();
              } else {
                navigation.navigate('MainTabs' as any);
              }
            }}]
          );
        } else {
          Alert.alert(
            'Hesap Oluşturuldu',
            'Hesabınız başarıyla oluşturuldu. Lütfen giriş yapın.',
            [{ text: 'Tamam', onPress: () => navigation.navigate('Login') }]
          );
        }
      } else {
        Alert.alert('Hata', result.message);
      }
    } catch (error) {
      Alert.alert('Hata', 'Doğrulama sırasında bir hata oluştu.');
    } finally {
      setIsLoading(false);
    }
  };

  const renderCountryPicker = () => (
    <Modal
      visible={showCountryPicker}
      animationType="slide"
      presentationStyle="pageSheet"
    >
      <View style={styles.modalContainer}>
        <View style={styles.modalHeader}>
          <TouchableOpacity onPress={() => setShowCountryPicker(false)}>
            <Text style={styles.modalCancelButton}>İptal</Text>
          </TouchableOpacity>
          <Text style={styles.modalTitle}>Ülke Seçin</Text>
          <View style={{ width: 50 }} />
        </View>
        
        <FlatList
          data={countries}
          keyExtractor={(item) => item.code}
          renderItem={({ item }) => (
            <TouchableOpacity
              style={styles.countryItem}
              onPress={() => {
                setSelectedCountry(item);
                setFormData(prev => ({ ...prev, phone: '' })); // Clear phone when country changes
                setShowCountryPicker(false);
              }}
            >
              <Text style={styles.countryFlag}>{item.flag}</Text>
              <View style={styles.countryInfo}>
                <Text style={styles.countryName}>{item.name}</Text>
                <Text style={styles.countryCode}>{item.phoneCode}</Text>
              </View>
              {selectedCountry.code === item.code && (
                <Text style={styles.selectedIndicator}>✓</Text>
              )}
            </TouchableOpacity>
          )}
        />
      </View>
    </Modal>
  );

  const renderRegisterStep = () => (
    <View style={styles.formContainer}>
      <Text style={styles.title}>🚀 Trader Dashboard</Text>
      <Text style={styles.subtitle}>Yeni hesap oluşturun</Text>
      <Text style={styles.stepIndicator}>Adım 1/2: Bilgilerinizi girin</Text>

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
        <Text style={styles.inputLabel}>Telefon * ({selectedCountry.name})</Text>
        <View style={styles.phoneContainer}>
          <TouchableOpacity
            style={styles.countrySelector}
            onPress={() => setShowCountryPicker(true)}
          >
            <Text style={styles.countryFlag}>{selectedCountry.flag}</Text>
            <Text style={styles.phoneCode}>{selectedCountry.phoneCode}</Text>
            <Text style={styles.dropdownArrow}>▼</Text>
          </TouchableOpacity>
          <TextInput
            style={styles.phoneInput}
            value={formData.phone}
            onChangeText={(value) => handleInputChange('phone', value)}
            placeholder={selectedCountry.phoneFormat || `${selectedCountry.phoneLength} rakam`}
            placeholderTextColor="#999"
            keyboardType="phone-pad"
            maxLength={selectedCountry.phoneFormat?.length || selectedCountry.phoneLength + 5}
          />
        </View>
        <Text style={styles.phoneHelper}>
          Format: {selectedCountry.phoneFormat} ({selectedCountry.phoneLength} rakam)
        </Text>
      </View>

      <TouchableOpacity
        style={[styles.registerButton, isLoading && styles.disabledButton]}
        onPress={handleSendVerification}
        disabled={isLoading}
      >
        <Text style={styles.registerButtonText}>
          {isLoading ? 'Doğrulama kodu gönderiliyor...' : 'Doğrulama Kodu Gönder'}
        </Text>
      </TouchableOpacity>

      <View style={styles.loginContainer}>
        <Text style={styles.loginText}>Zaten hesabınız var mı? </Text>
        <TouchableOpacity onPress={() => navigation.navigate('Login')}>
          <Text style={styles.loginLink}>Giriş yapın</Text>
        </TouchableOpacity>
      </View>
    </View>
  );

  const renderVerifyStep = () => (
    <View style={styles.formContainer}>
      <Text style={styles.title}>📧 Email Doğrulama</Text>
      <Text style={styles.subtitle}>
        {formData.email} adresine gönderilen doğrulama kodunu giriniz
      </Text>
      <Text style={styles.stepIndicator}>Adım 2/2: Email doğrulama</Text>

      <View style={styles.inputContainer}>
        <Text style={styles.inputLabel}>Doğrulama Kodu</Text>
        <TextInput
          style={styles.input}
          value={verificationCode}
          onChangeText={setVerificationCode}
          placeholder="6 haneli doğrulama kodunu giriniz"
          placeholderTextColor="#999"
          autoCapitalize="characters"
          maxLength={6}
        />
      </View>

      <TouchableOpacity
        style={[styles.registerButton, isLoading && styles.disabledButton]}
        onPress={handleVerifyAndRegister}
        disabled={isLoading}
      >
        <Text style={styles.registerButtonText}>
          {isLoading ? 'Hesap oluşturuluyor...' : 'Hesabı Oluştur'}
        </Text>
      </TouchableOpacity>

      <View style={styles.verifyActions}>
        <TouchableOpacity onPress={() => setCurrentStep('register')}>
          <Text style={styles.backLink}>← Geri dön</Text>
        </TouchableOpacity>
        
        <TouchableOpacity onPress={async () => {
          try {
            const result = await apiService.resendVerificationCode(formData.email);
            Alert.alert(result.success ? 'Başarılı' : 'Hata', result.message);
          } catch (error) {
            Alert.alert('Hata', 'Kod gönderilirken bir hata oluştu.');
          }
        }}>
          <Text style={styles.resendLink}>Kodu tekrar gönder</Text>
        </TouchableOpacity>
      </View>
    </View>
  );

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
          {currentStep === 'register' ? renderRegisterStep() : renderVerifyStep()}
        </ScrollView>
      </KeyboardAvoidingView>
      {renderCountryPicker()}
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
    marginBottom: 10,
  },
  stepIndicator: {
    fontSize: 14,
    textAlign: 'center',
    color: '#667eea',
    fontWeight: '600',
    marginBottom: 20,
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
  phoneContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  countrySelector: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#f8fafc',
    borderRadius: 12,
    padding: 15,
    marginRight: 10,
    borderWidth: 1,
    borderColor: '#e2e8f0',
    minWidth: 100,
  },
  countryFlag: {
    fontSize: 20,
    marginRight: 5,
  },
  phoneCode: {
    fontSize: 16,
    color: '#333',
    marginRight: 5,
  },
  dropdownArrow: {
    fontSize: 12,
    color: '#666',
  },
  phoneInput: {
    flex: 1,
    backgroundColor: '#f8fafc',
    borderRadius: 12,
    padding: 15,
    fontSize: 16,
    borderWidth: 1,
    borderColor: '#e2e8f0',
  },
  phoneHelper: {
    fontSize: 12,
    color: '#666',
    marginTop: 5,
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
  verifyActions: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 20,
  },
  backLink: {
    color: '#667eea',
    fontSize: 14,
    fontWeight: '600',
  },
  resendLink: {
    color: '#666',
    fontSize: 14,
    textDecorationLine: 'underline',
  },
  modalContainer: {
    flex: 1,
    backgroundColor: 'white',
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#e2e8f0',
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
  },
  modalCancelButton: {
    fontSize: 16,
    color: '#667eea',
  },
  countryItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#f1f5f9',
  },
  countryInfo: {
    flex: 1,
    marginLeft: 12,
  },
  countryName: {
    fontSize: 16,
    fontWeight: '500',
    color: '#333',
  },
  countryCode: {
    fontSize: 14,
    color: '#666',
    marginTop: 2,
  },
  selectedIndicator: {
    fontSize: 18,
    color: '#667eea',
    fontWeight: 'bold',
  },
});

export default RegisterScreen;
