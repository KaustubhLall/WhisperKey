#!/usr/bin/env python
"""
Basic functionality test for WhisperKey
"""
import os
import sys
import tempfile
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all modules can be imported"""
    try:
        from database import TranscriptionDatabase, TranscriptionRecord
        print("✅ Database module imported successfully")
        
        from gui import WhisperKeyGUI
        print("✅ GUI module imported successfully")
        
        import yaml
        import numpy as np
        import sounddevice as sd
        import pyperclip
        from dotenv import load_dotenv
        print("✅ All dependencies imported successfully")
        
        return True
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

def test_database():
    """Test database functionality"""
    try:
        from database import TranscriptionDatabase, TranscriptionRecord
        
        # Create temporary database
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as temp_db:
            temp_db_path = temp_db.name
        
        db = TranscriptionDatabase(temp_db_path)
        
        # Test adding a record
        record = TranscriptionRecord(
            text="Test transcription",
            duration_seconds=2.5,
            engine="test",
            model="test-model",
            audio_device="default",
            hotkey_used="ctrl+alt+enter",
            processing_time_ms=1500
        )
        
        record_id = db.add_transcription(record)
        print(f"✅ Database record added with ID: {record_id}")
        
        # Test retrieving records
        recent = db.get_recent_transcriptions(1)
        if recent and recent[0].text == "Test transcription":
            print("✅ Database retrieval working")
        else:
            print("❌ Database retrieval failed")
        
        # Cleanup
        os.unlink(temp_db_path)
        return True
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def test_config():
    """Test configuration loading"""
    try:
        import yaml
        
        config_path = Path(__file__).parent / 'config.yaml'
        if not config_path.exists():
            print("❌ config.yaml not found")
            return False
            
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        required_keys = ['hotkey', 'sample_rate', 'channels', 'buffer_duration']
        missing_keys = [key for key in required_keys if key not in config]
        
        if missing_keys:
            print(f"❌ Missing config keys: {missing_keys}")
            return False
        else:
            print("✅ Configuration file is valid")
            print(f"   - Hotkey: {config['hotkey']}")
            print(f"   - Sample rate: {config['sample_rate']}")
            print(f"   - Buffer duration: {config['buffer_duration']}")
            return True
            
    except Exception as e:
        print(f"❌ Config error: {e}")
        return False

def test_audio_devices():
    """Test audio device enumeration"""
    try:
        import sounddevice as sd
        
        devices = sd.query_devices()
        input_devices = [d for d in devices if d['max_input_channels'] > 0]
        
        if input_devices:
            print(f"✅ Found {len(input_devices)} input audio devices")
            for i, device in enumerate(input_devices[:3]):  # Show first 3
                print(f"   - {device['name']}")
            return True
        else:
            print("❌ No input audio devices found")
            return False
            
    except Exception as e:
        print(f"❌ Audio device error: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Running WhisperKey Basic Tests...\n")
    
    tests = [
        ("Import Test", test_imports),
        ("Database Test", test_database),
        ("Configuration Test", test_config),
        ("Audio Devices Test", test_audio_devices),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        success = test_func()
        results.append((test_name, success))
    
    print(f"\n{'='*50}")
    print("📋 Test Summary:")
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {test_name}: {status}")
    
    all_passed = all(success for _, success in results)
    if all_passed:
        print("\n🎉 All tests passed! WhisperKey basic functionality is working.")
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")
    
    return all_passed

if __name__ == "__main__":
    main()
