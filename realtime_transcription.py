#!/usr/bin/env python
"""
Real-time Streaming Transcription for WhisperKey
Uses OpenAI's Realtime API with WebSocket connection
"""
import asyncio
import json
import logging
import threading
import time
from typing import Optional, Callable, Dict, Any
import base64

import websockets
import numpy as np
import sounddevice as sd
from collections import deque

logger = logging.getLogger("whisperkey.realtime")


class RealtimeTranscriptionSession:
    """Manages real-time transcription session with OpenAI Realtime API."""
    
    def __init__(self, config: Dict[str, Any], on_transcript: Callable[[str, bool], None]):
        self.config = config
        self.on_transcript = on_transcript  # Callback for transcript updates (text, is_final)
        
        # WebSocket connection
        self.websocket = None
        self.session_id = None
        self.is_connected = False
        self.is_recording = False
        
        # Audio configuration
        self.sample_rate = 24000  # Realtime API uses 24kHz
        self.channels = 1
        self.audio_format = "pcm16"
        
        # Audio streaming
        self.audio_stream = None
        self.audio_buffer = deque()
        self.buffer_lock = threading.Lock()
        
        # Session configuration
        self.session_config = {
            "type": "transcription_session.update",
            "input_audio_format": self.audio_format,
            "input_audio_transcription": {
                "model": config.get('realtime', {}).get('model', 'gpt-4o-mini-transcribe'),
                "prompt": config.get('realtime', {}).get('prompt', ''),
                "language": config.get('realtime', {}).get('language', 'en')
            },
            "turn_detection": {
                "type": "server_vad",
                "threshold": config.get('realtime', {}).get('vad_threshold', 0.5),
                "prefix_padding_ms": config.get('realtime', {}).get('prefix_padding_ms', 300),
                "silence_duration_ms": config.get('realtime', {}).get('silence_duration_ms', 500)
            },
            "input_audio_noise_reduction": {
                "type": config.get('realtime', {}).get('noise_reduction', 'near_field')
            },
            "include": [
                "item.input_audio_transcription.logprobs"
            ]
        }
        
        # Event loop for async operations
        self.loop = None
        self.loop_thread = None
        
    async def connect(self) -> bool:
        """Connect to OpenAI Realtime API."""
        try:
            import os
            api_key = os.getenv('OPENAI_API_KEY') or self.config.get('openai_api_key')
            if not api_key:
                logger.error("OpenAI API key not found. Please set OPENAI_API_KEY environment variable.")
                return False
                
            # WebSocket URL for Realtime API
            url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "OpenAI-Beta": "realtime=v1"
            }
            
            self.websocket = await websockets.connect(url, extra_headers=headers)
            self.is_connected = True
            
            # Send session configuration
            await self.websocket.send(json.dumps(self.session_config))
            
            logger.info("Connected to OpenAI Realtime API")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Realtime API: {e}")
            return False
            
    async def disconnect(self):
        """Disconnect from the API."""
        self.is_connected = False
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
            
    async def send_audio_data(self, audio_data: bytes):
        """Send audio data to the API."""
        if not self.is_connected or not self.websocket:
            return
            
        try:
            # Encode audio data as base64
            audio_b64 = base64.b64encode(audio_data).decode('utf-8')
            
            # Send audio append event
            event = {
                "type": "input_audio_buffer.append",
                "audio": audio_b64
            }
            
            await self.websocket.send(json.dumps(event))
            
        except Exception as e:
            logger.error(f"Error sending audio data: {e}")
            
    async def commit_audio_buffer(self):
        """Commit the audio buffer for transcription."""
        if not self.is_connected or not self.websocket:
            return
            
        try:
            event = {
                "type": "input_audio_buffer.commit"
            }
            await self.websocket.send(json.dumps(event))
            
        except Exception as e:
            logger.error(f"Error committing audio buffer: {e}")
            
    async def listen_for_events(self):
        """Listen for events from the API."""
        if not self.websocket:
            return
            
        try:
            async for message in self.websocket:
                event = json.loads(message)
                await self.handle_event(event)
                
        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed")
        except Exception as e:
            logger.error(f"Error listening for events: {e}")
            
    async def handle_event(self, event: Dict[str, Any]):
        """Handle events from the API."""
        event_type = event.get("type")
        
        if event_type == "conversation.item.input_audio_transcription.delta":
            # Incremental transcript
            delta = event.get("delta", "")
            if delta:
                self.on_transcript(delta, False)  # Not final
                
        elif event_type == "conversation.item.input_audio_transcription.completed":
            # Final transcript
            transcript = event.get("transcript", "")
            if transcript:
                self.on_transcript(transcript, True)  # Final
                
        elif event_type == "error":
            logger.error(f"API error: {event}")
            
        elif event_type == "session.created":
            self.session_id = event.get("session", {}).get("id")
            logger.info(f"Session created: {self.session_id}")
            
    def audio_callback(self, indata, frames, time, status):
        """Audio input callback."""
        if status:
            logger.warning(f"Audio callback status: {status}")
            
        if self.is_recording:
            # Convert to PCM16 format
            audio_data = (indata.flatten() * 32767).astype(np.int16)
            audio_bytes = audio_data.tobytes()
            
            # Add to buffer
            with self.buffer_lock:
                self.audio_buffer.append(audio_bytes)
                
    async def process_audio_buffer(self):
        """Process audio buffer and send to API."""
        while self.is_recording:
            try:
                # Get audio data from buffer
                audio_chunks = []
                with self.buffer_lock:
                    while self.audio_buffer:
                        audio_chunks.append(self.audio_buffer.popleft())
                        
                # Send audio data
                if audio_chunks:
                    combined_audio = b''.join(audio_chunks)
                    await self.send_audio_data(combined_audio)
                    
                # Small delay to prevent overwhelming the API
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error processing audio buffer: {e}")
                
    def start_recording(self):
        """Start recording and streaming audio."""
        if self.is_recording:
            return
            
        try:
            # Start audio stream
            self.audio_stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                callback=self.audio_callback,
                dtype=np.float32
            )
            self.audio_stream.start()
            
            self.is_recording = True
            logger.info("Started real-time recording")
            
            # Start audio processing task
            if self.loop:
                asyncio.run_coroutine_threadsafe(self.process_audio_buffer(), self.loop)
                
        except Exception as e:
            logger.error(f"Error starting recording: {e}")
            
    def stop_recording(self):
        """Stop recording."""
        if not self.is_recording:
            return
            
        self.is_recording = False
        
        if self.audio_stream:
            self.audio_stream.stop()
            self.audio_stream.close()
            self.audio_stream = None
            
        # Commit any remaining audio
        if self.loop and self.is_connected:
            asyncio.run_coroutine_threadsafe(self.commit_audio_buffer(), self.loop)
            
        logger.info("Stopped real-time recording")
        
    def start_session(self):
        """Start the real-time transcription session."""
        if self.loop_thread and self.loop_thread.is_alive():
            return
            
        # Start event loop in separate thread
        self.loop_thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self.loop_thread.start()
        
    def stop_session(self):
        """Stop the real-time transcription session."""
        self.stop_recording()
        
        if self.loop:
            # Schedule disconnect
            asyncio.run_coroutine_threadsafe(self.disconnect(), self.loop)
            
        # Wait for thread to finish
        if self.loop_thread:
            self.loop_thread.join(timeout=5)
            
    def _run_event_loop(self):
        """Run the async event loop."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        try:
            # Connect and start listening
            self.loop.run_until_complete(self._session_main())
        except Exception as e:
            logger.error(f"Event loop error: {e}")
        finally:
            self.loop.close()
            
    async def _session_main(self):
        """Main session coroutine."""
        # Connect to API
        if not await self.connect():
            return
            
        # Start listening for events
        await self.listen_for_events()


class RealtimeTranscriptionManager:
    """Manages real-time transcription sessions."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.current_session: Optional[RealtimeTranscriptionSession] = None
        self.is_active = False
        
        # Transcript accumulation
        self.current_transcript = ""
        self.transcript_callback: Optional[Callable[[str], None]] = None
        
    def set_transcript_callback(self, callback: Callable[[str], None]):
        """Set callback for transcript updates."""
        self.transcript_callback = callback
        
    def start_session(self) -> bool:
        """Start a new real-time transcription session."""
        if self.is_active:
            return True
            
        try:
            self.current_session = RealtimeTranscriptionSession(
                self.config,
                self._on_transcript_update
            )
            
            self.current_session.start_session()
            self.is_active = True
            
            # Start recording after a short delay
            threading.Timer(1.0, self.current_session.start_recording).start()
            
            logger.info("Started real-time transcription session")
            return True
            
        except Exception as e:
            logger.error(f"Error starting real-time session: {e}")
            return False
            
    def stop_session(self):
        """Stop the current session."""
        if not self.is_active:
            return
            
        self.is_active = False
        
        if self.current_session:
            self.current_session.stop_session()
            self.current_session = None
            
        # Send final transcript
        if self.current_transcript and self.transcript_callback:
            self.transcript_callback(self.current_transcript)
            
        self.current_transcript = ""
        logger.info("Stopped real-time transcription session")
        
    def _on_transcript_update(self, text: str, is_final: bool):
        """Handle transcript updates from the session."""
        if is_final:
            # Final transcript - add to accumulated text
            self.current_transcript += text + " "
            
            # Send to callback for immediate typing
            if self.transcript_callback:
                self.transcript_callback(text)
        else:
            # Delta update - could be used for live preview
            logger.debug(f"Transcript delta: {text}")
            
    def toggle_session(self) -> bool:
        """Toggle the session on/off."""
        if self.is_active:
            self.stop_session()
            return False
        else:
            return self.start_session()
