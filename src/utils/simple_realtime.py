"""
Simplified Realtime Transcription using chunking strategy with gpt-4o-mini-transcribe
Enhanced to build running transcripts and better text handling
"""
import logging
import threading
import time
from collections import deque
from typing import Callable

import numpy as np
import sounddevice as sd

logger = logging.getLogger(__name__)


class SimpleRealtimeTranscriber:
    """
    Simple realtime transcription using chunking strategy with gpt-4o-mini-transcribe.
    Enhanced to build running transcripts instead of separate chunks.
    """

    def __init__(self, config, transcription_worker, callback: Callable[[str, bool], None]):
        self.config = config
        self.transcription_worker = transcription_worker
        self.callback = callback

        # Audio configuration
        self.sample_rate = config.get('sample_rate', 16000)
        self.channels = config.get('channels', 1)
        self.chunk_duration = config.get('realtime', {}).get('chunk_duration', 3.0)
        self.audio_device_index = config.get('audio_device_index')

        # Realtime state
        self.is_active = False
        self.audio_stream = None
        self.audio_buffer = deque()
        self.buffer_lock = threading.Lock()
        self.processing_thread = None

        # Running transcript management
        self.session_transcript = ""
        self.last_typed_length = 0
        self.transcript_lock = threading.Lock()

        # Buffer management
        self.max_buffer_size = int(self.sample_rate * 30)  # 30 seconds max buffer
        self.min_chunk_size = int(self.sample_rate * 1.0)  # Minimum 1 second for processing

        logger.info(f"Enhanced realtime transcriber initialized: chunk_duration={self.chunk_duration}s")

    def start(self):
        """Start realtime transcription using chunking strategy."""
        if self.is_active:
            logger.warning("Realtime transcription is already active")
            return

        try:
            self.is_active = True
            self.audio_buffer.clear()

            # Reset transcript state
            with self.transcript_lock:
                self.session_transcript = ""
                self.last_typed_length = 0

            # Start audio stream
            logger.info(f"Starting audio stream: sample_rate={self.sample_rate}, device={self.audio_device_index}")
            self.audio_stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                callback=self._audio_callback,
                device=self.audio_device_index,
                blocksize=1024,  # Small block size for low latency
                dtype=np.float32
            )
            self.audio_stream.start()
            logger.info("Audio stream started successfully")

            # Start processing thread
            self.processing_thread = threading.Thread(target=self._processing_loop, daemon=True)
            self.processing_thread.start()
            logger.info("Processing thread started")

            logger.info("Enhanced realtime transcription started successfully")

            # Send initial feedback
            if self.callback:
                self.callback("🎤 Realtime transcription active - speak now!", False)

        except Exception as e:
            logger.error(f"Failed to start realtime transcription: {e}")
            self.is_active = False
            raise

    def stop(self):
        """Stop realtime transcription."""
        if not self.is_active:
            logger.warning("Realtime transcription is not active")
            return

        logger.info("Stopping realtime transcription...")
        self.is_active = False

        # Stop audio stream
        if self.audio_stream:
            try:
                self.audio_stream.stop()
                self.audio_stream.close()
                self.audio_stream = None
                logger.info("Audio stream stopped")
            except Exception as e:
                logger.error(f"Error stopping audio stream: {e}")

        # Process any remaining audio
        try:
            self._process_remaining_audio()
        except Exception as e:
            logger.error(f"Error processing remaining audio: {e}")

        # Finalize the session transcript
        with self.transcript_lock:
            if self.session_transcript.strip():
                logger.info(f"Session transcript completed: {len(self.session_transcript)} characters")
                # Save final transcript to database
                self._save_session_transcript()

        logger.info("Enhanced realtime transcription stopped")

    def _audio_callback(self, indata, frames, time_info, status):
        """Audio input callback - adds audio to buffer."""
        if status:
            logger.warning(f"Audio callback status: {status}")

        if not self.is_active:
            return

        try:
            with self.buffer_lock:
                # Convert audio to proper format
                if self.channels == 1:
                    audio_data = indata.flatten()
                else:
                    audio_data = indata.mean(axis=1)  # Convert stereo to mono

                # Add to buffer
                self.audio_buffer.extend(audio_data)

                # Prevent buffer from growing too large
                while len(self.audio_buffer) > self.max_buffer_size:
                    # Remove old data from beginning
                    for _ in range(min(1024, len(self.audio_buffer))):
                        if self.audio_buffer:
                            self.audio_buffer.popleft()

        except Exception as e:
            logger.error(f"Audio callback error: {e}")

    def _processing_loop(self):
        """Main processing loop - extracts chunks and transcribes them."""
        last_chunk_time = time.time()

        logger.info(f"Processing loop started with chunk duration: {self.chunk_duration}s")

        while self.is_active:
            try:
                current_time = time.time()

                # Check if it's time to process a chunk
                if current_time - last_chunk_time >= self.chunk_duration:
                    self._extract_and_process_chunk()
                    last_chunk_time = current_time

                # Small delay to prevent busy waiting
                time.sleep(0.1)

            except Exception as e:
                logger.error(f"Processing loop error: {e}")
                time.sleep(1)  # Longer delay on error

        logger.info("Processing loop ended")

    def _extract_and_process_chunk(self):
        """Extract a chunk from buffer and process it."""
        try:
            with self.buffer_lock:
                if len(self.audio_buffer) < self.min_chunk_size:
                    logger.debug(f"Buffer too small: {len(self.audio_buffer)} < {self.min_chunk_size}")
                    return

                # Extract chunk
                chunk_samples = int(self.chunk_duration * self.sample_rate)
                available_samples = len(self.audio_buffer)

                # Use available samples or chunk size, whichever is smaller
                samples_to_take = min(chunk_samples, available_samples)

                if samples_to_take < self.min_chunk_size:
                    return

                # Get the chunk
                chunk_data = []
                for _ in range(samples_to_take):
                    if self.audio_buffer:
                        chunk_data.append(self.audio_buffer.popleft())

                if len(chunk_data) >= self.min_chunk_size:
                    audio_chunk = np.array(chunk_data, dtype=np.float32)

                    # Normalize audio
                    if np.max(np.abs(audio_chunk)) > 0:
                        audio_chunk = audio_chunk / np.max(np.abs(audio_chunk))

                    logger.debug(
                        f"Processing audio chunk: {len(audio_chunk)} samples, {len(audio_chunk) / self.sample_rate:.1f}s")

                    # Process chunk in background
                    threading.Thread(
                        target=self._transcribe_chunk,
                        args=(audio_chunk,),
                        daemon=True
                    ).start()

        except Exception as e:
            logger.error(f"Chunk extraction error: {e}")

    def _process_remaining_audio(self):
        """Process any remaining audio in the buffer when stopping."""
        try:
            with self.buffer_lock:
                if len(self.audio_buffer) >= self.min_chunk_size:
                    logger.info("Processing remaining audio buffer...")

                    # Get all remaining audio
                    remaining_data = list(self.audio_buffer)
                    self.audio_buffer.clear()

                    if remaining_data:
                        audio_chunk = np.array(remaining_data, dtype=np.float32)

                        # Normalize audio
                        if np.max(np.abs(audio_chunk)) > 0:
                            audio_chunk = audio_chunk / np.max(np.abs(audio_chunk))

                        # Process synchronously for final chunk
                        self._transcribe_chunk(audio_chunk, is_final=True)

        except Exception as e:
            logger.error(f"Error processing remaining audio: {e}")

    def _transcribe_chunk(self, audio_chunk, is_final=False):
        """Transcribe an audio chunk and build running transcript."""
        try:
            # Minimum chunk size check
            duration = len(audio_chunk) / self.sample_rate
            if duration < 0.8:  # Skip very short chunks (less than 0.8 seconds)
                logger.debug(f"Skipping short chunk: {duration:.1f}s")
                return

            logger.debug(f"Transcribing chunk: {duration:.1f}s duration")

            # Use existing transcription worker
            def chunk_callback(transcript):
                try:
                    if transcript and transcript.strip():
                        cleaned_transcript = transcript.strip()
                        logger.info(f"Realtime chunk transcript ({duration:.1f}s): {cleaned_transcript}")

                        # Update running transcript
                        self._update_running_transcript(cleaned_transcript, is_final)

                    else:
                        logger.debug("Empty transcript received for chunk")

                except Exception as e:
                    logger.error(f"Error in chunk callback: {e}")

            # Queue for transcription
            self.transcription_worker.queue_transcription(audio_chunk, chunk_callback)

        except Exception as e:
            logger.error(f"Chunk transcription error: {e}")

    def _update_running_transcript(self, new_text, is_final=False):
        """Update the running transcript and type incrementally."""
        try:
            with self.transcript_lock:
                # Add new text to session transcript
                if self.session_transcript and not self.session_transcript.endswith(' '):
                    self.session_transcript += ' '
                self.session_transcript += new_text

                # Calculate what new text needs to be typed
                current_length = len(self.session_transcript)
                new_text_to_type = self.session_transcript[self.last_typed_length:]

                if new_text_to_type:
                    # Type the new text directly if enabled
                    if self.config.get('realtime', {}).get('type_text', True):
                        try:
                            import keyboard
                            keyboard.write(new_text_to_type)
                            logger.debug(f"Typed incremental text: '{new_text_to_type}'")
                        except Exception as e:
                            logger.error(f"Error typing incremental text: {e}")

                    # Update our position
                    self.last_typed_length = current_length

                    # Send callback with running transcript
                    if self.callback:
                        self.callback(self.session_transcript, is_final)

                    logger.debug(f"Running transcript updated: {len(self.session_transcript)} chars total")

        except Exception as e:
            logger.error(f"Error updating running transcript: {e}")

    def _save_session_transcript(self):
        """Save the complete session transcript to database."""
        try:
            if not self.session_transcript.strip():
                return

            from datetime import datetime
            import sys
            import os
            
            # Get access to the database
            # First, try to access it from the transcription worker if it has app reference
            db = None
            if hasattr(self.transcription_worker, 'app') and hasattr(self.transcription_worker.app, 'db'):
                db = self.transcription_worker.app.db
            
            # If we couldn't get it from the worker, try to import it directly
            if db is None:
                try:
                    # Add the project root to path if needed
                    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
                    if project_root not in sys.path:
                        sys.path.insert(0, project_root)
                        
                    from utils.database import TranscriptionDatabase, TranscriptionRecord
                    db = TranscriptionDatabase()
                except Exception as import_error:
                    logger.error(f"Failed to import database: {import_error}")
                    return
            
            # Create the record
            from utils.database import TranscriptionRecord
            
            record = TranscriptionRecord(
                timestamp=datetime.now().isoformat(),
                text=self.session_transcript,
                duration_seconds=0.0,  # Realtime session duration would need tracking
                engine="openai_realtime_session",
                model=self.config.get('realtime', {}).get('model', 'gpt-4o-mini-transcribe'),
                audio_device=str(self.config.get('audio_device_index', 'default')),
                hotkey_used=self.config.get('realtime_hotkey', 'ctrl+alt+shift+enter'),
                processing_time_ms=0  # Realtime processing
            )

            # Save to database
            if db:
                record_id = db.add_transcription(record)
                logger.info(f"Saved session transcript to database with ID {record_id}: {len(self.session_transcript)} characters")
            else:
                logger.error("Could not access database to save session transcript")

        except Exception as e:
            logger.error(f"Error saving session transcript: {e}", exc_info=True)


class RealtimeTranscriptionSession:
    """
    Compatibility wrapper for the simplified realtime transcription.
    Maintains the same interface as the original complex implementation.
    """

    def __init__(self, config, callback):
        self.config = config
        self.callback = callback
        self.transcriber = None

    async def start_session(self):
        """Start transcription session (async wrapper for compatibility)."""
        # This will be called from the main app, but we need the transcription worker
        # We'll initialize it when start_session is called
        pass

    async def stop_session(self):
        """Stop transcription session (async wrapper for compatibility)."""
        if self.transcriber:
            self.transcriber.stop()

    def set_transcription_worker(self, transcription_worker):
        """Set the transcription worker and initialize the simple transcriber."""
        if not self.transcriber:
            self.transcriber = SimpleRealtimeTranscriber(
                self.config,
                transcription_worker,
                self.callback
            )

    def start_realtime(self):
        """Start realtime transcription."""
        if self.transcriber:
            self.transcriber.start()

    def stop_realtime(self):
        """Stop realtime transcription."""
        if self.transcriber:
            self.transcriber.stop()
