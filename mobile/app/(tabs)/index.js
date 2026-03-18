/**
 * Clientes — Main screen.
 *
 * Lists all clients. From each card the rep can:
 *   📞 Llamar   → opens native dialer, then shows result modal to log the call
 *   🗺️ Navegar  → opens Google Maps with client coordinates or address
 *   🎙️ Visita   → navigates to the visit recording screen
 *
 * Also supports:
 *   - Text search
 *   - Sync contacts from phone
 *   - Manual client creation (FAB)
 */
import { useState, useEffect, useCallback } from 'react';
import {
  View, Text, FlatList, TextInput, TouchableOpacity,
  StyleSheet, RefreshControl, Alert, Linking, Modal,
  ScrollView, KeyboardAvoidingView, Platform, ActivityIndicator,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { Stack } from 'expo-router';
import api from '../../services/api';

const STATUS_COLORS = {
  nuevo:       { bg: '#334155', text: '#94a3b8', label: 'Nuevo' },
  no_llamar:   { bg: '#7f1d1d', text: '#fca5a5', label: 'No Llamar' },
  venta:       { bg: '#064e3b', text: '#6ee7b7', label: 'Venta' },
  equivocado:  { bg: '#713f12', text: '#fde047', label: 'Equivocado' },
  cita:        { bg: '#581c87', text: '#d8b4fe', label: 'Cita' },
  seguimiento: { bg: '#1e3a5f', text: '#93c5fd', label: 'Seguimiento' },
};

const RESULTADOS = [
  { key: 'cita',        label: 'Cita',        icon: 'calendar',         color: '#a855f7' },
  { key: 'no_cita',     label: 'No Cita',     icon: 'close-circle',     color: '#64748b' },
  { key: 'no_contesta', label: 'No Contesta', icon: 'call',             color: '#f59e0b' },
  { key: 'venta',       label: 'Venta',       icon: 'checkmark-circle', color: '#10b981' },
  { key: 'equivocado',  label: 'Equivocado',  icon: 'alert-circle',     color: '#eab308' },
  { key: 'no_llamar',   label: 'No Llamar',   icon: 'ban',              color: '#ef4444' },
];

export default function ClientesScreen() {
  const router = useRouter();
  const [clientes, setClientes] = useState([]);
  const [search, setSearch] = useState('');
  const [refreshing, setRefreshing] = useState(false);
  // ── New client modal ──────────────────────────────────────────
  const [newClientModal, setNewClientModal] = useState(false);
  const [saving, setSaving] = useState(false);
  const [nombre, setNombre] = useState('');
  const [telefono, setTelefono] = useState('');
  const [zona, setZona] = useState('');
  const [fuente, setFuente] = useState('');

  // ── Call result modal ─────────────────────────────────────────
  const [callModal, setCallModal] = useState(false);
  const [callingClient, setCallingClient] = useState(null);
  const [callStartTime, setCallStartTime] = useState(null);
  const [callNotas, setCallNotas] = useState('');

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

  // ── New client ────────────────────────────────────────────────
  const handleCrearCliente = async () => {
    if (!nombre.trim() || !telefono.trim()) {
      Alert.alert('Error', 'Nombre y teléfono son obligatorios.');
      return;
    }
    setSaving(true);
    try {
      await api.crearCliente(nombre.trim(), telefono.trim(), zona.trim(), fuente.trim());
      setNewClientModal(false);
      setNombre(''); setTelefono(''); setZona(''); setFuente('');
      await loadClientes();
      Alert.alert('Éxito', 'Cliente creado correctamente.');
    } catch (e) {
      Alert.alert('Error', e.message || 'No se pudo crear el cliente.');
    }
    setSaving(false);
  };

  // ── Call: open dialer + show result modal ─────────────────────
  const handleCall = (cliente) => {
    setCallingClient(cliente);
    setCallStartTime(Date.now());
    setCallNotas('');
    setCallModal(true);
    Linking.openURL(`tel:${cliente.telefono}`);
  };

  const handleCallResult = async (resultado) => {
    if (!callingClient) return;
    const duracion = callStartTime
      ? Math.round((Date.now() - callStartTime) / 1000)
      : 0;
    try {
      await api.registrarLlamada(callingClient.id, duracion, resultado, callNotas || null);
      const label = RESULTADOS.find(r => r.key === resultado)?.label;
      setCallModal(false);
      setCallingClient(null);
      setCallNotas('');
      await loadClientes();
      Alert.alert('Llamada Registrada', `${callingClient.nombre_apellido}\nResultado: ${label}`);
    } catch (error) {
      Alert.alert('Error', error.message);
    }
  };

  const dismissCallModal = () => {
    setCallModal(false);
    setCallingClient(null);
    setCallNotas('');
  };

  // ── Navigate to client location ───────────────────────────────
  const handleNavegar = (cliente) => {
    let url = null;
    if (cliente.lat && cliente.lng) {
      url = `geo:${cliente.lat},${cliente.lng}?q=${cliente.lat},${cliente.lng}`;
    } else if (cliente.direccion) {
      url = `geo:0,0?q=${encodeURIComponent(cliente.direccion)}`;
    }
    if (!url) {
      Alert.alert('Sin ubicación', 'Este cliente no tiene dirección ni coordenadas registradas.');
      return;
    }
    Linking.openURL(url);
  };

  // ── Render ────────────────────────────────────────────────────
  const renderCliente = ({ item }) => {
    const status = STATUS_COLORS[item.estado] || STATUS_COLORS.nuevo;
    return (
      <View style={styles.card}>
        <View style={styles.cardHeader}>
          <View style={{ flex: 1 }}>
            <Text style={styles.nombre}>{item.nombre_apellido}</Text>
            <Text style={styles.tel}>{item.telefono}</Text>
            {item.zona ? <Text style={styles.zona}>{item.zona}</Text> : null}
          </View>
          <View style={[styles.badge, { backgroundColor: status.bg }]}>
            <Text style={[styles.badgeText, { color: status.text }]}>{status.label}</Text>
          </View>
        </View>

        <View style={styles.cardActions}>
          <TouchableOpacity style={styles.actionBtn} onPress={() => handleCall(item)}>
            <Ionicons name="call" size={18} color="#10b981" />
            <Text style={styles.actionText}>Llamar</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.actionBtn} onPress={() => handleNavegar(item)}>
            <Ionicons name="navigate" size={18} color="#3b82f6" />
            <Text style={styles.actionText}>Navegar</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.actionBtn}
            onPress={() => router.push({
              pathname: '/(tabs)/visita',
              params: { clienteId: String(item.id), clienteNombre: item.nombre_apellido },
            })}
          >
            <Ionicons name="mic" size={18} color="#a855f7" />
            <Text style={styles.actionText}>Visita</Text>
          </TouchableOpacity>
        </View>
      </View>
    );
  };

  const handleLogout = () => {
    Alert.alert(
      'Cerrar sesión',
      '¿Seguro que quieres salir?',
      [
        { text: 'Cancelar', style: 'cancel' },
        { text: 'Salir', style: 'destructive', onPress: () => api.logout() },
      ]
    );
  };

  return (
    <View style={styles.container}>

      <Stack.Screen options={{
        headerRight: () => (
          <TouchableOpacity onPress={handleLogout} style={{ marginRight: 4 }}>
            <Ionicons name="log-out-outline" size={24} color="#ef4444" />
          </TouchableOpacity>
        ),
      }} />

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
          style={[styles.iconBtn, refreshing && styles.disabled]}
          onPress={onRefresh}
          disabled={refreshing}
        >
          <Ionicons name="refresh" size={20} color="#f59e0b" />
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
              {search
                ? 'No se encontraron clientes.'
                : 'Sin clientes. Sincroniza tus contactos o agrega uno.'}
            </Text>
          </View>
        }
        contentContainerStyle={{ paddingBottom: 90 }}
      />

      {/* FAB — new client */}
      <TouchableOpacity style={styles.fab} onPress={() => setNewClientModal(true)}>
        <Ionicons name="person-add" size={24} color="#0f172a" />
      </TouchableOpacity>

      {/* ── Modal: New client ──────────────────────────────────── */}
      <Modal visible={newClientModal} animationType="slide" transparent>
        <KeyboardAvoidingView
          style={styles.overlay}
          behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        >
          <View style={styles.sheet}>
            <View style={styles.sheetHeader}>
              <Text style={styles.sheetTitle}>Nuevo Cliente</Text>
              <TouchableOpacity onPress={() => setNewClientModal(false)}>
                <Ionicons name="close" size={24} color="#94a3b8" />
              </TouchableOpacity>
            </View>
            <ScrollView showsVerticalScrollIndicator={false}>
              <Text style={styles.label}>Nombre y Apellido *</Text>
              <TextInput style={styles.input} placeholder="Ej: Juan García"
                placeholderTextColor="#475569" value={nombre}
                onChangeText={setNombre} autoCapitalize="words" />

              <Text style={styles.label}>Teléfono *</Text>
              <TextInput style={styles.input} placeholder="Ej: +1 555 123 4567"
                placeholderTextColor="#475569" value={telefono}
                onChangeText={setTelefono} keyboardType="phone-pad" />

              <Text style={styles.label}>Zona (opcional)</Text>
              <TextInput style={styles.input} placeholder="Ej: Norte, Centro..."
                placeholderTextColor="#475569" value={zona} onChangeText={setZona} />

              <Text style={styles.label}>Fuente (opcional)</Text>
              <TextInput style={styles.input} placeholder="Ej: Referido, Web..."
                placeholderTextColor="#475569" value={fuente} onChangeText={setFuente} />

              <TouchableOpacity
                style={[styles.saveBtn, saving && styles.disabled]}
                onPress={handleCrearCliente}
                disabled={saving}
              >
                {saving
                  ? <ActivityIndicator color="#0f172a" />
                  : <Text style={styles.saveBtnText}>Guardar Cliente</Text>}
              </TouchableOpacity>
            </ScrollView>
          </View>
        </KeyboardAvoidingView>
      </Modal>

      {/* ── Modal: Call result ─────────────────────────────────── */}
      <Modal visible={callModal} animationType="slide" transparent>
        <View style={styles.overlay}>
          <View style={styles.sheet}>
            <View style={styles.sheetHeader}>
              <View>
                <Text style={styles.sheetTitle}>Resultado de Llamada</Text>
                {callingClient && (
                  <Text style={styles.callClientName}>{callingClient.nombre_apellido}</Text>
                )}
              </View>
              <TouchableOpacity onPress={dismissCallModal}>
                <Ionicons name="close" size={24} color="#94a3b8" />
              </TouchableOpacity>
            </View>

            <View style={styles.resultGrid}>
              {RESULTADOS.map(r => (
                <TouchableOpacity
                  key={r.key}
                  style={[styles.resultBtn, { borderColor: r.color }]}
                  onPress={() => handleCallResult(r.key)}
                >
                  <Ionicons name={r.icon} size={26} color={r.color} />
                  <Text style={[styles.resultLabel, { color: r.color }]}>{r.label}</Text>
                </TouchableOpacity>
              ))}
            </View>

            <TextInput
              style={styles.notasInput}
              placeholder="Notas de la llamada (opcional)..."
              placeholderTextColor="#64748b"
              value={callNotas}
              onChangeText={setCallNotas}
              multiline
            />
          </View>
        </View>
      </Modal>

    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0f172a' },

  // Search bar
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

  // Client card
  card: {
    backgroundColor: '#1e293b', marginHorizontal: 16, marginBottom: 8,
    borderRadius: 14, padding: 16,
  },
  cardHeader: { flexDirection: 'row', alignItems: 'flex-start' },
  nombre: { color: '#f1f5f9', fontSize: 16, fontWeight: '700' },
  tel: { color: '#94a3b8', fontSize: 13, marginTop: 2 },
  zona: { color: '#64748b', fontSize: 12, marginTop: 2 },
  badge: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12 },
  badgeText: { fontSize: 11, fontWeight: '700' },
  cardActions: {
    flexDirection: 'row', gap: 12, marginTop: 12,
    paddingTop: 12, borderTopWidth: 1, borderTopColor: '#334155',
  },
  actionBtn: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  actionText: { color: '#94a3b8', fontSize: 12 },

  // Empty state
  empty: { alignItems: 'center', paddingTop: 60 },
  emptyText: {
    color: '#475569', fontSize: 14, marginTop: 12,
    textAlign: 'center', paddingHorizontal: 32,
  },

  // FAB
  fab: {
    position: 'absolute', bottom: 24, right: 24,
    width: 56, height: 56, borderRadius: 28,
    backgroundColor: '#10b981', alignItems: 'center', justifyContent: 'center',
    elevation: 6,
  },

  // Modals (shared)
  overlay: {
    flex: 1, backgroundColor: 'rgba(0,0,0,0.6)', justifyContent: 'flex-end',
  },
  sheet: {
    backgroundColor: '#1e293b', borderTopLeftRadius: 24, borderTopRightRadius: 24,
    padding: 24, maxHeight: '85%',
  },
  sheetHeader: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start',
    marginBottom: 20,
  },
  sheetTitle: { color: '#f1f5f9', fontSize: 18, fontWeight: '700' },
  callClientName: { color: '#94a3b8', fontSize: 14, marginTop: 2 },

  // New client form
  label: { color: '#94a3b8', fontSize: 13, marginBottom: 6, marginTop: 12 },
  input: {
    backgroundColor: '#0f172a', color: '#f1f5f9',
    borderRadius: 12, paddingHorizontal: 16, height: 48, fontSize: 15,
  },
  saveBtn: {
    backgroundColor: '#10b981', borderRadius: 12, height: 50,
    alignItems: 'center', justifyContent: 'center', marginTop: 24, marginBottom: 8,
  },
  saveBtnText: { color: '#0f172a', fontWeight: '700', fontSize: 16 },

  // Call result grid
  resultGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10, marginBottom: 16 },
  resultBtn: {
    width: '48%', backgroundColor: '#0f172a', borderRadius: 14,
    padding: 14, alignItems: 'center', gap: 6, borderWidth: 2,
  },
  resultLabel: { fontSize: 13, fontWeight: '700' },
  notasInput: {
    backgroundColor: '#0f172a', borderRadius: 12, padding: 14,
    color: '#f1f5f9', fontSize: 14, minHeight: 70, textAlignVertical: 'top',
  },

  disabled: { opacity: 0.5 },
});
