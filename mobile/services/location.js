/**
 * Location & Geofencing Service
 * 
 * Detects when a sales rep arrives at a client's address.
 * Triggers automatic audio recording on arrival.
 */
import * as Location from 'expo-location';
import * as TaskManager from 'expo-task-manager';

const GEOFENCE_TASK = 'GEOFENCE_TASK';
const GEOFENCE_RADIUS = 100; // meters — triggers when within 100m of client

// Callback registry for geofence events
let onArrivalCallback = null;

export function setOnArrivalCallback(callback) {
  onArrivalCallback = callback;
}

// Define the background task for geofencing
TaskManager.defineTask(GEOFENCE_TASK, ({ data, error }) => {
  if (error) {
    console.error('Geofence task error:', error.message);
    return;
  }

  if (data?.eventType === Location.GeofencingEventType.Enter) {
    const region = data.region;
    console.log(`Arrived at client location: ${region.identifier}`);
    
    if (onArrivalCallback) {
      onArrivalCallback(region);
    }
  }

  if (data?.eventType === Location.GeofencingEventType.Exit) {
    console.log(`Left client location: ${data.region.identifier}`);
  }
});

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

export async function startGeofencing(clients) {
  /**
   * Start monitoring geofences for a list of clients.
   * 
   * @param clients - Array of { id, nombre_apellido, lat, lng }
   *                  Only clients with GPS coordinates are monitored.
   */
  const regions = clients
    .filter(c => c.lat && c.lng)
    .map(c => ({
      identifier: String(c.id),
      latitude: c.lat,
      longitude: c.lng,
      radius: GEOFENCE_RADIUS,
      notifyOnEnter: true,
      notifyOnExit: true,
    }));

  if (regions.length === 0) {
    console.log('No clients with GPS coordinates to monitor');
    return;
  }

  await Location.startGeofencingAsync(GEOFENCE_TASK, regions);
  console.log(`Monitoring ${regions.length} client locations`);
}

export async function stopGeofencing() {
  const isRegistered = await TaskManager.isTaskRegisteredAsync(GEOFENCE_TASK);
  if (isRegistered) {
    await Location.stopGeofencingAsync(GEOFENCE_TASK);
  }
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
