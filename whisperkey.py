#!/usr/bin/env python
"""
WhisperKey - A lightweight desktop dictation tool using OpenAI Whisper
"""
import os
import sys
import time
import json
import queue
import threading
import tempfile
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from collections import deque
from datetime import datetime

import yaml
import numpy as np
import sounddevice as sd
import pyperclip
import keyboard
from dotenv import load_dotenv
from PIL import Image, ImageDraw
from pystray import Icon, Menu, MenuItem
import openai
from win10toast import ToastNotifier
from rich.logging import RichHandler
import vosk

# Import custom modules
from database import TranscriptionDatabase, TranscriptionRecord
from complete_gui import CompleteWhisperKeyGUI

# Setup logging
LOG_DIR = Path(os.getenv('LOCALAPPDATA')) / 'WhisperKey' / 'logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        RichHandler(rich_tracebacks=True),
        logging.FileHandler(LOG_DIR / f"whisperkey_{time.strftime('%Y%m%d')}.log")
    ]
)
logger = logging.getLogger("whisperkey")

# Load environment variables and configuration
load_dotenv()

CONFIG_PATH = Path(__file__).parent / 'config.yaml'
DEFAULT_CONFIG = {
    'hotkey': 'ctrl+alt+enter',
    'sample_rate': 16000,
    'channels': 1,
    'audio_device_index': None,  # None for default device
    'buffer_duration': 2.0,  # seconds of pre-recording buffer
    'transcription': {
        'engine': 'openai',
        'model': 'gpt-4o-mini-transcribe',  # Updated model
        'local_model_path': None,
    },
    'tray_icon': {
        'idle_color': 'gray',
        'recording_color': 'red',
        'transcribing_color': 'blue',
    },
    'vosk': {
        'model_path': None,  # Path to Vosk model
        'model_url': 'https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip'
    }
}


class AudioRecorder:
    """Handles microphone recording with rolling buffer support."""
    
    def __init__(self, sample_rate=16000, channels=1, buffer_duration=2.0, device_index=None):
        self.sample_rate = sample_rate
        self.channels = channels
        self.device_index = device_index
        self.buffer_duration = buffer_duration
        
        # Rolling buffer for pre-recording
        buffer_size = int(sample_rate * buffer_duration)
        self.rolling_buffer = deque(maxlen=buffer_size)
        
        # Recording state
        self.recording = False
        self.recording_buffer = []
        self.stream = None
        self.buffer_stream = None
        
        # Start continuous buffering
        self.start_continuous_buffering()
        
    def buffer_callback(self, indata, frames, time_info, status):
        """Callback for continuous audio buffering."""
        if status:
            logger.warning(f"Buffer callback status: {status}")
        
        # Add to rolling buffer efficiently
        try:
            if self.channels == 1:
                # For mono, flatten the data
                audio_data = indata.flatten()
            else:
                # For multi-channel, keep as is
                audio_data = indata
            
            # Extend buffer with new data
            self.rolling_buffer.extend(audio_data)
        except Exception as e:
            logger.error(f"Buffer callback error: {e}")
    
    def recording_callback(self, indata, frames, time_info, status):
        """Callback for active recording."""
        if status:
            logger.warning(f"Recording callback status: {status}")
        if self.recording:
            self.recording_buffer.append(indata.copy())
    
    def start_continuous_buffering(self):
        """Start continuous audio buffering in background."""
        try:
            self.buffer_stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                callback=self.buffer_callback,
                device=self.device_index
            )
            self.buffer_stream.start()
            logger.info("Continuous audio buffering started")
        except Exception as e:
            logger.error(f"Failed to start continuous buffering: {e}")
    
    def start_recording(self):
        """Start active recording (in addition to buffering)."""
        self.recording = True
        self.recording_buffer = []
        
        try:
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                callback=self.recording_callback,
                device=self.device_index
            )
            self.stream.start()
            logger.info("Active recording started")
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            self.recording = False
            
    def stop_recording(self):
        """Stop recording and return complete audio including buffer."""
        if not self.recording:
            return None
            
        self.recording = False
        
        # Stop recording stream
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        
        try:
            # Combine rolling buffer + recording buffer
            combined_audio = []
            
            # Add pre-recording buffer
            if self.rolling_buffer:
                buffer_array = np.array(list(self.rolling_buffer))
                if len(buffer_array.shape) == 1:
                    buffer_array = buffer_array.reshape(-1, 1)
                combined_audio.append(buffer_array)
            
            # Add recording buffer
            if self.recording_buffer:
                recording_array = np.concatenate(self.recording_buffer, axis=0)
                combined_audio.append(recording_array)
            
            if not combined_audio:
                logger.warning("No audio recorded")
                return None
            
            # Combine all audio
            final_audio = np.concatenate(combined_audio, axis=0)
            duration = len(final_audio) / self.sample_rate
            logger.info(f"Recording stopped. Captured {duration:.2f} seconds of audio")
            
            return final_audio
            
        except Exception as e:
            logger.error(f"Error processing recorded audio: {e}")
            return None
    
    def cleanup(self):
        """Clean up audio resources."""
        self.recording = False
        
        if self.stream:
            self.stream.stop()
            self.stream.close()
            
        if self.buffer_stream:
            self.buffer_stream.stop()
            self.buffer_stream.close()


