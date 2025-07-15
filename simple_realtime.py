#!/usr/bin/env python
"""
Simplified Real-time Streaming Transcription for WhisperKey
Uses OpenAI's standard API with streaming approach instead of WebSocket Realtime API
"""
import os
import time
import logging
import threading
import tempfile
from typing import Optional, Callable
import queue

import numpy as np
import sounddevice as sd
import openai
from scipy.io import wavfile

logger = logging.getLogger("whisperkey.simple_realtime")


class SimpleRealtimeTranscription:
    """Simple real-time transcription using OpenAI's standard API with chunked audio."""
    
    def __init__(self, config: dict, on_transcript: Callable[[str], None]):
        self.config = config
        self.on_transcript = on_transcript
        
        # OpenAI client
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OpenAI API key not found. Please set OPENAI_API_KEY environment variable.")
        
        self.openai_client = openai.OpenAI(api_key=api_key)
        
        # Audio configuration
        self.sample_rate = 16000  # Standard for Whisper
        self.channels = 1
        self.chunk_duration = 4.0  # Increased to 4 seconds for better context
        self.overlap_duration = 0.2  # Reduced overlap to minimize repetition
        self.silence_threshold = 0.01  # Threshold for silence detection
        self.min_chunk_duration = 1.0  # Minimum chunk duration to process
        
        # Recording state
        self.is_recording = False
        self.audio_stream = None
        self.audio_buffer = queue.Queue()
        self.processing_thread = None
        
        # Buffer for audio chunks
        self.current_chunk = []
        self.chunk_size = int(self.sample_rate * self.chunk_duration)
        self.overlap_size = int(self.sample_rate * self.overlap_duration)
        self.min_chunk_size = int(self.sample_rate * self.min_chunk_duration)
        
        # Deduplication
        self.last_transcript = ""
        self.transcript_history = []  # Keep last few transcripts to avoid repetition
        
    def audio_callback(self, indata, frames, time, status):
        """Audio input callback."""
        if status:
            logger.warning(f"Audio callback status: {status}")
            
        if self.is_recording:
            # Convert to mono and add to current chunk
            audio_data = indata.flatten() if self.channels == 1 else indata[:, 0]
            self.current_chunk.extend(audio_data)
            
            # If chunk is full, queue it for processing
            if len(self.current_chunk) >= self.chunk_size:
                chunk_array = np.array(self.current_chunk[:self.chunk_size])
                
                # Check if chunk has sufficient audio (not just silence/noise)
                if self.has_speech(chunk_array):
                    self.audio_buffer.put(chunk_array)
                
                # Keep overlap for next chunk
                self.current_chunk = self.current_chunk[self.chunk_size - self.overlap_size:]
    
    def has_speech(self, audio_data: np.ndarray) -> bool:
        """Check if audio chunk contains speech (not just silence or noise)."""
        # Calculate RMS (Root Mean Square) energy
        rms = np.sqrt(np.mean(audio_data ** 2))
        
        # Check if RMS is above silence threshold
        if rms < self.silence_threshold:
            return False
            
        # Additional check: look for sustained audio activity
        # Split into smaller segments and check how many have activity
        segment_size = len(audio_data) // 10  # 10 segments
        active_segments = 0
        
        for i in range(0, len(audio_data), segment_size):
            segment = audio_data[i:i + segment_size]
            if len(segment) > 0:
                segment_rms = np.sqrt(np.mean(segment ** 2))
                if segment_rms > self.silence_threshold:
                    active_segments += 1
        
        # Require at least 30% of segments to have activity
        return active_segments >= 3
    
    def is_new_content(self, transcript: str) -> bool:
        """Check if transcript contains new content (not repetition)."""
        if not transcript:
            return False
            
        # Convert to lowercase for comparison
        transcript_lower = transcript.lower().strip()
        
        # Skip very short transcripts (likely noise)
        if len(transcript_lower) < 3:
            return False
            
        # Check against last transcript
        if self.last_transcript:
            last_lower = self.last_transcript.lower().strip()
            
            # Skip if identical
            if transcript_lower == last_lower:
                return False
                
            # Skip if current is substring of last (partial repetition)
            if transcript_lower in last_lower or last_lower in transcript_lower:
                # Only allow if current is significantly longer
                if len(transcript_lower) <= len(last_lower) * 1.5:
                    return False
        
        # Check against recent history
        for hist_transcript in self.transcript_history[-3:]:  # Check last 3
            hist_lower = hist_transcript.lower().strip()
            
            # Skip if too similar
            if transcript_lower == hist_lower:
                return False
                
            # Calculate similarity (simple word overlap)
            transcript_words = set(transcript_lower.split())
            hist_words = set(hist_lower.split())
            
            if transcript_words and hist_words:
                overlap = len(transcript_words & hist_words)
                similarity = overlap / max(len(transcript_words), len(hist_words))
                
                # Skip if more than 70% similar
                if similarity > 0.7:
                    return False
        
        return True
                
    def process_audio_chunks(self):
        """Process audio chunks in background thread."""
        while self.is_recording:
            try:
                # Get audio chunk with timeout
                try:
                    audio_chunk = self.audio_buffer.get(timeout=1.0)
                except queue.Empty:
                    continue
                    
                # Skip if chunk is too short
                if len(audio_chunk) < self.min_chunk_size:
                    continue
                    
                # Transcribe the chunk
                transcript = self.transcribe_chunk(audio_chunk)
                
                if transcript and transcript.strip():
                    clean_transcript = transcript.strip()
                    
                    # Apply deduplication
                    if self.is_new_content(clean_transcript):
                        # Send transcript to callback
                        self.on_transcript(clean_transcript)
                        
                        # Update history
                        self.last_transcript = clean_transcript
                        self.transcript_history.append(clean_transcript)
                        
                        # Keep only last 5 transcripts for comparison
                        if len(self.transcript_history) > 5:
                            self.transcript_history.pop(0)
                    
            except Exception as e:
                logger.error(f"Error processing audio chunk: {e}")
                
    def transcribe_chunk(self, audio_data: np.ndarray) -> str:
        """Transcribe a single audio chunk using OpenAI API."""
        try:
            # Create temporary WAV file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                # Convert to int16 for WAV format
                audio_int16 = (audio_data * 32767).astype(np.int16)
                wavfile.write(temp_file.name, self.sample_rate, audio_int16)
                temp_filename = temp_file.name
            
            # Transcribe using OpenAI
            with open(temp_filename, 'rb') as audio_file:
                response = self.openai_client.audio.transcriptions.create(
                    model="whisper-1",  # Use standard Whisper model for reliability
                    file=audio_file,
                    language=self.config.get('realtime', {}).get('language', 'en')
                )
                transcript = response.text
            
            # Clean up temp file
            os.unlink(temp_filename)
            
            return transcript
            
        except Exception as e:
            logger.error(f"Error transcribing audio chunk: {e}")
            return ""
            
    def start_recording(self) -> bool:
        """Start real-time recording and transcription."""
        if self.is_recording:
            return True
            
        try:
            # Start audio stream
            self.audio_stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                callback=self.audio_callback,
                dtype=np.float32
            )
            self.audio_stream.start()
            
            # Start processing thread
            self.is_recording = True
            self.processing_thread = threading.Thread(target=self.process_audio_chunks, daemon=True)
            self.processing_thread.start()
            
            logger.info("Started simple real-time transcription")
            return True
            
        except Exception as e:
            logger.error(f"Error starting real-time recording: {e}")
            return False
            
    def stop_recording(self):
        """Stop real-time recording and transcription."""
        if not self.is_recording:
            return
            
        self.is_recording = False
        
        # Stop audio stream
        if self.audio_stream:
            self.audio_stream.stop()
            self.audio_stream.close()
            self.audio_stream = None
            
        # Wait for processing thread to finish
        if self.processing_thread:
            self.processing_thread.join(timeout=2.0)
            
        # Process any remaining audio
        if self.current_chunk and len(self.current_chunk) > self.sample_rate * 0.5:
            final_chunk = np.array(self.current_chunk)
            transcript = self.transcribe_chunk(final_chunk)
            if transcript and transcript.strip():
                self.on_transcript(transcript.strip())
                
        self.current_chunk = []
        logger.info("Stopped simple real-time transcription")


