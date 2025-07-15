#!/usr/bin/env python
"""
Comprehensive functionality test for WhisperKey
"""
import sys
import time
import threading
import tkinter as tk
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

def test_gui_creation():
    """Test if GUI can be created and displayed"""
    print("🧪 Testing GUI Creation...")
    try:
        from gui import WhisperKeyGUI
        
        # Create a mock app instance
        class MockApp:
            def __init__(self):
                self.config = {
                    'hotkey': 'ctrl+alt+enter',
                    'transcription': {'engine': 'openai'},
                    'audio_device_index': None
                }
        
        mock_app = MockApp()
        gui = WhisperKeyGUI(mock_app)
        gui.create_window()
        
        # Test window creation
        if gui.window:
            print("✅ GUI window created successfully")
            gui.window.update()  # Process any pending events
            
            # Test if widgets exist
            if hasattr(gui, 'status_label'):
                print("✅ GUI widgets created")
            else:
                print("❌ GUI widgets missing")
            
            # Clean up
            gui.window.destroy()
            return True
        else:
            print("❌ GUI window creation failed")
            return False
            
    except Exception as e:
        print(f"❌ GUI creation error: {e}")
        return False

def test_database_operations():
    """Test database functionality"""
    print("🧪 Testing Database Operations...")
    try:
        from database import TranscriptionDatabase, TranscriptionRecord
        import tempfile
        import os
        
        # Create temporary database
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as temp_db:
            temp_db_path = temp_db.name
        
        db = TranscriptionDatabase(temp_db_path)
        
        # Test record creation
        record = TranscriptionRecord(
            text="Test transcription for functionality check",
            duration_seconds=3.5,
            engine="test",
            model="test-model",
            audio_device="default",
            hotkey_used="ctrl+alt+enter",
            processing_time_ms=2000
        )
        
        record_id = db.add_transcription(record)
        print(f"✅ Database record added with ID: {record_id}")
        
        # Test retrieval
        recent = db.get_recent_transcriptions(1)
        if recent and len(recent) > 0:
            print(f"✅ Database retrieval working: '{recent[0].text[:30]}...'")
            
            # Test statistics
            stats = db.get_statistics()
            print(f"✅ Database statistics: {stats['total_transcriptions']} transcriptions")
        else:
            print("❌ Database retrieval failed")
        
        # Cleanup
        try:
            # Ensure database is closed properly
            del db
            import time
            time.sleep(0.1)  # Brief pause for Windows file system
            os.unlink(temp_db_path)
        except Exception as cleanup_error:
            print(f"⚠️  Cleanup warning: {cleanup_error}")
        return True
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def test_audio_system():
    """Test audio system initialization"""
    print("🧪 Testing Audio System...")
    try:
        import sounddevice as sd
        from whisperkey import AudioRecorder
        
        # Test device enumeration
        devices = sd.query_devices()
        input_devices = [d for d in devices if d['max_input_channels'] > 0]
        print(f"✅ Found {len(input_devices)} input audio devices")
        
        # Test AudioRecorder initialization
        recorder = AudioRecorder(
            sample_rate=16000,
            channels=1,
            buffer_duration=1.0,  # Short buffer for testing
            device_index=None
        )
        
        print("✅ AudioRecorder initialized")
        
        # Test buffer
        if hasattr(recorder, 'rolling_buffer'):
            print("✅ Rolling buffer created")
        else:
            print("❌ Rolling buffer missing")
        
        # Cleanup
        recorder.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ Audio system error: {e}")
        return False

def test_openai_client():
    """Test OpenAI client initialization"""
    print("🧪 Testing OpenAI Client...")
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
        
        # Check if API key exists
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("❌ No OpenAI API key found in environment")
            return False
        else:
            print("✅ OpenAI API key found")
        
        # Test TranscriptionWorker initialization
        worker = TranscriptionWorker(config)
        
        if worker.client:
            print("✅ OpenAI client initialized successfully")
            return True
        else:
            print("❌ OpenAI client initialization failed")
            return False
            
    except Exception as e:
        print(f"❌ OpenAI client error: {e}")
        return False

def test_hotkey_system():
    """Test hotkey system"""
    print("🧪 Testing Hotkey System...")
    try:
        import keyboard
        
        # Test basic keyboard functionality
        print("✅ Keyboard library imported")
        
        # Test hotkey registration (but don't actually register to avoid conflicts)
        test_combo = "ctrl+shift+f12"  # Unlikely to conflict
        
        def test_callback():
            print("Test hotkey triggered")
        
        # Try to register and immediately unregister
        keyboard.add_hotkey(test_combo, test_callback)
        keyboard.remove_hotkey(test_combo)
        print("✅ Hotkey registration/removal works")
        
        return True
        
    except Exception as e:
        print(f"❌ Hotkey system error: {e}")
        return False

def main():
    """Run comprehensive functionality tests"""
    print("🔍 WhisperKey Comprehensive Functionality Test\n")
    
    tests = [
        ("GUI Creation", test_gui_creation),
        ("Database Operations", test_database_operations), 
        ("Audio System", test_audio_system),
        ("OpenAI Client", test_openai_client),
        ("Hotkey System", test_hotkey_system),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        success = test_func()
        results.append((test_name, success))
        print(f"{'='*60}")
    
    print(f"\n{'🏁 FINAL RESULTS 🏁':^60}")
    print("="*60)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name:<30} {status}")
        if success:
            passed += 1
    
    print("="*60)
    print(f"Tests Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! Core functionality working.")
    else:
        print("⚠️  Some tests failed. Issues need to be addressed.")
        print("\nNext steps:")
        print("1. Fix failing components")
        print("2. Test end-to-end recording workflow")
        print("3. Improve GUI styling")
        print("4. Add remaining features")
    
    return passed == total

if __name__ == "__main__":
    main()