class TranscriptionWorker:
    """Handles audio transcription using OpenAI or Vosk."""
    
    def __init__(self, config):
        self.config = config
        self.transcription_queue = queue.Queue()
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        
        # Initialize OpenAI client
        openai_api_key = os.getenv("OPENAI_API_KEY")
        self.client = None
        
        if config['transcription']['engine'] == 'openai':
            if not openai_api_key:
                logger.error("OpenAI API key not found. Please set OPENAI_API_KEY in .env file.")
            else:
                try:
                    self.client = openai.OpenAI(api_key=openai_api_key)
                    logger.info("OpenAI client initialized successfully")
                except Exception as e:
                    logger.error(f"Failed to initialize OpenAI client: {e}")
                    logger.info("Trying alternative OpenAI client initialization...")
                    try:
                        # Alternative initialization without potential problematic parameters
                        import openai as openai_module
                        openai_module.api_key = openai_api_key
                        self.client = openai_module
                        logger.info("OpenAI client initialized with fallback method")
                    except Exception as e2:
                        logger.error(f"Both OpenAI initialization methods failed: {e2}")
                        self.client = None
        
        # Initialize Vosk model
        self.vosk_model = None
        self.vosk_recognizer = None
        if config['transcription']['engine'] == 'vosk':
            self._initialize_vosk()
    
    def _worker_loop(self):
        """Background worker that processes audio and gets transcriptions."""
        while True:
            try:
                audio_data, callback = self.transcription_queue.get()
                if audio_data is None:
                    continue
                    
                transcript = self.transcribe_audio(audio_data)
                if transcript:
                    callback(transcript)
                
            except Exception as e:
                logger.exception(f"Error in transcription worker: {e}")
            finally:
                self.transcription_queue.task_done()
    
    def _initialize_vosk(self):
        """Initialize Vosk model for local transcription."""
        try:
            model_path = self.config.get('vosk', {}).get('model_path')
            if not model_path or not os.path.exists(model_path):
                logger.warning("Vosk model path not found. Using default small model.")
                # You would need to download a Vosk model here
                return
            
            self.vosk_model = vosk.Model(model_path)
            self.vosk_recognizer = vosk.KaldiRecognizer(self.vosk_model, self.config['sample_rate'])
            logger.info("Vosk model initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Vosk model: {e}")
    
    def transcribe_audio(self, audio_data):
        """Transcribe audio data using the configured engine."""
        engine = self.config['transcription']['engine']
        
        if engine == 'openai':
            return self._transcribe_with_openai(audio_data)
        elif engine == 'vosk':
            return self._transcribe_with_vosk(audio_data)
        else:
            logger.error(f"Unknown transcription engine: {engine}")
            return None
    
    def _transcribe_with_openai(self, audio_data):
        """Transcribe audio using OpenAI's gpt-4o-mini-transcribe model."""
        try:
            if not self.client:
                logger.error("OpenAI client not initialized")
                return None
                
            # Save audio to a temporary file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                import scipy.io.wavfile as wavfile
                wavfile.write(temp_file.name, self.config['sample_rate'], audio_data)
                temp_filename = temp_file.name
            
            logger.info(f"Transcribing with OpenAI {self.config['transcription']['model']}...")
            
            try:
                # Try new client pattern first
                with open(temp_filename, 'rb') as audio_file:
                    if hasattr(self.client, 'audio'):
                        response = self.client.audio.transcriptions.create(
                            model=self.config['transcription']['model'],
                            file=audio_file
                        )
                        transcript = response.text
                    else:
                        # Fallback to older API pattern
                        response = self.client.Audio.transcribe(
                            model=self.config['transcription']['model'],
                            file=audio_file
                        )
                        transcript = response['text']
                        
            except Exception as api_error:
                logger.warning(f"Primary API call failed: {api_error}")
                # Try with whisper model as fallback
                logger.info("Trying with whisper-1 model as fallback...")
                with open(temp_filename, 'rb') as audio_file:
                    if hasattr(self.client, 'audio'):
                        response = self.client.audio.transcriptions.create(
                            model='whisper-1',
                            file=audio_file
                        )
                        transcript = response.text
                    else:
                        response = self.client.Audio.transcribe(
                            model='whisper-1',
                            file=audio_file
                        )
                        transcript = response['text']
            
            os.unlink(temp_filename)
            
            logger.info(f"Transcription received: {transcript[:50]}...")
            return transcript
            
        except Exception as e:
            logger.exception(f"Error transcribing with OpenAI: {e}")
            try:
                os.unlink(temp_filename)
            except:
                pass
            return None
    
    def _transcribe_with_vosk(self, audio_data):
        """Transcribe audio using Vosk local model."""
        try:
            if not self.vosk_recognizer:
                logger.error("Vosk recognizer not initialized")
                return None
            
            # Convert audio data to the format Vosk expects
            if len(audio_data.shape) > 1:
                audio_data = audio_data.flatten()
            
            # Convert to 16-bit integers
            audio_int16 = (audio_data * 32767).astype(np.int16)
            
            # Process audio in chunks
            chunk_size = 4000
            for i in range(0, len(audio_int16), chunk_size):
                chunk = audio_int16[i:i+chunk_size]
                self.vosk_recognizer.AcceptWaveform(chunk.tobytes())
            
            # Get final result
            result = json.loads(self.vosk_recognizer.FinalResult())
            transcript = result.get('text', '')
            
            if transcript:
                logger.info(f"Vosk transcription: {transcript[:50]}...")
            else:
                logger.warning("No transcription from Vosk")
            
            return transcript
            
        except Exception as e:
            logger.exception(f"Error transcribing with Vosk: {e}")
            return None
    
    def queue_transcription(self, audio_data, callback):
        """Queue audio data for transcription."""
        self.transcription_queue.put((audio_data, callback))


