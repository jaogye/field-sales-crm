/**
 * Location & Geofencing Service
 * 
 * Detects when a sales rep arrives at a client's address.
 * Triggers automatic audio recording on arrival.
 */
import * as Location from 'expo-location';

// NOTE: Geofencing (expo-task-manager) requires a native build — disabled in Expo Go.

export function setOnArrivalCallback(_callback) {
  // No-op in Expo Go
}

export async function requestLocationPermission() {
  const { status: foreground } = await Location.requestForegroundPermissionsAsync();
  if (foreground !== 'granted') return false;

  const { status: background } = await Location.requestBackgroundPermissionsAsync();
  return background === 'granted';
}

export async function getCurrentLocation() {
  const location = await Location.getCurrentPositionAsync({
    accuracy: Location.Accuracy.High,
  });
  return {
    lat: location.coords.latitude,
    lng: location.coords.longitude,
  };
}

export async function startGeofencing(_clients) {
  // No-op in Expo Go — requires native build
}

export async function stopGeofencing() {
  // No-op in Expo Go — requires native build
}

export function distanceBetween(lat1, lng1, lat2, lng2) {
  /**
   * Haversine distance in meters between two GPS points.
   */
  const R = 6371e3; // Earth radius in meters
  const toRad = (deg) => (deg * Math.PI) / 180;

  const dLat = toRad(lat2 - lat1);
  const dLng = toRad(lng2 - lng1);

  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) ** 2;

  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}
