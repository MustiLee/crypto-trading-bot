import React from 'react';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { StyleSheet, View, Text } from 'react-native';

import { AuthProvider } from './src/context/AuthContext';
import { PriceProvider } from './src/context/PriceContext';
import AppNavigation from './src/navigation/AppNavigation';

export default function App() {
  console.log('App component rendering...');
  
  return (
    <GestureHandlerRootView style={styles.container}>
      <SafeAreaProvider>
        <AuthProvider>
          <PriceProvider>
            <AppNavigation />
            <StatusBar style="light" />
          </PriceProvider>
        </AuthProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
});
