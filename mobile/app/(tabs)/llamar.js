/**
 * Call Tab — Select a client, call them, and log the result.
 * 
 * This replaces the "Notas del Telemarketing" column in the Excel.
 * Instead of calling the owner to report, the rep logs directly.
 */
import { useState, useEffect } from 'react';
import {
  View, Text, FlatList, TouchableOpacity, StyleSheet,
  Alert, Linking, TextInput,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import api from '../../services/api';

const RESULTADOS = [
  { key: 'cita', label: 'Cita', icon: 'calendar', color: '#a855f7' },
  { key: 'no_cita', label: 'No Cita', icon: 'close-circle', color: '#64748b' },
  { key: 'no_contesta', label: 'No Contesta', icon: 'call', color: '#f59e0b' },
  { key: 'venta', label: 'Venta', icon: 'checkmark-circle', color: '#10b981' },
  { key: 'equivocado', label: 'Equivocado', icon: 'alert-circle', color: '#eab308' },
  { key: 'no_llamar', label: 'No Llamar', icon: 'ban', color: '#ef4444' },
];

export default function LlamarTab() {
  const [clientes, setClientes] = useState([]);
  const [selected, setSelected] = useState(null);
  const [callStartTime, setCallStartTime] = useState(null);
  const [notas, setNotas] = useState('');
  const [search, setSearch] = useState('');

  useEffect(() => {
    loadClientes();
  }, []);

  const loadClientes = async () => {
    try {
      const data = await api.getClientes({ limit: 100 });
      // Filter out "no_llamar" clients
      setClientes(data.filter(c => c.estado !== 'no_llamar'));
    } catch (error) {
      console.error('Error:', error);
    }
  };

  const handleCall = (cliente) => {
    setSelected(cliente);
    setCallStartTime(Date.now());
    Linking.openURL(`tel:${cliente.telefono}`);
  };

  const handleResult = async (resultado) => {
    if (!selected) return;

    const duracion = callStartTime
      ? Math.round((Date.now() - callStartTime) / 1000)
      : 0;

    try {
      await api.registrarLlamada(
        selected.id,
        duracion,
        resultado,
        notas || null,
      );

      const resultLabel = RESULTADOS.find(r => r.key === resultado)?.label;
      Alert.alert(
        'Llamada Registrada',
        `${selected.nombre_apellido}\nResultado: ${resultLabel}\nDuración: ${Math.round(duracion / 60)}min`
      );

      setSelected(null);
      setCallStartTime(null);
      setNotas('');
      loadClientes();
    } catch (error) {
      Alert.alert('Error', error.message);
    }
  };

  const filteredClientes = clientes.filter(c =>
    c.nombre_apellido.toLowerCase().includes(search.toLowerCase()) ||
    c.telefono.includes(search)
  );

  // If a client is selected, show the result screen
  if (selected) {
    return (
      <View style={styles.container}>
        <View style={styles.selectedCard}>
          <Text style={styles.selectedName}>{selected.nombre_apellido}</Text>
          <Text style={styles.selectedPhone}>{selected.telefono}</Text>
          {callStartTime && (
            <Text style={styles.callTimer}>
              Llamada iniciada...
            </Text>
          )}
        </View>

        <Text style={styles.sectionTitle}>¿Cuál fue el resultado?</Text>

        <View style={styles.resultGrid}>
          {RESULTADOS.map(r => (
            <TouchableOpacity
              key={r.key}
              style={[styles.resultBtn, { borderColor: r.color }]}
              onPress={() => handleResult(r.key)}
            >
              <Ionicons name={r.icon} size={28} color={r.color} />
              <Text style={[styles.resultLabel, { color: r.color }]}>
                {r.label}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        <TextInput
          style={styles.notasInput}
          placeholder="Notas de la llamada (opcional)..."
          placeholderTextColor="#64748b"
          value={notas}
          onChangeText={setNotas}
          multiline
        />

        <TouchableOpacity
          style={styles.cancelBtn}
          onPress={() => { setSelected(null); setCallStartTime(null); }}
        >
          <Text style={styles.cancelText}>Cancelar</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.searchBox}>
        <Ionicons name="search" size={18} color="#64748b" />
        <TextInput
          style={styles.searchInput}
          placeholder="Buscar cliente para llamar..."
          placeholderTextColor="#64748b"
          value={search}
          onChangeText={setSearch}
        />
      </View>

      <FlatList
        data={filteredClientes}
        keyExtractor={item => String(item.id)}
        renderItem={({ item }) => (
          <TouchableOpacity
            style={styles.clientRow}
            onPress={() => handleCall(item)}
          >
            <View style={{ flex: 1 }}>
              <Text style={styles.clientName}>{item.nombre_apellido}</Text>
              <Text style={styles.clientPhone}>{item.telefono}</Text>
            </View>
            <Ionicons name="call" size={24} color="#10b981" />
          </TouchableOpacity>
        )}
        ListEmptyComponent={
          <Text style={styles.emptyText}>No hay clientes para llamar</Text>
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0f172a', padding: 16 },
  searchBox: {
    flexDirection: 'row', alignItems: 'center', gap: 8,
    backgroundColor: '#1e293b', borderRadius: 12, paddingHorizontal: 14,
    height: 44, marginBottom: 12,
  },
  searchInput: { flex: 1, color: '#f1f5f9', fontSize: 15 },
  clientRow: {
    flexDirection: 'row', alignItems: 'center',
    backgroundColor: '#1e293b', borderRadius: 12, padding: 16, marginBottom: 8,
  },
  clientName: { color: '#f1f5f9', fontSize: 16, fontWeight: '600' },
  clientPhone: { color: '#94a3b8', fontSize: 13, marginTop: 2 },
  selectedCard: {
    backgroundColor: '#1e293b', borderRadius: 16, padding: 24,
    alignItems: 'center', marginBottom: 24,
  },
  selectedName: { color: '#f1f5f9', fontSize: 22, fontWeight: '800' },
  selectedPhone: { color: '#94a3b8', fontSize: 16, marginTop: 4 },
  callTimer: { color: '#f59e0b', fontSize: 14, marginTop: 12, fontWeight: '600' },
  sectionTitle: {
    color: '#94a3b8', fontSize: 14, fontWeight: '700', marginBottom: 12,
    textTransform: 'uppercase', letterSpacing: 1,
  },
  resultGrid: {
    flexDirection: 'row', flexWrap: 'wrap', gap: 10, marginBottom: 16,
  },
  resultBtn: {
    width: '48%', backgroundColor: '#1e293b', borderRadius: 14,
    padding: 16, alignItems: 'center', gap: 8, borderWidth: 2,
  },
  resultLabel: { fontSize: 13, fontWeight: '700' },
  notasInput: {
    backgroundColor: '#1e293b', borderRadius: 12, padding: 14,
    color: '#f1f5f9', fontSize: 14, minHeight: 80, textAlignVertical: 'top',
    marginBottom: 12,
  },
  cancelBtn: {
    padding: 14, borderRadius: 12, alignItems: 'center',
    backgroundColor: '#334155',
  },
  cancelText: { color: '#94a3b8', fontSize: 14, fontWeight: '600' },
  emptyText: { color: '#475569', textAlign: 'center', marginTop: 40 },
});
