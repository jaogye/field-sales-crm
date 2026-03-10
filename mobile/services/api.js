/**
 * API Service — Communicates with FastAPI backend on the owner's laptop.
 * 
 * The BASE_URL should point to the Cloudflare Tunnel or ngrok URL
 * that exposes the owner's laptop to the internet.
 */

// TODO: Replace with actual tunnel URL in production
const BASE_URL = __DEV__ 
  ? 'http://192.168.1.100:8000'  // Local network during development
  : 'https://ventas.your-tunnel.com';  // Cloudflare Tunnel in production

const API = `${BASE_URL}/api/v1`;

class ApiService {
  constructor() {
    this.vendedorId = null; // Set after login/registration
  }

  async request(endpoint, options = {}) {
    const url = `${API}${endpoint}`;
    const config = {
      headers: { 'Content-Type': 'application/json', ...options.headers },
      ...options,
    };

    try {
      const response = await fetch(url, config);
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || `HTTP ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error(`API Error [${endpoint}]:`, error.message);
      throw error;
    }
  }

  // ============ VENDEDORES ============

  async registrarVendedor(nombre, telefono, zona) {
    const data = await this.request('/vendedores/', {
      method: 'POST',
      body: JSON.stringify({ nombre, telefono, zona }),
    });
    this.vendedorId = data.id;
    return data;
  }

  // ============ CLIENTES ============

  async getClientes(params = {}) {
    const query = new URLSearchParams(params).toString();
    return this.request(`/clientes/?${query}`);
  }

  async syncContactos(contactos) {
    return this.request('/clientes/sync', {
      method: 'POST',
      body: JSON.stringify({
        vendedor_id: this.vendedorId,
        contactos: contactos.map(c => ({
          nombre_apellido: c.name || `${c.firstName} ${c.lastName}`.trim(),
          telefono: c.phoneNumbers?.[0]?.number || '',
        })).filter(c => c.telefono),
      }),
    });
  }

  // ============ LLAMADAS ============

  async registrarLlamada(clienteId, duracionSeg, resultado, notas = null) {
    return this.request('/llamadas/', {
      method: 'POST',
      body: JSON.stringify({
        vendedor_id: this.vendedorId,
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
        vendedor_id: this.vendedorId,
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
    return this.request(`/visitas/${visitaId}/transcribir`, {
      method: 'POST',
    });
  }

  // ============ ESTADÍSTICAS ============

  async getEstadisticas() {
    return this.request('/estadisticas/');
  }
}

export default new ApiService();
