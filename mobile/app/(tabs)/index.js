/**
 * Clients Tab — List of all clients synced from phone contacts.
 * 
 * Shows status colors matching the original Excel legend:
 * Red = no_llamar, Green = venta, Yellow = equivocado, Purple = cita, Blue = seguimiento
 */
import { useState, useEffect, useCallback } from 'react';
import {
  View, Text, FlatList, TextInput, TouchableOpacity,
  StyleSheet, RefreshControl, Alert, Linking,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import api from '../../services/api';
import { syncContactsToBackend } from '../../services/contacts';

const STATUS_COLORS = {
  nuevo: { bg: '#334155', text: '#94a3b8', label: 'Nuevo' },
  no_llamar: { bg: '#7f1d1d', text: '#fca5a5', label: 'No Llamar' },
  venta: { bg: '#064e3b', text: '#6ee7b7', label: 'Venta' },
  equivocado: { bg: '#713f12', text: '#fde047', label: 'Equivocado' },
  cita: { bg: '#581c87', text: '#d8b4fe', label: 'Cita' },
  seguimiento: { bg: '#1e3a5f', text: '#93c5fd', label: 'Seguimiento' },
};

export default function ClientesTab() {
  const [clientes, setClientes] = useState([]);
  const [search, setSearch] = useState('');
  const [refreshing, setRefreshing] = useState(false);
  const [syncing, setSyncing] = useState(false);

  const loadClientes = useCallback(async () => {
    try {
      const params = {};
      if (search) params.buscar = search;
      const data = await api.getClientes(params);
      setClientes(data);
    } catch (error) {
      console.error('Error loading clients:', error);
    }
  }, [search]);

  useEffect(() => {
    loadClientes();
  }, [loadClientes]);

  const onRefresh = async () => {
    setRefreshing(true);
    await loadClientes();
    setRefreshing(false);
  };

  const handleSync = async () => {
    setSyncing(true);
    try {
      const result = await syncContactsToBackend();
      Alert.alert(
        'Contactos Sincronizados',
        `${result.created} nuevos clientes agregados.\n${result.skipped} ya existían.\n${result.totalOnPhone} contactos en tu teléfono.`
      );
      await loadClientes();
    } catch (error) {
      Alert.alert('Error', error.message);
    }
    setSyncing(false);
  };

  const handleCall = (telefono) => {
    Linking.openURL(`tel:${telefono}`);
  };

  const renderCliente = ({ item }) => {
    const status = STATUS_COLORS[item.estado] || STATUS_COLORS.nuevo;

    return (
      <TouchableOpacity style={styles.card}>
        <View style={styles.cardHeader}>
          <View style={{ flex: 1 }}>
            <Text style={styles.nombre}>{item.nombre_apellido}</Text>
            <Text style={styles.telefono}>{item.telefono}</Text>
            {item.zona && <Text style={styles.zona}>{item.zona}</Text>}
          </View>
          <View style={[styles.badge, { backgroundColor: status.bg }]}>
            <Text style={[styles.badgeText, { color: status.text }]}>
              {status.label}
            </Text>
          </View>
        </View>
        <View style={styles.cardActions}>
          <TouchableOpacity
            style={styles.actionBtn}
            onPress={() => handleCall(item.telefono)}
          >
            <Ionicons name="call" size={18} color="#10b981" />
            <Text style={styles.actionText}>Llamar</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.actionBtn}>
            <Ionicons name="navigate" size={18} color="#3b82f6" />
            <Text style={styles.actionText}>Navegar</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.actionBtn}>
            <Ionicons name="mic" size={18} color="#a855f7" />
            <Text style={styles.actionText}>Visita</Text>
          </TouchableOpacity>
        </View>
      </TouchableOpacity>
    );
  };

  return (
    <View style={styles.container}>
      {/* Search bar */}
      <View style={styles.searchRow}>
        <View style={styles.searchBox}>
          <Ionicons name="search" size={18} color="#64748b" />
          <TextInput
            style={styles.searchInput}
            placeholder="Buscar cliente..."
            placeholderTextColor="#64748b"
            value={search}
            onChangeText={setSearch}
            onSubmitEditing={loadClientes}
          />
        </View>
        <TouchableOpacity
          style={[styles.syncBtn, syncing && styles.syncBtnDisabled]}
          onPress={handleSync}
          disabled={syncing}
        >
          <Ionicons name="sync" size={20} color="#f59e0b" />
        </TouchableOpacity>
      </View>

      {/* Client list */}
      <FlatList
        data={clientes}
        keyExtractor={(item) => String(item.id)}
        renderItem={renderCliente}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
        ListEmptyComponent={
          <View style={styles.empty}>
            <Ionicons name="people-outline" size={48} color="#475569" />
            <Text style={styles.emptyText}>
              {search ? 'No se encontraron clientes' : 'Sin clientes. Sincroniza tus contactos.'}
            </Text>
          </View>
        }
        contentContainerStyle={{ paddingBottom: 20 }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0f172a' },
  searchRow: {
    flexDirection: 'row', alignItems: 'center', gap: 8,
    paddingHorizontal: 16, paddingVertical: 12,
  },
  searchBox: {
    flex: 1, flexDirection: 'row', alignItems: 'center', gap: 8,
    backgroundColor: '#1e293b', borderRadius: 12, paddingHorizontal: 14, height: 44,
  },
  searchInput: { flex: 1, color: '#f1f5f9', fontSize: 15 },
  syncBtn: {
    width: 44, height: 44, borderRadius: 12, backgroundColor: '#1e293b',
    alignItems: 'center', justifyContent: 'center',
  },
  syncBtnDisabled: { opacity: 0.5 },
  card: {
    backgroundColor: '#1e293b', marginHorizontal: 16, marginBottom: 8,
    borderRadius: 14, padding: 16,
  },
  cardHeader: { flexDirection: 'row', alignItems: 'flex-start' },
  nombre: { color: '#f1f5f9', fontSize: 16, fontWeight: '700' },
  telefono: { color: '#94a3b8', fontSize: 13, marginTop: 2 },
  zona: { color: '#64748b', fontSize: 12, marginTop: 2 },
  badge: {
    paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12,
  },
  badgeText: { fontSize: 11, fontWeight: '700' },
  cardActions: {
    flexDirection: 'row', gap: 12, marginTop: 12,
    paddingTop: 12, borderTopWidth: 1, borderTopColor: '#334155',
  },
  actionBtn: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  actionText: { color: '#94a3b8', fontSize: 12 },
  empty: { alignItems: 'center', paddingTop: 60 },
  emptyText: { color: '#475569', fontSize: 14, marginTop: 12 },
});
