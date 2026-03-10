/**
 * Visit Tab — Record the sales conversation and auto-fill CRM.
 * 
 * This is the core screen. The rep:
 * 1. Selects a client (or GPS auto-detects)
 * 2. Taps "Record" to start capturing the conversation
 * 3. Taps "Stop" when done
 * 4. Audio uploads → Whisper transcribes → GPT extracts → CRM updates
 * 
 * The owner sees the results instantly on their laptop dashboard.
 */
import { useState, useEffect, useRef } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, Alert,
  ScrollView, ActivityIndicator,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import audioRecorder from '../../services/audioRecorder';
import { getCurrentLocation } from '../../services/location';
import api from '../../services/api';

export default function VisitaTab() {
  const [clientes, setClientes] = useState([]);
  const [selectedClient, setSelectedClient] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [elapsed, setElapsed] = useState('00:00');
  const [processing, setProcessing] = useState(false);
  const [result, setResult] = useState(null);
  const [visitaId, setVisitaId] = useState(null);
  const timerRef = useRef(null);

  useEffect(() => {
    loadClientes();
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, []);

  const loadClientes = async () => {
    try {
      const data = await api.getClientes({ estado: 'cita', limit: 50 });
      setClientes(data);
    } catch (error) {
      console.error('Error:', error);
    }
  };

  const startVisit = async (cliente) => {
    try {
      setSelectedClient(cliente);

      // Get GPS location
      const location = await getCurrentLocation();

      // Create visit record in backend
      const visita = await api.crearVisita(
        cliente.id,
        location.lat,
        location.lng,
      );
      setVisitaId(visita.id);

      // Start recording
      await audioRecorder.startRecording();
      setIsRecording(true);

      // Start timer
      const startTime = Date.now();
      timerRef.current = setInterval(() => {
        const diff = Date.now() - startTime;
        const min = Math.floor(diff / 60000);
        const sec = Math.floor((diff % 60000) / 1000);
        setElapsed(
          `${min.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`
        );
      }, 1000);

    } catch (error) {
      Alert.alert('Error', error.message);
    }
  };

  const stopAndProcess = async () => {
    try {
      // Stop recording
      clearInterval(timerRef.current);
      const audioResult = await audioRecorder.stopRecording();
      setIsRecording(false);

      // Upload and transcribe
      setProcessing(true);
      const visitResult = await audioRecorder.uploadAndTranscribe(
        visitaId,
        audioResult.uri,
      );
      setResult(visitResult);
      setProcessing(false);

    } catch (error) {
      setProcessing(false);
      Alert.alert('Error al procesar', error.message);
    }
  };

  const resetVisit = () => {
    setSelectedClient(null);
    setVisitaId(null);
    setResult(null);
    setElapsed('00:00');
    loadClientes();
  };

  // ---- RESULT SCREEN ----
  if (result) {
    return (
      <ScrollView style={styles.container} contentContainerStyle={{ padding: 16 }}>
        <View style={styles.successCard}>
          <Ionicons name="checkmark-circle" size={48} color="#10b981" />
          <Text style={styles.successTitle}>CRM Actualizado</Text>
          <Text style={styles.successSubtitle}>{selectedClient?.nombre_apellido}</Text>
        </View>

        <View style={styles.resultSection}>
          <Text style={styles.resultLabel}>📝 Notas del Vendedor (IA)</Text>
          <Text style={styles.resultValue}>{result.notas_vendedor || '—'}</Text>
        </View>

        <View style={styles.resultSection}>
          <Text style={styles.resultLabel}>📊 Resultado</Text>
          <Text style={styles.resultValue}>{result.resultados || '—'}</Text>
        </View>

        <View style={styles.resultRow}>
          <View style={[styles.resultChip, { flex: 1 }]}>
            <Text style={styles.chipLabel}>Interés</Text>
            <Text style={[styles.chipValue, {
              color: result.nivel_interes === 'alto' ? '#10b981'
                : result.nivel_interes === 'medio' ? '#f59e0b' : '#ef4444'
            }]}>
              {result.nivel_interes?.toUpperCase()}
            </Text>
          </View>
          <View style={[styles.resultChip, { flex: 1 }]}>
            <Text style={styles.chipLabel}>Estado</Text>
            <Text style={[styles.chipValue, { color: '#a855f7' }]}>
              {result.estado_sugerido?.toUpperCase()}
            </Text>
          </View>
        </View>

        {result.productos_json && result.productos_json.length > 0 && (
          <View style={styles.resultSection}>
            <Text style={styles.resultLabel}>🛒 Productos Mencionados</Text>
            {result.productos_json.map((p, i) => (
              <View key={i} style={styles.productRow}>
                <Text style={styles.productName}>{p.nombre}</Text>
                <Text style={styles.productPrice}>
                  {p.precio_cotizado ? `$${p.precio_cotizado}` : '—'}
                </Text>
              </View>
            ))}
          </View>
        )}

        {result.siguiente_paso && (
          <View style={styles.resultSection}>
            <Text style={styles.resultLabel}>➡️ Siguiente Paso</Text>
            <Text style={styles.resultValue}>{result.siguiente_paso}</Text>
          </View>
        )}

        <TouchableOpacity style={styles.primaryBtn} onPress={resetVisit}>
          <Text style={styles.primaryBtnText}>Nueva Visita</Text>
        </TouchableOpacity>
      </ScrollView>
    );
  }

  // ---- RECORDING SCREEN ----
  if (isRecording || processing) {
    return (
      <View style={[styles.container, styles.centered]}>
        {processing ? (
          <>
            <ActivityIndicator size="large" color="#f59e0b" />
            <Text style={styles.processingTitle}>Procesando con IA...</Text>
            <Text style={styles.processingSubtitle}>
              Transcribiendo audio y extrayendo datos del CRM
            </Text>
          </>
        ) : (
          <>
            <View style={styles.recordingPulse}>
              <Ionicons name="mic" size={64} color="#ef4444" />
            </View>
            <Text style={styles.timer}>{elapsed}</Text>
            <Text style={styles.recordingLabel}>Grabando conversación...</Text>
            <Text style={styles.clientNameRecording}>
              {selectedClient?.nombre_apellido}
            </Text>

            <TouchableOpacity style={styles.stopBtn} onPress={stopAndProcess}>
              <Ionicons name="stop" size={32} color="#fff" />
              <Text style={styles.stopBtnText}>Detener y Procesar</Text>
            </TouchableOpacity>
          </>
        )}
      </View>
    );
  }

  // ---- CLIENT SELECTION SCREEN ----
  return (
    <View style={styles.container}>
      <View style={{ padding: 16 }}>
        <Text style={styles.pageTitle}>Nueva Visita</Text>
        <Text style={styles.pageSubtitle}>
          Selecciona el cliente que estás visitando
        </Text>
      </View>

      <ScrollView contentContainerStyle={{ paddingHorizontal: 16, paddingBottom: 20 }}>
        {clientes.length === 0 ? (
          <View style={styles.emptyState}>
            <Ionicons name="calendar-outline" size={48} color="#475569" />
            <Text style={styles.emptyText}>
              No hay clientes con cita. Haz llamadas primero.
            </Text>
          </View>
        ) : (
          clientes.map(cliente => (
            <TouchableOpacity
              key={cliente.id}
              style={styles.clientCard}
              onPress={() => startVisit(cliente)}
            >
              <View style={{ flex: 1 }}>
                <Text style={styles.clientName}>{cliente.nombre_apellido}</Text>
                <Text style={styles.clientPhone}>{cliente.telefono}</Text>
                {cliente.direccion && (
                  <Text style={styles.clientAddress}>{cliente.direccion}</Text>
                )}
              </View>
              <View style={styles.startVisitBtn}>
                <Ionicons name="mic" size={24} color="#fff" />
              </View>
            </TouchableOpacity>
          ))
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0f172a' },
  centered: { justifyContent: 'center', alignItems: 'center', padding: 24 },
  pageTitle: { color: '#f1f5f9', fontSize: 24, fontWeight: '800' },
  pageSubtitle: { color: '#64748b', fontSize: 14, marginTop: 4 },
  clientCard: {
    flexDirection: 'row', alignItems: 'center',
    backgroundColor: '#1e293b', borderRadius: 14, padding: 16, marginBottom: 10,
  },
  clientName: { color: '#f1f5f9', fontSize: 16, fontWeight: '700' },
  clientPhone: { color: '#94a3b8', fontSize: 13, marginTop: 2 },
  clientAddress: { color: '#64748b', fontSize: 12, marginTop: 2 },
  startVisitBtn: {
    width: 48, height: 48, borderRadius: 24, backgroundColor: '#a855f7',
    alignItems: 'center', justifyContent: 'center',
  },
  recordingPulse: {
    width: 120, height: 120, borderRadius: 60, backgroundColor: '#7f1d1d',
    alignItems: 'center', justifyContent: 'center', marginBottom: 24,
  },
  timer: { color: '#f1f5f9', fontSize: 48, fontWeight: '800', fontVariant: ['tabular-nums'] },
  recordingLabel: { color: '#ef4444', fontSize: 16, fontWeight: '600', marginTop: 8 },
  clientNameRecording: { color: '#94a3b8', fontSize: 14, marginTop: 4 },
  stopBtn: {
    flexDirection: 'row', alignItems: 'center', gap: 10,
    backgroundColor: '#ef4444', borderRadius: 16, paddingVertical: 16,
    paddingHorizontal: 32, marginTop: 40,
  },
  stopBtnText: { color: '#fff', fontSize: 16, fontWeight: '700' },
  processingTitle: { color: '#f59e0b', fontSize: 20, fontWeight: '700', marginTop: 20 },
  processingSubtitle: { color: '#94a3b8', fontSize: 14, marginTop: 8, textAlign: 'center' },
  successCard: {
    backgroundColor: '#064e3b', borderRadius: 16, padding: 24,
    alignItems: 'center', marginBottom: 20,
  },
  successTitle: { color: '#6ee7b7', fontSize: 22, fontWeight: '800', marginTop: 12 },
  successSubtitle: { color: '#94a3b8', fontSize: 14, marginTop: 4 },
  resultSection: {
    backgroundColor: '#1e293b', borderRadius: 14, padding: 16, marginBottom: 10,
  },
  resultLabel: { color: '#94a3b8', fontSize: 12, fontWeight: '700', marginBottom: 8 },
  resultValue: { color: '#f1f5f9', fontSize: 14, lineHeight: 20 },
  resultRow: { flexDirection: 'row', gap: 10, marginBottom: 10 },
  resultChip: {
    backgroundColor: '#1e293b', borderRadius: 14, padding: 16, alignItems: 'center',
  },
  chipLabel: { color: '#64748b', fontSize: 11, fontWeight: '600' },
  chipValue: { fontSize: 16, fontWeight: '800', marginTop: 4 },
  productRow: {
    flexDirection: 'row', justifyContent: 'space-between',
    paddingVertical: 6, borderBottomWidth: 1, borderBottomColor: '#334155',
  },
  productName: { color: '#f1f5f9', fontSize: 14 },
  productPrice: { color: '#f59e0b', fontSize: 14, fontWeight: '700' },
  primaryBtn: {
    backgroundColor: '#f59e0b', borderRadius: 14, padding: 16,
    alignItems: 'center', marginTop: 10,
  },
  primaryBtnText: { color: '#000', fontSize: 16, fontWeight: '700' },
  emptyState: { alignItems: 'center', paddingTop: 60 },
  emptyText: { color: '#475569', fontSize: 14, marginTop: 12, textAlign: 'center' },
});
