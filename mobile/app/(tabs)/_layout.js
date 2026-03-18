/**
 * App layout — Stack navigator (no tabs).
 * The sales rep has one main screen: Clientes.
 * Visit recording is a separate stack screen pushed from Clientes.
 */
import { Stack } from 'expo-router';

export default function Layout() {
  return (
    <Stack
      screenOptions={{
        headerStyle: { backgroundColor: '#0f172a' },
        headerTintColor: '#f1f5f9',
        headerTitleStyle: { fontWeight: '700' },
        headerBackTitle: 'Clientes',
      }}
    >
      <Stack.Screen name="index" options={{ title: 'Clientes' }} />
      <Stack.Screen name="visita" options={{ title: 'Nueva Visita' }} />
    </Stack>
  );
}
