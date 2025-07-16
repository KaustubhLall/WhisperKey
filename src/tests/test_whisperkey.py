#!/usr/bin/env python
"""
Test script for WhisperKey functionality
"""
import os
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from src.utils.database import TranscriptionDatabase, TranscriptionRecord
from src.whisperkey import AudioRecorder, TranscriptionWorker


class TestTranscriptionDatabase(unittest.TestCase):
    """Test cases for the transcription database"""

    def setUp(self):
        """Setup test database"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db = TranscriptionDatabase(self.temp_db.name)

    def tearDown(self):
        """Cleanup test database"""
        os.unlink(self.temp_db.name)

    def test_add_transcription(self):
        """Test adding a transcription record"""
        record = TranscriptionRecord(
            text="Hello world",
            duration_seconds=2.5,
            engine="test",
            model="test-model",
            audio_device="default",
            hotkey_used="ctrl+alt+enter",
            processing_time_ms=1500
        )

        record_id = self.db.add_transcription(record)
        self.assertIsNotNone(record_id)
        self.assertGreater(record_id, 0)

    def test_get_recent_transcriptions(self):
        """Test retrieving recent transcriptions"""
        # Add some test records
        for i in range(5):
            record = TranscriptionRecord(
                text=f"Test transcription {i}",
                duration_seconds=1.0,
                engine="test",
                model="test-model",
                audio_device="default",
                hotkey_used="ctrl+alt+enter",
                processing_time_ms=1000
            )
            self.db.add_transcription(record)

        recent = self.db.get_recent_transcriptions(3)
        self.assertEqual(len(recent), 3)
        self.assertEqual(recent[0].text, "Test transcription 4")  # Most recent first


class TestAudioRecorder(unittest.TestCase):
    """Test cases for the audio recorder"""

    def setUp(self):
        """Setup audio recorder"""
        self.recorder = AudioRecorder(
            sample_rate=16000,
            channels=1,
            buffer_duration=1.0  # Short buffer for testing
        )

    def tearDown(self):
        """Cleanup audio recorder"""
        self.recorder.cleanup()

    def test_audio_recorder_initialization(self):
        """Test audio recorder initialization"""
        self.assertEqual(self.recorder.sample_rate, 16000)
        self.assertEqual(self.recorder.channels, 1)
        self.assertEqual(self.recorder.buffer_duration, 1.0)
        self.assertFalse(self.recorder.recording)


class TestTranscriptionWorker(unittest.TestCase):
    """Test cases for the transcription worker"""

    def setUp(self):
        """Setup transcription worker"""
        self.config = {
            'sample_rate': 16000,
            'transcription': {
                'engine': 'openai',
                'model': 'gpt-4o-mini-transcribe'
            }
        }

    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test_key'})
    @patch('openai.OpenAI')
    def test_transcription_worker_initialization(self, mock_openai):
        """Test transcription worker initialization"""
        worker = TranscriptionWorker(self.config)
        self.assertIsNotNone(worker.client)
        mock_openai.assert_called_once()

    def test_parse_hotkey(self):
        """Test hotkey parsing"""
        from src.whisperkey import WhisperKeyApp

        # Mock the load_config method to avoid file operations
        with patch.object(WhisperKeyApp, 'load_config'):
            with patch.object(WhisperKeyApp, '__init__', lambda x: None):
                app = WhisperKeyApp()

                # Test basic hotkey parsing
                result = app.parse_hotkey('ctrl+alt+enter')
                expected = '<ctrl>+<alt>+<enter>'
                self.assertEqual(result, expected)

                # Test single key
                result = app.parse_hotkey('f1')
                self.assertEqual(result, 'f1')


def create_test_audio():
    """Create test audio data for testing"""
    sample_rate = 16000
    duration = 2.0  # 2 seconds
    frequency = 440  # A4 note

    t = np.linspace(0, duration, int(sample_rate * duration))
    audio_data = np.sin(2 * np.pi * frequency * t)

    # Add some noise to make it more realistic
    noise = np.random.normal(0, 0.1, audio_data.shape)
    audio_data = audio_data + noise

    # Convert to the format expected by the transcription system
    audio_data = audio_data.reshape(-1, 1)

    return audio_data.astype(np.float32)


if __name__ == '__main__':
    # Create test audio file for manual testing
    test_audio = create_test_audio()
    print(f"Created test audio: {test_audio.shape} samples")

    # Run unit tests
    unittest.main(verbosity=2)
