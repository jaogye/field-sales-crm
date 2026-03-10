/**
 * Audio Recording Service
 * 
 * Records visit conversations using expo-av.
 * Handles background recording, pause/resume, and upload to backend.
 */
import { Audio } from 'expo-av';
import * as FileSystem from 'expo-file-system';
import api from './api';

class AudioRecorder {
  constructor() {
    this.recording = null;
    this.isRecording = false;
    this.startTime = null;
  }

  async requestPermission() {
    const { status } = await Audio.requestPermissionsAsync();
    return status === 'granted';
  }

  async startRecording() {
    /**
     * Start recording audio from the microphone.
     * Uses high-quality settings for clear voice capture.
     */
    const hasPermission = await this.requestPermission();
    if (!hasPermission) {
      throw new Error('Microphone permission denied');
    }

    // Configure audio mode for recording
    await Audio.setAudioModeAsync({
      allowsRecordingIOS: true,
      playsInSilentModeIOS: true,
      staysActiveInBackground: true, // Keep recording in background
    });

    const { recording } = await Audio.Recording.createAsync(
      {
        // High quality voice recording
        android: {
          extension: '.m4a',
          outputFormat: Audio.AndroidOutputFormat.MPEG_4,
          audioEncoder: Audio.AndroidAudioEncoder.AAC,
          sampleRate: 44100,
          numberOfChannels: 1, // Mono is enough for voice
          bitRate: 128000,
        },
        ios: {
          extension: '.m4a',
          outputFormat: Audio.IOSOutputFormat.MPEG4AAC,
          audioQuality: Audio.IOSAudioQuality.HIGH,
          sampleRate: 44100,
          numberOfChannels: 1,
          bitRate: 128000,
        },
      }
    );

    this.recording = recording;
    this.isRecording = true;
    this.startTime = Date.now();

    console.log('Recording started');
    return recording;
  }

  async stopRecording() {
    /**
     * Stop recording and return the audio file URI.
     */
    if (!this.recording || !this.isRecording) {
      throw new Error('No active recording');
    }

    await this.recording.stopAndUnloadAsync();

    // Reset audio mode
    await Audio.setAudioModeAsync({
      allowsRecordingIOS: false,
      staysActiveInBackground: false,
    });

    const uri = this.recording.getURI();
    const durationMs = Date.now() - this.startTime;
    const durationMin = durationMs / 60000;

    // Get file info
    const fileInfo = await FileSystem.getInfoAsync(uri);

    this.isRecording = false;
    const result = {
      uri,
      durationMin: Math.round(durationMin * 10) / 10,
      sizeMB: Math.round((fileInfo.size / (1024 * 1024)) * 100) / 100,
    };

    this.recording = null;
    this.startTime = null;

    console.log(`Recording stopped: ${result.durationMin}min, ${result.sizeMB}MB`);
    return result;
  }

  async uploadAndTranscribe(visitaId, audioUri) {
    /**
     * Upload audio to backend and trigger AI transcription pipeline.
     * 
     * This is where the magic happens:
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

export default new AudioRecorder();
