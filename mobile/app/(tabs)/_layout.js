/**
 * Tab layout — Main navigation for the sales rep app.
 * 
 * 4 tabs: Clients, Call, Visit (record), Stats
 */
import { Tabs } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';

const COLORS = {
  active: '#f59e0b',
  inactive: '#94a3b8',
  bg: '#0f172a',
  card: '#1e293b',
};

export default function TabLayout() {
  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: COLORS.active,
        tabBarInactiveTintColor: COLORS.inactive,
        tabBarStyle: {
          backgroundColor: COLORS.bg,
          borderTopColor: COLORS.card,
          height: 60,
          paddingBottom: 8,
        },
        headerStyle: { backgroundColor: COLORS.bg },
        headerTintColor: '#f1f5f9',
        headerTitleStyle: { fontWeight: '700' },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: 'Clientes',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="people" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="llamar"
        options={{
          title: 'Llamar',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="call" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="visita"
        options={{
          title: 'Visita',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="mic" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="stats"
        options={{
          title: 'Stats',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="bar-chart" size={size} color={color} />
          ),
        }}
      />
    </Tabs>
  );
}
