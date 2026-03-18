/**
 * Root layout — renders login or tabs based on auth state.
 */
import { useEffect, useState } from 'react';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import api, { setAuthChangeHandler } from '../services/api';
import LoginScreen from './login';

export default function RootLayout() {
  const [ready, setReady] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    setAuthChangeHandler((val) => setIsAuthenticated(val));
    api.loadToken().then(() => {
      setIsAuthenticated(!!api.token);
      setReady(true);
    });
  }, []);

  if (!ready) return null;

  if (!isAuthenticated) {
    return (
      <GestureHandlerRootView style={{ flex: 1 }}>
        <StatusBar style="light" />
        <LoginScreen />
      </GestureHandlerRootView>
    );
  }

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <StatusBar style="light" />
      <Stack screenOptions={{ headerShown: false }}>
        <Stack.Screen name="(tabs)" />
      </Stack>
    </GestureHandlerRootView>
  );
}
