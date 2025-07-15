#!/usr/bin/env python
"""
End-to-end functionality test for WhisperKey
Tests the complete workflow: record → transcribe → clipboard → history
"""
import sys
import time
import numpy as np
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

def test_audio_recording():
    """Test actual audio recording and buffering"""
    print("🎤 Testing Audio Recording...")
    try:
        from whisperkey import AudioRecorder
        
        # Create recorder with short buffer for testing
        recorder = AudioRecorder(
            sample_rate=16000,
            channels=1,
            buffer_duration=1.0,  # 1 second buffer
            device_index=None
        )
        
        print("✅ AudioRecorder initialized")
        
        # Test buffer functionality
        print("📊 Testing rolling buffer...")
        time.sleep(2)  # Let buffer fill up
        
        if len(recorder.rolling_buffer) > 0:
            print(f"✅ Rolling buffer active: {len(recorder.rolling_buffer)} samples")
        else:
            print("❌ Rolling buffer empty")
            return False
        
        # Test recording start/stop
        print("🔴 Testing recording start/stop...")
        recorder.start_recording()
        
        if recorder.recording:
            print("✅ Recording started successfully")
        else:
            print("❌ Recording failed to start")
            return False
        
        # Record for a short time
        time.sleep(0.5)
        
        # Stop recording
        audio_data = recorder.stop_recording()
        
        if audio_data is not None and len(audio_data) > 0:
            duration = len(audio_data) / recorder.sample_rate
            print(f"✅ Recording stopped: {duration:.2f}s of audio captured")
            
            # Check if buffer was included
            if duration > 0.5:  # Should include buffer + recording
                print("✅ Rolling buffer appears to be included")
            else:
                print("⚠️  Audio might be too short (buffer issue?)")
            
        else:
            print("❌ No audio data captured")
            return False
        
        # Cleanup
        recorder.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ Audio recording error: {e}")
        return False

def test_transcription_pipeline():
    """Test transcription with synthetic audio"""
    print("🤖 Testing Transcription Pipeline...")
    try:
        from whisperkey import TranscriptionWorker
        import os
        
        config = {
            'sample_rate': 16000,
            'transcription': {
                'engine': 'openai',
                'model': 'gpt-4o-mini-transcribe'
            }
        }
        
        # Check API key
        if not os.getenv("OPENAI_API_KEY"):
            print("❌ No OpenAI API key - skipping transcription test")
            return False
        
        worker = TranscriptionWorker(config)
        
        if not worker.client:
            print("❌ OpenAI client not initialized")
            return False
        
        # Create synthetic speech-like audio (sine wave)
        print("🔊 Creating synthetic audio...")
        duration = 2.0  # 2 seconds
        sample_rate = 16000
        frequency = 440  # A4 note
        
        t = np.linspace(0, duration, int(sample_rate * duration))
        # Create a more complex waveform that might transcribe
        audio_data = (
            0.3 * np.sin(2 * np.pi * frequency * t) +
            0.2 * np.sin(2 * np.pi * frequency * 1.5 * t) +
            0.1 * np.random.normal(0, 0.1, len(t))
        )
        audio_data = audio_data.reshape(-1, 1).astype(np.float32)
        
        print("🎯 Testing transcription (this will make an API call)...")
        transcript = worker.transcribe_audio(audio_data)
        
        if transcript is not None:
            print(f"✅ Transcription completed: '{transcript}'")
            # Note: Synthetic audio may not produce meaningful text
            return True
        else:
            print("❌ Transcription failed")
            return False
            
    except Exception as e:
        print(f"❌ Transcription pipeline error: {e}")
        return False

def test_clipboard_integration():
    """Test clipboard functionality"""
    print("📋 Testing Clipboard Integration...")
    try:
        import pyperclip
        
        test_text = "WhisperKey clipboard test - " + str(int(time.time()))
        
        # Set clipboard
        pyperclip.copy(test_text)
        
        # Get clipboard
        clipboard_content = pyperclip.paste()
        
        if clipboard_content == test_text:
            print("✅ Clipboard read/write working")
            return True
        else:
            print(f"❌ Clipboard mismatch: expected '{test_text}', got '{clipboard_content}'")
            return False
            
    except Exception as e:
        print(f"❌ Clipboard error: {e}")
        return False

def test_database_persistence():
    """Test database with actual app database file"""
    print("💾 Testing Database Persistence...")
    try:
        from database import TranscriptionDatabase, TranscriptionRecord
        import os
        
        # Use the actual app database location
        app_data_dir = Path(os.getenv('LOCALAPPDATA')) / 'WhisperKey'
        app_data_dir.mkdir(parents=True, exist_ok=True)
        db_path = app_data_dir / 'transcriptions.db'
        
        print(f"📁 Using database: {db_path}")
        
        db = TranscriptionDatabase(str(db_path))
        
        # Add a test record
        test_record = TranscriptionRecord(
            text="End-to-end test transcription",
            duration_seconds=2.0,
            engine="test",
            model="test-model",
            audio_device="default",
            hotkey_used="ctrl+alt+enter",
            processing_time_ms=1500
        )
        
        record_id = db.add_transcription(test_record)
        
        if record_id:
            print(f"✅ Record added with ID: {record_id}")
            
            # Retrieve recent records
            recent = db.get_recent_transcriptions(5)
            
            if recent and len(recent) > 0:
                print(f"✅ Retrieved {len(recent)} recent records")
                
                # Check if our test record is there
                found_test = any(r.text == "End-to-end test transcription" for r in recent)
                if found_test:
                    print("✅ Test record found in database")
                else:
                    print("⚠️  Test record not found in recent records")
                
                return True
            else:
                print("❌ No records retrieved")
                return False
        else:
            print("❌ Failed to add record")
            return False
            
    except Exception as e:
        print(f"❌ Database persistence error: {e}")
        return False

def main():
    """Run end-to-end functionality tests"""
    print("🚀 WhisperKey End-to-End Functionality Test\n")
    
    tests = [
        ("Audio Recording & Buffering", test_audio_recording),
        ("Transcription Pipeline", test_transcription_pipeline),
        ("Clipboard Integration", test_clipboard_integration),
        ("Database Persistence", test_database_persistence),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*70}")
        success = test_func()
        results.append((test_name, success))
        print(f"{'='*70}")
    
    print(f"\n{'🏁 END-TO-END TEST RESULTS 🏁':^70}")
    print("="*70)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name:<40} {status}")
        if success:
            passed += 1
    
    print("="*70)
    print(f"End-to-End Tests Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All end-to-end tests passed! Core workflow functional.")
        print("\nNext steps:")
        print("1. Test GUI styling and improvements")
        print("2. Test hotkey customization interface")
        print("3. Test with real voice recording")
        print("4. Add remaining features")
    else:
        print("⚠️  Some end-to-end tests failed. Core workflow needs fixes.")
        print("\nCritical issues to address:")
        for test_name, success in results:
            if not success:
                print(f"- Fix: {test_name}")
    
    return passed == total

if __name__ == "__main__":
    main()
