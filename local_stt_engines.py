#!/usr/bin/env python
"""
Local Speech-to-Text Engines for WhisperKey
Supports Vosk, OpenAI Whisper (local), and SpeechRecognition
"""
import os
import json
import logging
import tempfile
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod

import numpy as np
import vosk

# Set up logger first
logger = logging.getLogger("whisperkey.local_stt")

# Optional imports with graceful fallback
try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    sr = None
    SPEECH_RECOGNITION_AVAILABLE = False
    logger.warning("SpeechRecognition not available - install with: pip install SpeechRecognition PyAudio")

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    whisper = None
    WHISPER_AVAILABLE = False
    logger.warning("Whisper not available - install with: pip install openai-whisper")


class LocalSTTEngine(ABC):
    """Abstract base class for local STT engines."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.is_initialized = False
        
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the engine. Returns True if successful."""
        pass
        
    @abstractmethod
    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        """Transcribe audio data and return text."""
        pass
        
    @abstractmethod
    def cleanup(self):
        """Clean up resources."""
        pass
        
    @property
    @abstractmethod
    def name(self) -> str:
        """Engine name."""
        pass


class VoskEngine(LocalSTTEngine):
    """Vosk local STT engine."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.model = None
        self.recognizer = None
        
    @property
    def name(self) -> str:
        return "vosk"
        
    def initialize(self) -> bool:
        """Initialize Vosk model."""
        try:
            model_path = self.config.get('vosk', {}).get('model_path')
            if not model_path or not Path(model_path).exists():
                logger.error(f"Vosk model path not found: {model_path}")
                return False
                
            # Initialize Vosk model
            self.model = vosk.Model(model_path)
            self.recognizer = vosk.KaldiRecognizer(self.model, 16000)
            self.recognizer.SetWords(True)
            
            self.is_initialized = True
            logger.info(f"Vosk engine initialized with model: {model_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Vosk: {e}")
            return False
            
    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        """Transcribe audio using Vosk."""
        if not self.is_initialized:
            return ""
            
        try:
            # Convert to bytes
            audio_bytes = (audio_data * 32767).astype(np.int16).tobytes()
            
            # Process audio
            if self.recognizer.AcceptWaveform(audio_bytes):
                result = json.loads(self.recognizer.Result())
                return result.get('text', '')
            else:
                # Get partial result
                partial = json.loads(self.recognizer.PartialResult())
                return partial.get('partial', '')
                
        except Exception as e:
            logger.error(f"Vosk transcription error: {e}")
            return ""
            
    def cleanup(self):
        """Clean up Vosk resources."""
        self.model = None
        self.recognizer = None
        self.is_initialized = False


class WhisperLocalEngine(LocalSTTEngine):
    """OpenAI Whisper local STT engine."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.model = None
        
    @property
    def name(self) -> str:
        return "whisper_local"
        
    def initialize(self) -> bool:
        """Initialize Whisper model."""
        if not WHISPER_AVAILABLE:
            logger.error("Whisper not available - cannot initialize WhisperLocalEngine")
            return False
            
        try:
            model_size = self.config.get('whisper_local', {}).get('model_size', 'base')
            
            # Load Whisper model
            self.model = whisper.load_model(model_size)
            
            self.is_initialized = True
            logger.info(f"Whisper local engine initialized with model: {model_size}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Whisper local: {e}")
            return False
            
    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        """Transcribe audio using local Whisper."""
        if not self.is_initialized:
            return ""
            
        try:
            # Whisper expects float32 audio normalized to [-1, 1]
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)
                
            # Normalize if needed
            if np.max(np.abs(audio_data)) > 1.0:
                audio_data = audio_data / np.max(np.abs(audio_data))
                
            # Transcribe
            result = self.model.transcribe(audio_data)
            return result.get('text', '').strip()
            
        except Exception as e:
            logger.error(f"Whisper local transcription error: {e}")
            return ""
            
    def cleanup(self):
        """Clean up Whisper resources."""
        self.model = None
        self.is_initialized = False


