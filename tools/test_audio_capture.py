#!/usr/bin/env python3
"""
Audio capture test script.

This script tests audio capture functionality and saves it to a WAV file
that can be used for testing speech recognition engines.
"""

import os
import sys
import wave
import tempfile
import logging
import audioop
import struct
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)

logger = logging.getLogger("audio_test")

# Add project root to path for imports
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def save_audio_to_wav(audio_data, filename, channels=1, sample_width=2, sample_rate=16000):
    """Save raw audio data to a proper WAV file."""
    with wave.open(filename, 'wb') as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_data)
    return filename

def main():
    """Capture audio and save it to a WAV file."""
    print("=== Audio Capture Test ===")
    
    try:
        import pyaudio
        
        # PyAudio configuration
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 16000
        CHUNK = 1024
        RECORD_SECONDS = 5
        
        print(f"✓ PyAudio imported successfully")
        
        # Initialize PyAudio
        p = pyaudio.PyAudio()
        print("✓ PyAudio initialized")
        
        # List available devices
        info = p.get_host_api_info_by_index(0)
        num_devices = info.get('deviceCount')
        
        print(f"\nAvailable input devices:")
        for i in range(num_devices):
            device_info = p.get_device_info_by_host_api_device_index(0, i)
            if device_info.get('maxInputChannels') > 0:
                print(f"  {i}: {device_info.get('name')}")
        
        # Open stream
        print(f"\nOpening audio stream (format: {FORMAT}, channels: {CHANNELS}, rate: {RATE})")
        stream = p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK
        )
        
        print(f"✓ Stream opened successfully")
        
        # Start recording
        print(f"\nRecording {RECORD_SECONDS} seconds of audio - please speak something...")
        
        frames = []
        for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)
        
        print(f"✓ Recording complete, captured {len(frames)} frames")
        
        # Stop and close the stream
        stream.stop_stream()
        stream.close()
        p.terminate()
        print(f"✓ Stream closed")
        
        # Combine all frames into a single audio buffer
        audio_data = b''.join(frames)
        print(f"✓ Combined audio data: {len(audio_data)} bytes")
        
        # Calculate audio properties
        max_amplitude = max(struct.unpack('h', audio_data[i:i+2])[0] for i in range(0, len(audio_data), 2))
        rms = audioop.rms(audio_data, 2)  # 2 bytes per sample (16-bit)
        print(f"Audio stats: max amplitude = {max_amplitude}, RMS = {rms}")
        
        # Save audio to a WAV file
        output_path = os.path.join(tempfile.gettempdir(), "test_recording.wav")
        save_audio_to_wav(audio_data, output_path)
        print(f"\n✓ Audio saved to: {output_path}")
        print(f"  Size: {os.path.getsize(output_path)} bytes")
        
        print("\nYou can use this WAV file for testing speech recognition engines.")
        return 0
        
    except Exception as e:
        print(f"✗ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())