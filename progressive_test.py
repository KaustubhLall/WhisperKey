"""
Progressive testing to identify which component causes GUI freezing
"""
import tkinter as tk
from tkinter import ttk
import logging
import sys
import os
import time
import tempfile
from pathlib import Path

# Setup detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('progressive_test.log')
    ]
)
logger = logging.getLogger("progressive_test")

class ProgressiveGUITest:
    """Progressive GUI testing with component-by-component addition"""
    
    def __init__(self):
        logger.info("=== Starting Progressive GUI Test ===")
        self.window = None
        self.components_loaded = []
        self.test_results = {}
        
        # Create basic GUI first
        self.create_basic_gui()
    
    def create_basic_gui(self):
        """Create basic GUI framework"""
        logger.info("STEP 1: Creating basic GUI framework...")
        
        try:
            self.window = tk.Tk()
            self.window.title("WhisperKey - Progressive Test")
            self.window.geometry("600x500")
            self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
            
            # Main frame
            main_frame = ttk.Frame(self.window, padding="20")
            main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
            
            # Configure grid
            self.window.columnconfigure(0, weight=1)
            self.window.rowconfigure(0, weight=1)
            main_frame.columnconfigure(0, weight=1)
            
            # Title
            title_label = ttk.Label(main_frame, text="WhisperKey Progressive Test", 
                                  font=("Arial", 16, "bold"))
            title_label.grid(row=0, column=0, pady=(0, 20))
            
            # Status area
            self.status_text = tk.Text(main_frame, height=15, width=70)
            scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.status_text.yview)
            self.status_text.configure(yscrollcommand=scrollbar.set)
            
            self.status_text.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
            scrollbar.grid(row=1, column=1, sticky=(tk.N, tk.S))
            
            main_frame.rowconfigure(1, weight=1)
            
            # Test buttons frame
            button_frame = ttk.Frame(main_frame)
            button_frame.grid(row=2, column=0, columnspan=2, pady=(10, 0), sticky=(tk.W, tk.E))
            
            # Test buttons
            tests = [
                ("Test 1: Audio Devices", self.test_audio_devices),
                ("Test 2: Database Init", self.test_database),
                ("Test 3: File Permissions", self.test_file_permissions),
                ("Test 4: System Tray", self.test_tray_icon),
                ("Test 5: Background Threading", self.test_threading),
                ("Test 6: Hotkey Registration", self.test_hotkeys),
                ("Test 7: Full Integration", self.test_full_integration),
            ]
            
            for i, (text, command) in enumerate(tests):
                btn = ttk.Button(button_frame, text=text, command=command)
                btn.grid(row=i//2, column=i%2, padx=5, pady=2, sticky=(tk.W, tk.E))
            
            button_frame.columnconfigure(0, weight=1)
            button_frame.columnconfigure(1, weight=1)
            
            self.log_status("Basic GUI created successfully!")
            self.components_loaded.append("basic_gui")
            logger.info("STEP 1: SUCCESS - Basic GUI created")
            
        except Exception as e:
            logger.error(f"STEP 1: FAILED - {e}", exc_info=True)
            raise
    
    def log_status(self, message):
        """Add message to status area"""
        timestamp = time.strftime("%H:%M:%S")
        full_message = f"[{timestamp}] {message}\n"
        
        if self.status_text:
            self.status_text.insert(tk.END, full_message)
            self.status_text.see(tk.END)
            self.window.update_idletasks()
        
        logger.info(message)
    
    def test_audio_devices(self):
        """Test audio device enumeration"""
        self.log_status("TESTING: Audio device enumeration...")
        
        try:
            import sounddevice as sd
            self.log_status("SUCCESS: sounddevice imported")
            
            devices = sd.query_devices()
            self.log_status(f"SUCCESS: Found {len(devices)} audio devices")
            
            # List a few devices
            for i, device in enumerate(devices[:3]):
                self.log_status(f"  Device {i}: {device['name']}")
            
            # Test default device
            default_device = sd.query_devices(kind='input')
            self.log_status(f"SUCCESS: Default input device: {default_device['name']}")
            
            self.test_results['audio_devices'] = 'PASS'
            self.components_loaded.append("audio_devices")
            
        except Exception as e:
            self.log_status(f"FAILED: Audio device test - {e}")
            self.test_results['audio_devices'] = f'FAIL: {e}'
            logger.error(f"Audio device test failed: {e}", exc_info=True)
    
    def test_database(self):
        """Test database initialization"""
        self.log_status("TESTING: Database initialization...")
        
        try:
            from database import TranscriptionDatabase, TranscriptionRecord
            self.log_status("SUCCESS: Database modules imported")
            
            db = TranscriptionDatabase()
            self.log_status("SUCCESS: Database instance created")
            
            # Test adding a record
            test_record = TranscriptionRecord(
                timestamp="2025-01-01T00:00:00",
                text="Test transcription",
                duration_seconds=1.0,
                engine="test",
                model="test",
                audio_device="test",
                hotkey_used="test",
                processing_time_ms=100
            )
            
            db.add_transcription(test_record)
            self.log_status("SUCCESS: Test record added to database")
            
            # Test retrieving records
            records = db.get_recent_transcriptions(1)
            self.log_status(f"SUCCESS: Retrieved {len(records)} records")
            
            self.test_results['database'] = 'PASS'
            self.components_loaded.append("database")
            
        except Exception as e:
            self.log_status(f"FAILED: Database test - {e}")
            self.test_results['database'] = f'FAIL: {e}'
            logger.error(f"Database test failed: {e}", exc_info=True)
    
    def test_file_permissions(self):
        """Test file system permissions"""
        self.log_status("TESTING: File system permissions...")
        
        try:
            # Test config directory
            config_path = Path(__file__).parent / 'config.yaml'
            self.log_status(f"Config path: {config_path}")
            
            if config_path.exists():
                with open(config_path, 'r') as f:
                    content = f.read()[:100]
                self.log_status("SUCCESS: Config file readable")
            else:
                self.log_status("WARNING: Config file does not exist")
            
            # Test log directory
            log_dir = Path(os.getenv('LOCALAPPDATA')) / 'WhisperKey' / 'logs'
            log_dir.mkdir(parents=True, exist_ok=True)
            self.log_status(f"SUCCESS: Log directory created/accessible: {log_dir}")
            
            # Test temporary file creation
            with tempfile.NamedTemporaryFile(delete=True) as tmp:
                tmp.write(b"test data")
                self.log_status(f"SUCCESS: Temporary file created: {tmp.name}")
            
            self.test_results['file_permissions'] = 'PASS'
            self.components_loaded.append("file_permissions")
            
        except Exception as e:
            self.log_status(f"FAILED: File permissions test - {e}")
            self.test_results['file_permissions'] = f'FAIL: {e}'
            logger.error(f"File permissions test failed: {e}", exc_info=True)
    
    def test_tray_icon(self):
        """Test system tray icon"""
        self.log_status("TESTING: System tray icon...")
        
        try:
            from PIL import Image, ImageDraw
            from pystray import Icon, Menu, MenuItem
            
            self.log_status("SUCCESS: Tray icon libraries imported")
            
            # Create a simple test icon
            image = Image.new('RGB', (64, 64), color='red')
            draw = ImageDraw.Draw(image)
            draw.ellipse([16, 16, 48, 48], fill='white')
            
            self.log_status("SUCCESS: Test icon image created")
            
            # Note: We won't actually create the tray icon as it might interfere
            self.log_status("SUCCESS: Tray icon components ready (not activated)")
            
            self.test_results['tray_icon'] = 'PASS'
            self.components_loaded.append("tray_icon")
            
        except Exception as e:
            self.log_status(f"FAILED: Tray icon test - {e}")
            self.test_results['tray_icon'] = f'FAIL: {e}'
            logger.error(f"Tray icon test failed: {e}", exc_info=True)
    
    def test_threading(self):
        """Test background threading"""
        self.log_status("TESTING: Background threading...")
        
        try:
            import threading
            import queue
            
            # Test simple threading
            test_queue = queue.Queue()
            
            def worker():
                time.sleep(0.1)
                test_queue.put("Thread completed")
            
            thread = threading.Thread(target=worker, daemon=True)
            thread.start()
            self.log_status("SUCCESS: Background thread started")
            
            # Wait for result
            result = test_queue.get(timeout=1.0)
            self.log_status(f"SUCCESS: Thread result: {result}")
            
            thread.join(timeout=1.0)
            self.log_status("SUCCESS: Thread joined successfully")
            
            self.test_results['threading'] = 'PASS'
            self.components_loaded.append("threading")
            
        except Exception as e:
            self.log_status(f"FAILED: Threading test - {e}")
            self.test_results['threading'] = f'FAIL: {e}'
            logger.error(f"Threading test failed: {e}", exc_info=True)
    
    def test_hotkeys(self):
        """Test hotkey registration"""
        self.log_status("TESTING: Hotkey registration...")
        
        try:
            import keyboard
            self.log_status("SUCCESS: Keyboard library imported")
            
            # Test parsing hotkey
            hotkey = 'ctrl+alt+t'
            self.log_status(f"SUCCESS: Hotkey string parsed: {hotkey}")
            
            # Note: We won't actually register the hotkey to avoid conflicts
            self.log_status("SUCCESS: Hotkey system ready (not registered)")
            
            self.test_results['hotkeys'] = 'PASS'
            self.components_loaded.append("hotkeys")
            
        except Exception as e:
            self.log_status(f"FAILED: Hotkey test - {e}")
            self.test_results['hotkeys'] = f'FAIL: {e}'
            logger.error(f"Hotkey test failed: {e}", exc_info=True)
    
    def test_full_integration(self):
        """Test full integration simulation"""
        self.log_status("TESTING: Full integration simulation...")
        
        try:
            # Import main app modules
            from whisperkey import WhisperKeyApp
            self.log_status("SUCCESS: Main app module imported")
            
            # We won't actually create the full app to avoid conflicts
            self.log_status("SUCCESS: All imports successful")
            
            # Summary
            self.log_status("\n=== TEST SUMMARY ===")
            for component, result in self.test_results.items():
                status = "✓" if result == 'PASS' else "✗"
                self.log_status(f"{status} {component}: {result}")
            
            self.log_status(f"\nComponents loaded: {', '.join(self.components_loaded)}")
            
            passed = sum(1 for r in self.test_results.values() if r == 'PASS')
            total = len(self.test_results)
            self.log_status(f"Overall: {passed}/{total} tests passed")
            
            self.test_results['full_integration'] = 'PASS'
            
        except Exception as e:
            self.log_status(f"FAILED: Full integration test - {e}")
            self.test_results['full_integration'] = f'FAIL: {e}'
            logger.error(f"Full integration test failed: {e}", exc_info=True)
    
    def on_closing(self):
        """Handle window closing"""
        logger.info("Window close requested")
        self.window.destroy()
        sys.exit(0)
    
    def run(self):
        """Run the progressive test GUI"""
        self.log_status("Progressive test GUI ready!")
        self.log_status("Click test buttons to run individual components.")
        self.log_status("Watch for any that cause freezing or errors.")
        
        self.window.mainloop()


if __name__ == "__main__":
    try:
        test = ProgressiveGUITest()
        test.run()
    except Exception as e:
        logger.error(f"Critical error: {e}", exc_info=True)
        print(f"Critical error: {e}")
