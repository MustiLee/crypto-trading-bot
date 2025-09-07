import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Text, View, TouchableOpacity, StyleSheet } from 'react-native';

import { useAuth } from '../context/AuthContext';
import { RootStackParamList, AuthStackParamList } from '../types';

import LoginScreen from '../screens/LoginScreen';
import RegisterScreen from '../screens/RegisterScreen';
import ForgotPasswordStart from '../screens/ForgotPasswordStart';
import ForgotPasswordVerify from '../screens/ForgotPasswordVerify';
import ResetPasswordScreen from '../screens/ResetPasswordScreen';
import DashboardScreen from '../screens/DashboardScreen';
import NewsScreen from '../screens/NewsScreen';
import StrategiesScreen from '../screens/StrategiesScreen';
import StrategyTestScreen from '../screens/StrategyTestScreen';

const RootStack = createStackNavigator<RootStackParamList>();
const AuthStack = createStackNavigator<AuthStackParamList>();
const MainTabs = createBottomTabNavigator();

const AuthNavigator = () => (
  <AuthStack.Navigator
    screenOptions={({ navigation }) => ({
      headerShown: true,
      headerStyle: { backgroundColor: 'white' },
      headerTitleStyle: { fontWeight: '700', color: '#333' },
      headerBackTitleVisible: false,
      headerBackTitle: '',
      headerRight: () => (
        <TouchableOpacity
          onPress={() => navigation.getParent()?.goBack()}
          style={{ paddingHorizontal: 16, paddingVertical: 8 }}
          accessibilityLabel="Kapat"
        >
          <Text style={{ fontSize: 18 }}>✖️</Text>
        </TouchableOpacity>
      ),
    })}
  >
    <AuthStack.Screen 
      name="Login" 
      component={LoginScreen}
      options={{ title: 'Giriş' }}
    />
    <AuthStack.Screen 
      name="Register" 
      component={RegisterScreen}
      options={{ title: 'Kayıt Ol' }}
    />
    <AuthStack.Screen
      name="ForgotPasswordStart"
      component={ForgotPasswordStart}
      options={{ title: 'Şifremi Unuttum' }}
    />
    <AuthStack.Screen
      name="ForgotPasswordVerify"
      component={ForgotPasswordVerify}
      options={{ title: 'Doğrulama' }}
    />
    <AuthStack.Screen
      name="ResetPassword"
      component={ResetPasswordScreen}
      options={{ title: 'Yeni Şifre' }}
    />
  </AuthStack.Navigator>
);

const ProfileScreen = ({ navigation }: any) => {
  const { user, logout } = useAuth();

  const handleLogout = async () => {
    await logout();
  };

  const handleLogin = () => {
    navigation.navigate('AuthStack');
  };

  return (
    <View style={profileStyles.container}>
      <Text style={profileStyles.title}>👤 Profil</Text>
      
      {user ? (
        <View style={profileStyles.userInfo}>
          <Text style={profileStyles.userName}>{user.first_name} {user.last_name}</Text>
          <Text style={profileStyles.userEmail}>{user.email}</Text>
          {user.phone && <Text style={profileStyles.userDetail}>📞 {user.phone}</Text>}
          {user.telegram_id && <Text style={profileStyles.userDetail}>📱 {user.telegram_id}</Text>}
          
          <TouchableOpacity style={profileStyles.logoutButton} onPress={handleLogout}>
            <Text style={profileStyles.logoutText}>🚪 Çıkış Yap</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <View style={profileStyles.userInfo}>
          <Text style={profileStyles.guestTitle}>Misafir Modunda</Text>
          <Text style={profileStyles.guestText}>Stratejileri kaydetmek için giriş yapın</Text>
          
          <TouchableOpacity style={profileStyles.loginButton} onPress={handleLogin}>
            <Text style={profileStyles.loginText}>🔑 Giriş Yap</Text>
          </TouchableOpacity>
        </View>
      )}
    </View>
  );
};