class SimpleRealtimeManager:
    """Manages simple real-time transcription sessions."""
    
    def __init__(self, config: dict):
        self.config = config
        self.current_session: Optional[SimpleRealtimeTranscription] = None
        self.is_active = False
        self.transcript_callback: Optional[Callable[[str], None]] = None
        
    def set_transcript_callback(self, callback: Callable[[str], None]):
        """Set callback for transcript updates."""
        self.transcript_callback = callback
        
    def start_session(self) -> bool:
        """Start a new real-time transcription session."""
        if self.is_active:
            return True
            
        try:
            if not self.transcript_callback:
                logger.error("No transcript callback set")
                return False
                
            self.current_session = SimpleRealtimeTranscription(
                self.config,
                self.transcript_callback
            )
            
            if self.current_session.start_recording():
                self.is_active = True
                logger.info("Started simple real-time transcription session")
                return True
            else:
                self.current_session = None
                return False
                
        except Exception as e:
            logger.error(f"Error starting simple real-time session: {e}")
            return False
            
    def stop_session(self):
        """Stop the current session."""
        if not self.is_active:
            return
            
        self.is_active = False
        
        if self.current_session:
            self.current_session.stop_recording()
            self.current_session = None
            
        logger.info("Stopped simple real-time transcription session")
        
    def toggle_session(self) -> bool:
        """Toggle the session on/off."""
        if self.is_active:
            self.stop_session()
            return False
        else:
            return self.start_session()
