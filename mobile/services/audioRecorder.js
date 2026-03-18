/**
 * Audio Recording Service
 *
 * Records visit conversations using expo-audio (replaces deprecated expo-av).
 * Handles background recording and upload to backend.
 */
import { AudioModule, RecordingPresets, requestRecordingPermissionsAsync, setAudioModeAsync } from 'expo-audio';
import api from './api';

class AudioRecorderService {
  constructor() {
    this.recorder = null;
    this.isRecording = false;
    this.startTime = null;
  }

  async requestPermission() {
    const { granted } = await requestRecordingPermissionsAsync();
    return granted;
  }

  async startRecording() {
    /**
     * Start recording audio from the microphone.
     */
    const hasPermission = await this.requestPermission();
    if (!hasPermission) {
      throw new Error('Microphone permission denied');
    }

    // Configure audio mode for recording
    await setAudioModeAsync({
      allowsRecording: true,
      playsInSilentMode: true,
      shouldPlayInBackground: true,
    });

    this.recorder = new AudioModule.AudioRecorder(RecordingPresets.HIGH_QUALITY);
    await this.recorder.prepareToRecordAsync(RecordingPresets.HIGH_QUALITY);
    this.recorder.record();

    this.isRecording = true;
    this.startTime = Date.now();

    console.log('Recording started');
    return this.recorder;
  }

  async stopRecording() {
    /**
     * Stop recording and return the audio file URI.
     */
    if (!this.recorder || !this.isRecording) {
      throw new Error('No active recording');
    }

    await this.recorder.stop();

    // Reset audio mode
    await setAudioModeAsync({
      allowsRecording: false,
      shouldPlayInBackground: false,
    });

    const uri = this.recorder.uri;
    const durationMs = Date.now() - this.startTime;
    const durationMin = durationMs / 60000;

    this.isRecording = false;
    const result = {
      uri,
      durationMin: Math.round(durationMin * 10) / 10,
    };

    this.recorder = null;
    this.startTime = null;

    console.log(`Recording stopped: ${result.durationMin}min, ${result.sizeMB}MB`);
    return result;
  }

  async uploadAndTranscribe(visitaId, audioUri) {
    /**
     * Upload audio to backend and trigger AI transcription pipeline.
     *
     * 1. Audio file → FastAPI backend
     * 2. Backend → Whisper API (transcription)
     * 3. Transcription → GPT (extract CRM fields)
     * 4. CRM fields → SQLite (update client record)
     *
     * Returns the fully populated visit with AI-extracted data.
     */
    console.log(`Uploading audio for visit ${visitaId}...`);
    await api.subirAudio(visitaId, audioUri);

    console.log(`Transcribing visit ${visitaId}...`);
    const result = await api.transcribirVisita(visitaId);

    console.log(`Visit ${visitaId} processed:`, {
      estado: result.estado_sugerido,
      interes: result.nivel_interes,
      productos: result.productos_json?.length || 0,
    });

    return result;
  }

  getRecordingStatus() {
    if (!this.isRecording) return { isRecording: false };

    const elapsed = Date.now() - this.startTime;
    return {
      isRecording: true,
      elapsedMin: Math.round(elapsed / 60000 * 10) / 10,
      elapsedFormatted: formatDuration(elapsed),
    };
  }
}

function formatDuration(ms) {
  const totalSec = Math.floor(ms / 1000);
  const min = Math.floor(totalSec / 60);
  const sec = totalSec % 60;
  return `${min.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`;
}

export default new AudioRecorderService();
