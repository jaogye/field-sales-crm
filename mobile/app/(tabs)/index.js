/**
 * Clients Tab — List of all clients with search, sync, and manual creation.
 */
import { useState, useEffect, useCallback } from 'react';
import {
  View, Text, FlatList, TextInput, TouchableOpacity,
  StyleSheet, RefreshControl, Alert, Linking, Modal,
  ScrollView, KeyboardAvoidingView, Platform, ActivityIndicator,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import api from '../../services/api';
import { syncContactsToBackend } from '../../services/contacts';

const STATUS_COLORS = {
  nuevo:      { bg: '#334155', text: '#94a3b8', label: 'Nuevo' },
  no_llamar:  { bg: '#7f1d1d', text: '#fca5a5', label: 'No Llamar' },
  venta:      { bg: '#064e3b', text: '#6ee7b7', label: 'Venta' },
  equivocado: { bg: '#713f12', text: '#fde047', label: 'Equivocado' },
  cita:       { bg: '#581c87', text: '#d8b4fe', label: 'Cita' },
  seguimiento:{ bg: '#1e3a5f', text: '#93c5fd', label: 'Seguimiento' },
};

export default function ClientesTab() {
  const [clientes, setClientes] = useState([]);
  const [search, setSearch] = useState('');
  const [refreshing, setRefreshing] = useState(false);
  const [syncing, setSyncing] = useState(false);

  // Modal state
  const [modalVisible, setModalVisible] = useState(false);
  const [saving, setSaving] = useState(false);
  const [nombre, setNombre] = useState('');
  const [telefono, setTelefono] = useState('');
  const [zona, setZona] = useState('');
  const [fuente, setFuente] = useState('');

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

  useEffect(() => { loadClientes(); }, [loadClientes]);

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

  const handleCrearCliente = async () => {
    if (!nombre.trim() || !telefono.trim()) {
      Alert.alert('Error', 'Nombre y teléfono son obligatorios.');
      return;
    }
    setSaving(true);
    try {
      await api.crearCliente(nombre.trim(), telefono.trim(), zona.trim(), fuente.trim());
      setModalVisible(false);
      setNombre(''); setTelefono(''); setZona(''); setFuente('');
      await loadClientes();
      Alert.alert('Éxito', 'Cliente creado correctamente.');
    } catch (e) {
      Alert.alert('Error', e.message || 'No se pudo crear el cliente.');
    }
    setSaving(false);
  };

  const handleCall = (tel) => Linking.openURL(`tel:${tel}`);

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
            <Text style={[styles.badgeText, { color: status.text }]}>{status.label}</Text>
          </View>
        </View>
        <View style={styles.cardActions}>
          <TouchableOpacity style={styles.actionBtn} onPress={() => handleCall(item.telefono)}>
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
      {/* Search + Sync */}
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
          style={[styles.iconBtn, syncing && styles.iconBtnDisabled]}
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
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        ListEmptyComponent={
          <View style={styles.empty}>
            <Ionicons name="people-outline" size={48} color="#475569" />
            <Text style={styles.emptyText}>
              {search ? 'No se encontraron clientes' : 'Sin clientes. Sincroniza tus contactos o agrega uno.'}
            </Text>
          </View>
        }
        contentContainerStyle={{ paddingBottom: 90 }}
      />

      {/* FAB — Nuevo cliente */}
      <TouchableOpacity style={styles.fab} onPress={() => setModalVisible(true)}>
        <Ionicons name="person-add" size={24} color="#0f172a" />
      </TouchableOpacity>

      {/* Modal — Formulario nuevo cliente */}
      <Modal visible={modalVisible} animationType="slide" transparent>
        <KeyboardAvoidingView
          style={styles.modalOverlay}
          behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        >
          <View style={styles.modalCard}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Nuevo Cliente</Text>
              <TouchableOpacity onPress={() => setModalVisible(false)}>
                <Ionicons name="close" size={24} color="#94a3b8" />
              </TouchableOpacity>
            </View>

            <ScrollView showsVerticalScrollIndicator={false}>
              <Text style={styles.label}>Nombre y Apellido *</Text>
              <TextInput
                style={styles.input}
                placeholder="Ej: Juan García"
                placeholderTextColor="#475569"
                value={nombre}
                onChangeText={setNombre}
                autoCapitalize="words"
              />

              <Text style={styles.label}>Teléfono *</Text>
              <TextInput
                style={styles.input}
                placeholder="Ej: +1 555 123 4567"
                placeholderTextColor="#475569"
                value={telefono}
                onChangeText={setTelefono}
                keyboardType="phone-pad"
              />

              <Text style={styles.label}>Zona (opcional)</Text>
              <TextInput
                style={styles.input}
                placeholder="Ej: Norte, Centro..."
                placeholderTextColor="#475569"
                value={zona}
                onChangeText={setZona}
              />

              <Text style={styles.label}>Fuente (opcional)</Text>
              <TextInput
                style={styles.input}
                placeholder="Ej: Referido, Web, Feria..."
                placeholderTextColor="#475569"
                value={fuente}
                onChangeText={setFuente}
              />

              <TouchableOpacity
                style={[styles.saveBtn, saving && styles.saveBtnDisabled]}
                onPress={handleCrearCliente}
                disabled={saving}
              >
                {saving
                  ? <ActivityIndicator color="#0f172a" />
                  : <Text style={styles.saveBtnText}>Guardar Cliente</Text>
                }
              </TouchableOpacity>
            </ScrollView>
          </View>
        </KeyboardAvoidingView>
      </Modal>
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
  iconBtn: {
    width: 44, height: 44, borderRadius: 12, backgroundColor: '#1e293b',
    alignItems: 'center', justifyContent: 'center',
  },
  iconBtnDisabled: { opacity: 0.5 },
  card: {
    backgroundColor: '#1e293b', marginHorizontal: 16, marginBottom: 8,
    borderRadius: 14, padding: 16,
  },
  cardHeader: { flexDirection: 'row', alignItems: 'flex-start' },
  nombre: { color: '#f1f5f9', fontSize: 16, fontWeight: '700' },
  telefono: { color: '#94a3b8', fontSize: 13, marginTop: 2 },
  zona: { color: '#64748b', fontSize: 12, marginTop: 2 },
  badge: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12 },
  badgeText: { fontSize: 11, fontWeight: '700' },
  cardActions: {
    flexDirection: 'row', gap: 12, marginTop: 12,
    paddingTop: 12, borderTopWidth: 1, borderTopColor: '#334155',
  },
  actionBtn: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  actionText: { color: '#94a3b8', fontSize: 12 },
  empty: { alignItems: 'center', paddingTop: 60 },
  emptyText: { color: '#475569', fontSize: 14, marginTop: 12, textAlign: 'center', paddingHorizontal: 32 },
  fab: {
    position: 'absolute', bottom: 24, right: 24,
    width: 56, height: 56, borderRadius: 28,
    backgroundColor: '#10b981', alignItems: 'center', justifyContent: 'center',
    elevation: 6,
  },
  modalOverlay: {
    flex: 1, backgroundColor: 'rgba(0,0,0,0.6)',
    justifyContent: 'flex-end',
  },
  modalCard: {
    backgroundColor: '#1e293b', borderTopLeftRadius: 24, borderTopRightRadius: 24,
    padding: 24, maxHeight: '85%',
  },
  modalHeader: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    marginBottom: 20,
  },
  modalTitle: { color: '#f1f5f9', fontSize: 18, fontWeight: '700' },
  label: { color: '#94a3b8', fontSize: 13, marginBottom: 6, marginTop: 12 },
  input: {
    backgroundColor: '#0f172a', color: '#f1f5f9',
    borderRadius: 12, paddingHorizontal: 16, height: 48, fontSize: 15,
  },
  saveBtn: {
    backgroundColor: '#10b981', borderRadius: 12, height: 50,
    alignItems: 'center', justifyContent: 'center', marginTop: 24, marginBottom: 8,
  },
  saveBtnDisabled: { opacity: 0.6 },
  saveBtnText: { color: '#0f172a', fontWeight: '700', fontSize: 16 },
});
