/**
 * Login / Register screen.
 * Shown when there is no saved JWT token.
 */
import { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity,
  StyleSheet, Alert, ActivityIndicator, KeyboardAvoidingView, Platform,
} from 'react-native';
import api from '../services/api';

export default function LoginScreen() {
  const [modo, setModo] = useState('login'); // 'login' | 'registro'
  const [loading, setLoading] = useState(false);

  const [telefono, setTelefono] = useState('');
  const [password, setPassword] = useState('');
  const [nombre, setNombre] = useState('');
  const [zona, setZona] = useState('');

  const handleLogin = async () => {
    if (!telefono || !password) {
      Alert.alert('Error', 'Ingresa teléfono y contraseña');
      return;
    }
    setLoading(true);
    try {
      await api.login(telefono.trim(), password);
    } catch (e) {
      Alert.alert('Error', e.message || 'Credenciales incorrectas');
    }
    setLoading(false);
  };

  const handleRegistro = async () => {
    if (!nombre || !telefono || !password) {
      Alert.alert('Error', 'Nombre, teléfono y contraseña son obligatorios');
      return;
    }
    if (password.length < 6) {
      Alert.alert('Error', 'La contraseña debe tener al menos 6 caracteres');
      return;
    }
    setLoading(true);
    try {
      await api.registrar(nombre.trim(), telefono.trim(), password, zona.trim() || null);
    } catch (e) {
      Alert.alert('Error', e.message || 'No se pudo registrar');
    }
    setLoading(false);
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <View style={styles.card}>
        <Text style={styles.title}>Field Sales CRM</Text>
        <Text style={styles.subtitle}>
          {modo === 'login' ? 'Iniciar sesión' : 'Nuevo vendedor'}
        </Text>

        {modo === 'registro' && (
          <>
            <TextInput
              style={styles.input}
              placeholder="Nombre completo"
              placeholderTextColor="#64748b"
              value={nombre}
              onChangeText={setNombre}
              autoCapitalize="words"
            />
            <TextInput
              style={styles.input}
              placeholder="Zona (opcional)"
              placeholderTextColor="#64748b"
              value={zona}
              onChangeText={setZona}
            />
          </>
        )}

        <TextInput
          style={styles.input}
          placeholder="Teléfono"
          placeholderTextColor="#64748b"
          value={telefono}
          onChangeText={setTelefono}
          keyboardType="phone-pad"
          autoCapitalize="none"
        />
        <TextInput
          style={styles.input}
          placeholder="Contraseña"
          placeholderTextColor="#64748b"
          value={password}
          onChangeText={setPassword}
          secureTextEntry
        />

        <TouchableOpacity
          style={[styles.btn, loading && styles.btnDisabled]}
          onPress={modo === 'login' ? handleLogin : handleRegistro}
          disabled={loading}
        >
          {loading
            ? <ActivityIndicator color="#0f172a" />
            : <Text style={styles.btnText}>
                {modo === 'login' ? 'Entrar' : 'Registrarme'}
              </Text>
          }
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.switchBtn}
          onPress={() => setModo(modo === 'login' ? 'registro' : 'login')}
        >
          <Text style={styles.switchText}>
            {modo === 'login'
              ? '¿Primera vez? Registrarme'
              : 'Ya tengo cuenta. Iniciar sesión'}
          </Text>
        </TouchableOpacity>

        {modo === 'login' && (
          <TouchableOpacity
            style={styles.demoBtn}
            onPress={async () => {
              setLoading(true);
              try {
                await api.login('0000000000', 'demo1234');
              } catch (e) {
                Alert.alert('Error', e.message || 'No se pudo acceder al demo');
              }
              setLoading(false);
            }}
            disabled={loading}
          >
            <Text style={styles.demoBtnText}>Probar demo</Text>
          </TouchableOpacity>
        )}
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1, backgroundColor: '#0f172a',
    alignItems: 'center', justifyContent: 'center',
  },
  card: {
    width: '88%', backgroundColor: '#1e293b',
    borderRadius: 20, padding: 28,
  },
  title: {
    color: '#f1f5f9', fontSize: 24, fontWeight: '800',
    textAlign: 'center', marginBottom: 4,
  },
  subtitle: {
    color: '#94a3b8', fontSize: 14, textAlign: 'center', marginBottom: 24,
  },
  input: {
    backgroundColor: '#0f172a', color: '#f1f5f9',
    borderRadius: 12, paddingHorizontal: 16, height: 50,
    marginBottom: 12, fontSize: 15,
  },
  btn: {
    backgroundColor: '#10b981', borderRadius: 12,
    height: 50, alignItems: 'center', justifyContent: 'center',
    marginTop: 8,
  },
  btnDisabled: { opacity: 0.6 },
  btnText: { color: '#0f172a', fontWeight: '700', fontSize: 16 },
  switchBtn: { marginTop: 16, alignItems: 'center' },
  switchText: { color: '#3b82f6', fontSize: 13 },
  demoBtn: {
    marginTop: 20, borderWidth: 1, borderColor: '#334155',
    borderRadius: 12, height: 46, alignItems: 'center', justifyContent: 'center',
  },
  demoBtnText: { color: '#64748b', fontSize: 14 },
});
