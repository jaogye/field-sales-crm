/**
 * Visita — Visit recording screen.
 *
 * Always reached from the Clientes screen with clienteId + clienteNombre params.
 * Flow:
 *   1. GPS coordinates are captured silently on mount
 *   2. Rep taps Record → expo-audio captures the conversation
 *   3. Rep taps Stop → audio uploads to backend
 *   4. Whisper transcribes → GPT-4o-mini extracts CRM fields
 *   5. Result screen shows AI summary; CRM is already updated
 */
import { useState, useEffect, useRef } from 'react';
import { useLocalSearchParams, useRouter } from 'expo-router';
import {
  View, Text, StyleSheet, Alert,
  ActivityIndicator, ScrollView,
} from 'react-native';
import { TouchableOpacity } from 'react-native-gesture-handler';
import { Ionicons } from '@expo/vector-icons';
import * as Location from 'expo-location';
import audioRecorder from '../../services/audioRecorder';
import { getCurrentLocation } from '../../services/location';
import api from '../../services/api';

export default function VisitaScreen() {
  const { clienteId, clienteNombre } = useLocalSearchParams();
  const router = useRouter();

  const [isRecording, setIsRecording] = useState(false);
  const [elapsed, setElapsed] = useState('00:00');
  const [processing, setProcessing] = useState(false);
  const [result, setResult] = useState(null);
  const [visitaId, setVisitaId] = useState(null);
  const [starting, setStarting] = useState(true);
  const timerRef = useRef(null);

  // Start the visit as soon as the screen mounts
  useEffect(() => {
    initVisit();
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, []);

  const initVisit = async () => {
    try {
      // GPS — optional, don't block if unavailable
      let location = { lat: null, lng: null };
      try {
        const { status } = await Location.requestForegroundPermissionsAsync();
        if (status === 'granted') {
          location = await getCurrentLocation();
        }
      } catch (locError) {
        console.log('Location unavailable:', locError.message);
      }

      // Create visit record
      const visita = await api.crearVisita(Number(clienteId), location.lat, location.lng);
      setVisitaId(visita.id);

      // Start recording immediately
      await audioRecorder.startRecording();
      setIsRecording(true);
      setStarting(false);

      // Timer
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
      setStarting(false);
      Alert.alert('Error al iniciar visita', error.message, [
        { text: 'Volver', onPress: () => router.back() },
      ]);
    }
  };

  const stopAndProcess = async () => {
    try {
      clearInterval(timerRef.current);
      const audioResult = await audioRecorder.stopRecording();
      setIsRecording(false);
      setProcessing(true);
      const visitResult = await audioRecorder.uploadAndTranscribe(visitaId, audioResult.uri);
      setResult(visitResult);
      setProcessing(false);
    } catch (error) {
      setProcessing(false);
      Alert.alert('Error al procesar', error.message);
    }
  };

  // ── Starting screen ──────────────────────────────────────────
  if (starting) {
    return (
      <View style={[styles.container, styles.centered]}>
        <ActivityIndicator size="large" color="#a855f7" />
        <Text style={styles.statusText}>Obteniendo ubicación e iniciando grabación...</Text>
      </View>
    );
  }

  // ── Processing screen ────────────────────────────────────────
  if (processing) {
    return (
      <View style={[styles.container, styles.centered]}>
        <ActivityIndicator size="large" color="#f59e0b" />
        <Text style={styles.processingTitle}>Procesando con IA...</Text>
        <Text style={styles.processingSubtitle}>
          Transcribiendo audio y extrayendo datos del CRM
        </Text>
      </View>
    );
  }

  // ── Result screen ────────────────────────────────────────────
  if (result) {
    return (
      <ScrollView style={styles.container} contentContainerStyle={{ padding: 16 }}>
        <View style={styles.successCard}>
          <Ionicons name="checkmark-circle" size={48} color="#10b981" />
          <Text style={styles.successTitle}>CRM Actualizado</Text>
          <Text style={styles.successSubtitle}>{clienteNombre}</Text>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionLabel}>📝 Notas del Vendedor (IA)</Text>
          <Text style={styles.sectionValue}>{result.notas_vendedor || '—'}</Text>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionLabel}>📊 Resultado</Text>
          <Text style={styles.sectionValue}>{result.resultados || '—'}</Text>
        </View>

        <View style={styles.chipRow}>
          <View style={styles.chip}>
            <Text style={styles.chipLabel}>Interés</Text>
            <Text style={[styles.chipValue, {
              color: result.nivel_interes === 'alto' ? '#10b981'
                : result.nivel_interes === 'medio' ? '#f59e0b' : '#ef4444',
            }]}>
              {result.nivel_interes?.toUpperCase() || '—'}
            </Text>
          </View>
          <View style={styles.chip}>
            <Text style={styles.chipLabel}>Estado</Text>
            <Text style={[styles.chipValue, { color: '#a855f7' }]}>
              {result.estado_sugerido?.toUpperCase() || '—'}
            </Text>
          </View>
        </View>

        {result.productos_json?.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionLabel}>🛒 Productos Mencionados</Text>
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

        {result.siguiente_paso ? (
          <View style={styles.section}>
            <Text style={styles.sectionLabel}>➡️ Siguiente Paso</Text>
            <Text style={styles.sectionValue}>{result.siguiente_paso}</Text>
          </View>
        ) : null}

        <TouchableOpacity style={styles.backBtn} onPress={() => router.back()}>
          <Text style={styles.backBtnText}>Volver a Clientes</Text>
        </TouchableOpacity>
      </ScrollView>
    );
  }

  // ── Recording screen ─────────────────────────────────────────
  return (
    <View style={[styles.container, styles.centered]}>
      <View style={styles.recordingPulse}>
        <Ionicons name="mic" size={64} color="#ef4444" />
      </View>
      <Text style={styles.timer}>{elapsed}</Text>
      <Text style={styles.recordingLabel}>Grabando conversación...</Text>
      <Text style={styles.clientName}>{clienteNombre}</Text>

      <TouchableOpacity style={styles.stopBtn} onPress={stopAndProcess}>
        <Ionicons name="stop" size={32} color="#fff" />
        <Text style={styles.stopBtnText}>Detener y Procesar</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0f172a' },
  centered: { justifyContent: 'center', alignItems: 'center', padding: 24 },

  statusText: { color: '#94a3b8', fontSize: 14, marginTop: 16, textAlign: 'center' },

  processingTitle: { color: '#f59e0b', fontSize: 20, fontWeight: '700', marginTop: 20 },
  processingSubtitle: { color: '#94a3b8', fontSize: 14, marginTop: 8, textAlign: 'center' },

  // Recording
  recordingPulse: {
    width: 120, height: 120, borderRadius: 60, backgroundColor: '#7f1d1d',
    alignItems: 'center', justifyContent: 'center', marginBottom: 24,
  },
  timer: {
    color: '#f1f5f9', fontSize: 48, fontWeight: '800',
    fontVariant: ['tabular-nums'],
  },
  recordingLabel: { color: '#ef4444', fontSize: 16, fontWeight: '600', marginTop: 8 },
  clientName: { color: '#94a3b8', fontSize: 14, marginTop: 4 },
  stopBtn: {
    flexDirection: 'row', alignItems: 'center', gap: 10,
    backgroundColor: '#ef4444', borderRadius: 16,
    paddingVertical: 16, paddingHorizontal: 32, marginTop: 40,
  },
  stopBtnText: { color: '#fff', fontSize: 16, fontWeight: '700' },

  // Result
  successCard: {
    backgroundColor: '#064e3b', borderRadius: 16, padding: 24,
    alignItems: 'center', marginBottom: 16,
  },
  successTitle: { color: '#6ee7b7', fontSize: 22, fontWeight: '800', marginTop: 12 },
  successSubtitle: { color: '#94a3b8', fontSize: 14, marginTop: 4 },
  section: {
    backgroundColor: '#1e293b', borderRadius: 14, padding: 16, marginBottom: 10,
  },
  sectionLabel: { color: '#94a3b8', fontSize: 12, fontWeight: '700', marginBottom: 8 },
  sectionValue: { color: '#f1f5f9', fontSize: 14, lineHeight: 20 },
  chipRow: { flexDirection: 'row', gap: 10, marginBottom: 10 },
  chip: {
    flex: 1, backgroundColor: '#1e293b', borderRadius: 14,
    padding: 16, alignItems: 'center',
  },
  chipLabel: { color: '#64748b', fontSize: 11, fontWeight: '600' },
  chipValue: { fontSize: 16, fontWeight: '800', marginTop: 4 },
  productRow: {
    flexDirection: 'row', justifyContent: 'space-between',
    paddingVertical: 6, borderBottomWidth: 1, borderBottomColor: '#334155',
  },
  productName: { color: '#f1f5f9', fontSize: 14 },
  productPrice: { color: '#f59e0b', fontSize: 14, fontWeight: '700' },
  backBtn: {
    backgroundColor: '#f59e0b', borderRadius: 14, padding: 16,
    alignItems: 'center', marginTop: 10, marginBottom: 24,
  },
  backBtnText: { color: '#000', fontSize: 16, fontWeight: '700' },
});
