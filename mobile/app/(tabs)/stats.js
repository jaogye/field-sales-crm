/**
 * Stats Tab — Quick stats for the sales rep.
 * The owner has a full dashboard via Streamlit on their laptop.
 * This is the rep's personal view of their performance.
 */
import { useState, useEffect } from 'react';
import {
  View, Text, ScrollView, StyleSheet, RefreshControl,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import api from '../../services/api';

export default function StatsTab() {
  const [stats, setStats] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const loadStats = async () => {
    try {
      const data = await api.getEstadisticas();
      setStats(data);
    } catch (error) {
      console.error('Error loading stats:', error);
    }
  };

  useEffect(() => { loadStats(); }, []);

  const onRefresh = async () => {
    setRefreshing(true);
    await loadStats();
    setRefreshing(false);
  };

  if (!stats) {
    return (
      <View style={[styles.container, styles.centered]}>
        <Text style={styles.loadingText}>Cargando estadísticas...</Text>
      </View>
    );
  }

  const kpis = [
    { icon: 'people', label: 'Clientes', value: stats.total_clientes, color: '#3b82f6' },
    { icon: 'call', label: 'Llamadas Hoy', value: stats.llamadas_hoy, color: '#f59e0b' },
    { icon: 'car', label: 'Visitas Hoy', value: stats.visitas_hoy, color: '#a855f7' },
    { icon: 'trending-up', label: 'Tasa de Citas', value: `${stats.tasa_citas}%`, color: '#10b981' },
    { icon: 'cash', label: 'Ventas del Mes', value: stats.ventas_mes, color: '#10b981' },
    { icon: 'person', label: 'Vendedores', value: stats.total_vendedores, color: '#64748b' },
  ];

  const statusLabels = {
    nuevo: { label: 'Nuevos', color: '#94a3b8' },
    cita: { label: 'Con Cita', color: '#a855f7' },
    seguimiento: { label: 'Seguimiento', color: '#3b82f6' },
    venta: { label: 'Venta', color: '#10b981' },
    no_llamar: { label: 'No Llamar', color: '#ef4444' },
    equivocado: { label: 'Equivocado', color: '#eab308' },
  };

  return (
    <ScrollView
      style={styles.container}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      contentContainerStyle={{ padding: 16 }}
    >
      <Text style={styles.title}>Mi Rendimiento</Text>

      {/* KPI Grid */}
      <View style={styles.kpiGrid}>
        {kpis.map((kpi, i) => (
          <View key={i} style={styles.kpiCard}>
            <Ionicons name={kpi.icon} size={24} color={kpi.color} />
            <Text style={[styles.kpiValue, { color: kpi.color }]}>{kpi.value}</Text>
            <Text style={styles.kpiLabel}>{kpi.label}</Text>
          </View>
        ))}
      </View>

      {/* Pipeline */}
      <Text style={styles.sectionTitle}>Pipeline de Clientes</Text>
      <View style={styles.pipelineCard}>
        {Object.entries(stats.por_estado || {}).map(([estado, count]) => {
          const info = statusLabels[estado] || { label: estado, color: '#64748b' };
          const total = stats.total_clientes || 1;
          const pct = Math.round((count / total) * 100);
          return (
            <View key={estado} style={styles.pipelineRow}>
              <View style={[styles.pipelineDot, { backgroundColor: info.color }]} />
              <Text style={styles.pipelineLabel}>{info.label}</Text>
              <View style={styles.pipelineBarBg}>
                <View style={[styles.pipelineBar, {
                  width: `${pct}%`, backgroundColor: info.color
                }]} />
              </View>
              <Text style={styles.pipelineCount}>{count}</Text>
            </View>
          );
        })}
      </View>

      {/* Top reps */}
      {stats.top_vendedores && stats.top_vendedores.length > 0 && (
        <>
          <Text style={styles.sectionTitle}>Top Vendedores del Mes</Text>
          <View style={styles.topCard}>
            {stats.top_vendedores.map((rep, i) => (
              <View key={i} style={styles.topRow}>
                <Text style={styles.topRank}>#{i + 1}</Text>
                <Text style={styles.topName}>{rep.nombre}</Text>
                <Text style={styles.topVisits}>{rep.visitas} visitas</Text>
              </View>
            ))}
          </View>
        </>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0f172a' },
  centered: { justifyContent: 'center', alignItems: 'center' },
  loadingText: { color: '#64748b', fontSize: 14 },
  title: { color: '#f1f5f9', fontSize: 24, fontWeight: '800', marginBottom: 16 },
  kpiGrid: {
    flexDirection: 'row', flexWrap: 'wrap', gap: 10, marginBottom: 24,
  },
  kpiCard: {
    width: '48%', backgroundColor: '#1e293b', borderRadius: 14,
    padding: 16, alignItems: 'center', gap: 6,
  },
  kpiValue: { fontSize: 28, fontWeight: '800' },
  kpiLabel: { color: '#64748b', fontSize: 12, fontWeight: '600' },
  sectionTitle: {
    color: '#94a3b8', fontSize: 13, fontWeight: '700',
    textTransform: 'uppercase', letterSpacing: 1, marginBottom: 10,
  },
  pipelineCard: {
    backgroundColor: '#1e293b', borderRadius: 14, padding: 16, marginBottom: 24,
  },
  pipelineRow: {
    flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 10,
  },
  pipelineDot: { width: 8, height: 8, borderRadius: 4 },
  pipelineLabel: { color: '#94a3b8', fontSize: 13, width: 90 },
  pipelineBarBg: {
    flex: 1, height: 8, backgroundColor: '#334155', borderRadius: 4, overflow: 'hidden',
  },
  pipelineBar: { height: '100%', borderRadius: 4 },
  pipelineCount: { color: '#f1f5f9', fontSize: 13, fontWeight: '700', width: 30, textAlign: 'right' },
  topCard: { backgroundColor: '#1e293b', borderRadius: 14, padding: 16 },
  topRow: {
    flexDirection: 'row', alignItems: 'center', gap: 10,
    paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: '#334155',
  },
  topRank: { color: '#f59e0b', fontSize: 16, fontWeight: '800', width: 30 },
  topName: { color: '#f1f5f9', fontSize: 14, flex: 1 },
  topVisits: { color: '#94a3b8', fontSize: 13 },
});