class WhisperKeyApp:
    """Main application class for WhisperKey."""
    
    def __init__(self):
        self.load_config()
        
        # Initialize database
        self.db = TranscriptionDatabase()
        
        # Initialize components
        self.recorder = AudioRecorder(
            sample_rate=self.config['sample_rate'],
            channels=self.config['channels'],
            buffer_duration=self.config['buffer_duration'],
            device_index=self.config.get('audio_device_index')
        )
        self.transcriber = TranscriptionWorker(self.config)
        self.toast = ToastNotifier()
        
        # Initialize GUI
        self.gui = CompleteWhisperKeyGUI(self)
        
        # GUI mainloop will be started in main() function
        # This ensures GUI events can be processed properly
        
        # Setup tray icon
        self.setup_tray_icon()
        
        # Register global hotkey
        self.setup_hotkey()
        
        self.is_recording = False
        logger.info("WhisperKey initialized")
    
    def load_config(self):
        """Load configuration from file or create default."""
        try:
            if CONFIG_PATH.exists():
                with open(CONFIG_PATH, 'r') as f:
                    self.config = yaml.safe_load(f)
                logger.info(f"Configuration loaded from {CONFIG_PATH}")
            else:
                self.config = DEFAULT_CONFIG
                with open(CONFIG_PATH, 'w') as f:
                    yaml.dump(self.config, f, default_flow_style=False)
                logger.info(f"Default configuration created at {CONFIG_PATH}")
        except Exception as e:
            logger.exception(f"Error loading configuration: {e}")
            self.config = DEFAULT_CONFIG
    
    def create_tray_icon_image(self, color):
        """Create a colored circle image for the tray icon."""
        width, height = 64, 64
        image = Image.new('RGBA', (width, height), color=(0, 0, 0, 0))
        dc = ImageDraw.Draw(image)
        
        # Map color names to RGB
        color_map = {
            'gray': (128, 128, 128),
            'red': (255, 0, 0),
            'blue': (0, 0, 255),
        }
        rgb_color = color_map.get(color, (128, 128, 128))
        
        # Draw a circle
        dc.ellipse([8, 8, width-8, height-8], fill=rgb_color)
        return image
    
    def setup_tray_icon(self):
        """Setup the system tray icon and menu."""
        menu = Menu(
            MenuItem('Open WhisperKey', self.show_gui),
            MenuItem('About', self.show_about),
            MenuItem('Exit', self.exit_app)
         )
        
        self.icon_image = self.create_tray_icon_image(self.config['tray_icon']['idle_color'])
        self.tray_icon = Icon(
            'whisperkey',
            self.icon_image,
            'WhisperKey (Idle)',
            menu=menu
        )
        
        # Start the icon in a separate thread
        threading.Thread(target=self.tray_icon.run, daemon=True).start()
    
    def update_tray_icon(self, status, title=None):
        """Update the tray icon appearance based on status."""
        if status == 'idle':
            color = self.config['tray_icon']['idle_color']
            title = 'WhisperKey (Idle)'
        elif status == 'recording':
            color = self.config['tray_icon']['recording_color']
            title = 'WhisperKey (Recording)'
        elif status == 'transcribing':
            color = self.config['tray_icon']['transcribing_color']
            title = 'WhisperKey (Transcribing)'
        
        self.icon_image = self.create_tray_icon_image(color)
        self.tray_icon.icon = self.icon_image
        if title:
            self.tray_icon.title = title
    
    def setup_hotkey(self):
        """Register the global hotkey for recording."""
        try:
            # Register the hotkey using keyboard library
            # Note: keyboard library will automatically handle existing hotkeys
            keyboard.add_hotkey(
                self.config['hotkey'],
                self.toggle_recording,
                suppress=True
            )
            logger.info(f"Hotkey registered: {self.config['hotkey']}")
        except Exception as e:
            logger.exception(f"Error registering hotkey: {e}")
            # Try alternative registration method
            try:
                logger.info("Trying alternative hotkey registration...")
                keyboard.on_hotkey(
                    self.config['hotkey'],
                    self.toggle_recording
                )
                logger.info(f"Hotkey registered with alternative method: {self.config['hotkey']}")
            except Exception as e2:
                logger.error(f"Both hotkey registration methods failed: {e2}")
    
    def update_hotkey(self):
        """Update hotkey registration with new settings."""
        self.setup_hotkey()
    
    def toggle_recording(self):
        """Toggle recording state when hotkey is pressed."""
        if not self.is_recording:
            # Start recording
            self.is_recording = True
            self.recording_start_time = time.time()
            self.update_tray_icon('recording')
            
            if self.gui:
                self.gui.update_status("Recording...")
            
            self.recorder.start_recording()
        else:
            # Stop recording and process audio
            self.is_recording = False
            recording_duration = time.time() - getattr(self, 'recording_start_time', time.time())
            self.update_tray_icon('transcribing')
            
            if self.gui:
                self.gui.update_status("Transcribing...")
            
            audio_data = self.recorder.stop_recording()
            
            if audio_data is not None and len(audio_data) > 0:
                def transcription_callback(transcript):
                    self.handle_transcription(transcript, self.recording_start_time, recording_duration)
                
                self.transcriber.queue_transcription(
                    audio_data,
                    transcription_callback
                )
            else:
                self.update_tray_icon('idle')
                if self.gui:
                    self.gui.update_status("Idle")
    
    def handle_transcription(self, transcript, start_time=None, audio_duration=0.0):
        """Process the transcription result."""
        if transcript:
            # Copy to clipboard
            pyperclip.copy(transcript)
            
            # Save to database
            try:
                record = TranscriptionRecord(
                    timestamp=datetime.now().isoformat(),
                    text=transcript,
                    duration_seconds=audio_duration,
                    engine=self.config['transcription']['engine'],
                    model=self.config['transcription']['model'],
                    audio_device=str(self.config.get('audio_device_index', 'default')),
                    hotkey_used=self.config['hotkey'],
                    processing_time_ms=int((time.time() - (start_time or time.time())) * 1000)
                )
                self.db.add_transcription(record)
                
                # Update GUI if visible
                if self.gui and self.gui.is_visible:
                    self.gui.update_recent_transcriptions()
                    
            except Exception as e:
                logger.error(f"Error saving transcription to database: {e}")
            
            # Show notification
            self.toast.show_toast(
                "WhisperKey",
                "Transcription copied to clipboard!",
                duration=3,
                threaded=True
            )
            
            logger.info("Transcription copied to clipboard")
        
        # Reset tray icon
        self.update_tray_icon('idle')
        
        # Update GUI status
        if self.gui:
            self.gui.update_status("Idle")
    
    def show_gui(self):
        """Show the main GUI window."""
        if self.gui:
            self.gui.show_window()
    
    def save_config(self):
        """Save current configuration to file."""
        try:
            with open(CONFIG_PATH, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False)
            logger.info("Configuration saved")
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
    
    def show_about(self):
        """Show about dialog."""
        self.toast.show_toast(
            "About WhisperKey",
            "WhisperKey v0.1.0\nA lightweight desktop dictation tool",
            duration=5,
            threaded=True
        )
    
    def exit_app(self):
        """Exit the application."""
        logger.info("Exiting WhisperKey")
        
        # Cleanup resources
        if self.recorder:
            self.recorder.cleanup()
        
        # Cleanup GUI
        if self.gui:
            self.gui.cleanup()
        
        # Clear keyboard hotkeys
        try:
            keyboard.unhook_all()
        except:
            pass
        
        self.tray_icon.stop()
        sys.exit(0)


def main():
    """Main entry point for the application."""
    try:
        app = WhisperKeyApp()
        
        # Start tkinter mainloop to process GUI events
        # This replaces the simple sleep loop and enables GUI functionality
        logger.info("Starting tkinter mainloop for GUI event processing")
        
        if app.gui and app.gui.window:
            # Run tkinter mainloop on main thread
            app.gui.window.mainloop()
        else:
            # Fallback to sleep loop if no GUI
            logger.warning("No GUI window available, using fallback sleep loop")
            while True:
                time.sleep(1)
                
    except KeyboardInterrupt:
        logger.info("Application terminated by user")
    except Exception as e:
        logger.exception(f"Unhandled exception: {e}")


if __name__ == "__main__":
    main()