class SpeechRecognitionEngine(LocalSTTEngine):
    """SpeechRecognition library engine (supports multiple backends)."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.recognizer = None
        
    @property
    def name(self) -> str:
        return "speech_recognition"
        
    def initialize(self) -> bool:
        """Initialize SpeechRecognition."""
        if not SPEECH_RECOGNITION_AVAILABLE:
            logger.error("SpeechRecognition not available - cannot initialize SpeechRecognitionEngine")
            return False
            
        try:
            self.recognizer = sr.Recognizer()
            
            # Adjust for ambient noise if configured
            if self.config.get('speech_recognition', {}).get('adjust_for_ambient_noise', True):
                # We'll adjust during transcription since we don't have a live microphone here
                pass
                
            self.is_initialized = True
            logger.info("SpeechRecognition engine initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize SpeechRecognition: {e}")
            return False
            
    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        """Transcribe audio using SpeechRecognition."""
        if not self.is_initialized:
            return ""
            
        try:
            # Convert numpy array to AudioData
            # SpeechRecognition expects 16-bit PCM
            if audio_data.dtype != np.int16:
                audio_data = (audio_data * 32767).astype(np.int16)
                
            # Create AudioData object
            audio_bytes = audio_data.tobytes()
            audio = sr.AudioData(audio_bytes, sample_rate, 2)  # 2 bytes per sample for int16
            
            # Choose recognition method
            backend = self.config.get('speech_recognition', {}).get('backend', 'google')
            
            if backend == 'google':
                return self.recognizer.recognize_google(audio)
            elif backend == 'sphinx':
                return self.recognizer.recognize_sphinx(audio)
            elif backend == 'wit':
                api_key = self.config.get('speech_recognition', {}).get('wit_api_key')
                if api_key:
                    return self.recognizer.recognize_wit(audio, key=api_key)
            elif backend == 'azure':
                api_key = self.config.get('speech_recognition', {}).get('azure_api_key')
                if api_key:
                    return self.recognizer.recognize_azure(audio, key=api_key)
                    
            return ""
            
        except sr.UnknownValueError:
            logger.debug("SpeechRecognition could not understand audio")
            return ""
        except sr.RequestError as e:
            logger.error(f"SpeechRecognition request error: {e}")
            return ""
        except Exception as e:
            logger.error(f"SpeechRecognition transcription error: {e}")
            return ""
            
    def cleanup(self):
        """Clean up SpeechRecognition resources."""
        self.recognizer = None
        self.is_initialized = False


class LocalSTTManager:
    """Manages multiple local STT engines."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.engines: Dict[str, LocalSTTEngine] = {}
        self.current_engine: Optional[LocalSTTEngine] = None
        
        # Initialize available engines
        self._initialize_engines()
        
    def _initialize_engines(self):
        """Initialize all available engines."""
        # Vosk
        if self.config.get('vosk', {}).get('model_path'):
            vosk_engine = VoskEngine(self.config)
            if vosk_engine.initialize():
                self.engines['vosk'] = vosk_engine
                
        # Whisper Local
        if WHISPER_AVAILABLE and self.config.get('whisper_local', {}).get('enabled', False):
            whisper_engine = WhisperLocalEngine(self.config)
            if whisper_engine.initialize():
                self.engines['whisper_local'] = whisper_engine
                
        # SpeechRecognition
        if SPEECH_RECOGNITION_AVAILABLE and self.config.get('speech_recognition', {}).get('enabled', False):
            sr_engine = SpeechRecognitionEngine(self.config)
            if sr_engine.initialize():
                self.engines['speech_recognition'] = sr_engine
                
        # Set default engine
        preferred_engine = self.config.get('transcription', {}).get('local_engine', 'vosk')
        if preferred_engine in self.engines:
            self.current_engine = self.engines[preferred_engine]
        elif self.engines:
            self.current_engine = next(iter(self.engines.values()))
            
        logger.info(f"Initialized local STT engines: {list(self.engines.keys())}")
        if self.current_engine:
            logger.info(f"Current engine: {self.current_engine.name}")
            
    def get_available_engines(self) -> List[str]:
        """Get list of available engine names."""
        return list(self.engines.keys())
        
    def set_engine(self, engine_name: str) -> bool:
        """Set the current engine."""
        if engine_name in self.engines:
            self.current_engine = self.engines[engine_name]
            logger.info(f"Switched to engine: {engine_name}")
            return True
        return False
        
    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        """Transcribe audio using the current engine."""
        if not self.current_engine:
            logger.error("No local STT engine available")
            return ""
            
        return self.current_engine.transcribe(audio_data, sample_rate)
        
    def cleanup(self):
        """Clean up all engines."""
        for engine in self.engines.values():
            engine.cleanup()
        self.engines.clear()
        self.current_engine = None