const MainTabsNavigator = () => (
  <MainTabs.Navigator
    screenOptions={{
      headerShown: false,
      tabBarStyle: {
        backgroundColor: '#667eea',
        borderTopWidth: 0,
        elevation: 8,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: -2 },
        shadowOpacity: 0.1,
        shadowRadius: 4,
        paddingBottom: 5,
        height: 60,
      },
      tabBarActiveTintColor: 'white',
      tabBarInactiveTintColor: 'rgba(255,255,255,0.6)',
      tabBarLabelStyle: {
        fontSize: 12,
        fontWeight: '600',
        marginBottom: 3,
      },
    }}
  >
    <MainTabs.Screen
      name="Dashboard"
      component={DashboardScreen}
      options={{
        tabBarLabel: 'Ana Sayfa',
        tabBarIcon: ({ color }) => <Text style={{ fontSize: 20, color }}>📊</Text>,
      }}
    />
    <MainTabs.Screen
      name="News"
      component={NewsScreen}
      options={{
        tabBarLabel: 'Haberler',
        tabBarIcon: ({ color }) => <Text style={{ fontSize: 20, color }}>📰</Text>,
      }}
    />
    <MainTabs.Screen
      name="Strategies"
      component={StrategiesScreen}
      options={{
        tabBarLabel: 'Stratejiler',
        tabBarIcon: ({ color }) => <Text style={{ fontSize: 20, color }}>🎯</Text>,
      }}
    />
    <MainTabs.Screen
      name="Profile"
      component={ProfileScreen}
      options={{
        tabBarLabel: 'Profil',
        tabBarIcon: ({ color }) => <Text style={{ fontSize: 20, color }}>👤</Text>,
      }}
    />
  </MainTabs.Navigator>
);

const AppNavigation = () => {
  const { isLoading } = useAuth();

  if (isLoading) {
    return (
      <View style={profileStyles.container}>
        <Text style={profileStyles.loading}>🚀 Yükleniyor...</Text>
      </View>
    );
  }

  return (
    <NavigationContainer>
      <RootStack.Navigator screenOptions={{ headerShown: false }}>
        <RootStack.Screen name="MainTabs" component={MainTabsNavigator} />
        <RootStack.Screen 
          name="AuthStack" 
          component={AuthNavigator} 
          options={{ presentation: 'modal' }}
        />
        <RootStack.Screen 
          name="StrategyTest" 
          component={StrategyTestScreen}
          options={{ presentation: 'modal' }}
        />
      </RootStack.Navigator>
    </NavigationContainer>
  );
};

const profileStyles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8fafc',
    padding: 20,
    paddingTop: 60,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#333',
    textAlign: 'center',
    marginBottom: 30,
  },
  userInfo: {
    backgroundColor: 'white',
    borderRadius: 15,
    padding: 20,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  userName: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 8,
  },
  userEmail: {
    fontSize: 16,
    color: '#666',
    marginBottom: 15,
  },
  userDetail: {
    fontSize: 14,
    color: '#888',
    marginBottom: 5,
  },
  logoutButton: {
    backgroundColor: '#ef4444',
    paddingHorizontal: 30,
    paddingVertical: 12,
    borderRadius: 25,
    marginTop: 20,
  },
  logoutText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
  guestTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 8,
    textAlign: 'center',
  },
  guestText: {
    fontSize: 14,
    color: '#666',
    textAlign: 'center',
    marginBottom: 20,
  },
  loginButton: {
    backgroundColor: '#667eea',
    paddingHorizontal: 30,
    paddingVertical: 12,
    borderRadius: 25,
    marginTop: 10,
  },
  loginText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
  comingSoon: {
    fontSize: 18,
    color: '#666',
    textAlign: 'center',
    marginTop: 50,
  },
  loading: {
    fontSize: 18,
    color: '#666',
    textAlign: 'center',
    flex: 1,
    textAlignVertical: 'center',
  },
});

export default AppNavigation;
