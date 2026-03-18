/**
 * API Service — Communicates with the FastAPI backend on Fly.io.
 */
import AsyncStorage from '@react-native-async-storage/async-storage';

let _onAuthChange = null;
export function setAuthChangeHandler(fn) { _onAuthChange = fn; }

const BASE_URL = 'https://field-sales-crm.fly.dev';  // Fly.io

const API = `${BASE_URL}/api/v1`;
const TOKEN_KEY = 'crm_token';
const VENDEDOR_ID_KEY = 'crm_vendedor_id';

class ApiService {
  constructor() {
    this.token = null;
    this.vendedorId = null;
  }

  // Call once on app start to restore session from storage
  async loadToken() {
    try {
      this.token = await AsyncStorage.getItem(TOKEN_KEY);
      const vid = await AsyncStorage.getItem(VENDEDOR_ID_KEY);
      this.vendedorId = vid ? parseInt(vid, 10) : null;
    } catch {}
  }

  async _saveSession(token, vendedorId) {
    this.token = token;
    this.vendedorId = vendedorId;
    await AsyncStorage.setItem(TOKEN_KEY, token);
    await AsyncStorage.setItem(VENDEDOR_ID_KEY, String(vendedorId));
    if (_onAuthChange) _onAuthChange(true);
  }

  async logout() {
    this.token = null;
    this.vendedorId = null;
    await AsyncStorage.removeItem(TOKEN_KEY);
    await AsyncStorage.removeItem(VENDEDOR_ID_KEY);
    if (_onAuthChange) _onAuthChange(false);
  }

  async request(endpoint, options = {}, requiresAuth = true) {
    const url = `${API}${endpoint}`;
    const headers = { 'Content-Type': 'application/json', ...options.headers };
    if (requiresAuth && this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }
    try {
      const response = await fetch(url, { ...options, headers });
      if (!response.ok) {
        if (response.status === 401) {
          await this.logout();
          if (_onAuthChange) _onAuthChange(false);
        }
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || `HTTP ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error(`API Error [${endpoint}]:`, error.message);
      throw error;
    }
  }

  // ============ AUTH ============

  async login(telefono, password) {
    const data = await this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ telefono, password }),
    }, false);
    await this._saveSession(data.access_token, data.vendedor_id);
    return data;
  }

  async registrar(nombre, telefono, password, zona) {
    await this.request('/vendedores/', {
      method: 'POST',
      body: JSON.stringify({ nombre, telefono, password, zona: zona || null }),
    }, false);
    return this.login(telefono, password);
  }

  // ============ CLIENTES ============

  async getClientes(params = {}) {
    const query = new URLSearchParams(params).toString();
    return this.request(`/clientes/?${query}`);
  }

  async crearCliente(nombre_apellido, telefono, zona, fuente) {
    return this.request('/clientes/', {
      method: 'POST',
      body: JSON.stringify({
        nombre_apellido,
        telefono,
        zona: zona || null,
        fuente: fuente || null,
      }),
    });
  }

  async syncContactos(contactos) {
    return this.request('/clientes/sync', {
      method: 'POST',
      body: JSON.stringify({
        contactos: contactos
          .map(c => ({
            nombre_apellido: c.name || `${c.firstName} ${c.lastName}`.trim(),
            telefono: c.phoneNumbers?.[0]?.number || '',
          }))
          .filter(c => c.telefono),
      }),
    });
  }

  // ============ LLAMADAS ============

  async registrarLlamada(clienteId, duracionSeg, resultado, notas = null) {
    return this.request('/llamadas/', {
      method: 'POST',
      body: JSON.stringify({
        cliente_id: clienteId,
        duracion_seg: duracionSeg,
        resultado,
        notas_telemarketing: notas,
      }),
    });
  }

  // ============ VISITAS ============

  async crearVisita(clienteId, lat, lng) {
    return this.request('/visitas/', {
      method: 'POST',
      body: JSON.stringify({
        cliente_id: clienteId,
        lat,
        lng,
      }),
    });
  }

  async subirAudio(visitaId, audioUri) {
    const formData = new FormData();
    formData.append('audio', {
      uri: audioUri,
      name: `visita_${visitaId}.m4a`,
      type: 'audio/m4a',
    });
    return this.request(`/visitas/${visitaId}/audio`, {
      method: 'POST',
      headers: { 'Content-Type': 'multipart/form-data' },
      body: formData,
    });
  }

  async transcribirVisita(visitaId) {
    return this.request(`/visitas/${visitaId}/transcribir`, { method: 'POST' });
  }

  // ============ ESTADÍSTICAS ============

  async getEstadisticas() {
    return this.request('/estadisticas/');
  }
}

export default new ApiService();
