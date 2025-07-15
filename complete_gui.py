"""
Complete WhisperKey GUI implementation with cost tracking
Built using the working progressive test foundation
"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import logging
from datetime import datetime
from typing import Optional, Callable
import pyperclip
from pynput import keyboard, mouse

# Import WhisperKey components (all tested to work individually)
from database import TranscriptionDatabase, TranscriptionRecord
from billing import OpenAIBillingAPI

logger = logging.getLogger("complete_gui")


class HotkeyRecorder:
    """Records hotkey combinations including mouse buttons"""
    
    def __init__(self, callback: Callable[[str], None]):
        self.callback = callback
        self.recording = False
        self.pressed_keys = set()
        self.keyboard_listener = None
        self.mouse_listener = None
        
    def start_recording(self):
        """Start recording hotkey combination"""
        self.recording = True
        self.pressed_keys.clear()
        
        self.keyboard_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release
        )
        
        self.mouse_listener = mouse.Listener(
            on_click=self._on_mouse_click
        )
        
        self.keyboard_listener.start()
        self.mouse_listener.start()
    
    def stop_recording(self):
        """Stop recording and return the hotkey combination"""
        self.recording = False
        
        if self.keyboard_listener:
            self.keyboard_listener.stop()
        if self.mouse_listener:
            self.mouse_listener.stop()
        
        if self.pressed_keys:
            hotkey_str = self._format_hotkey()
            self.callback(hotkey_str)
    
    def _on_key_press(self, key):
        if not self.recording:
            return
        
        try:
            key_str = key.char if hasattr(key, 'char') and key.char else str(key).replace('Key.', '')
            self.pressed_keys.add(key_str)
        except AttributeError:
            key_str = str(key).replace('Key.', '')
            self.pressed_keys.add(key_str)
    
    def _on_key_release(self, key):
        if not self.recording:
            return
        
        # Stop recording when any key is released
        self.stop_recording()
    
    def _on_mouse_click(self, x, y, button, pressed):
        if not self.recording or not pressed:
            return
        
        button_str = f"mouse_{button.name}"
        self.pressed_keys.add(button_str)
        self.stop_recording()
    
    def _format_hotkey(self) -> str:
        """Format the pressed keys into a hotkey string"""
        if not self.pressed_keys:
            return ""
        
        # Sort keys for consistent formatting
        sorted_keys = sorted(list(self.pressed_keys))
        return "+".join(sorted_keys)


class CompleteWhisperKeyGUI:
    """Complete GUI with all WhisperKey functionality + cost tracking"""
    
    def __init__(self, app_instance):
        logger.info("=== Initializing Complete WhisperKey GUI ===")
        
        self.app = app_instance
        self.db = TranscriptionDatabase()
        self.window = None
        self.is_visible = False
        
        # Cost tracking
        self.billing = None
        if hasattr(app_instance, 'config'):
            api_key = app_instance.config.get('transcription', {}).get('api_key', '')
            if api_key:
                self.billing = OpenAIBillingAPI(api_key, app_instance.config)
        
        # GUI components
        self.status_label = None
        self.cost_label = None
        self.device_combo = None
        self.engine_combo = None
        self.hotkey_var = None
        self.recent_listbox = None
        
        # Initialize GUI
        self.create_window()
        logger.info("=== Complete WhisperKey GUI Initialized ===")
    
    def create_window(self):
        """Create the main GUI window using proven working approach"""
        logger.info("Creating main window...")
        
        try:
            # Use direct Tk() approach that worked in progressive test
            self.window = tk.Tk()
            self.window.title("WhisperKey - Voice Transcription Assistant")
            self.window.geometry("800x700")
            self.window.resizable(True, True)
            self.window.minsize(600, 500)
            
            # Configure colors
            self.colors = {
                'bg_primary': '#2b2b2b',
                'bg_secondary': '#3d3d3d',
                'bg_accent': '#4a90e2',
                'text_primary': '#ffffff',
                'text_secondary': '#b0b0b0',
                'success': '#28a745',
                'warning': '#ffc107',
                'danger': '#dc3545'
            }
            
            self.window.configure(bg=self.colors['bg_primary'])
            # Window close protocol will be set after widget creation
            
            # Create all widgets
            self.create_widgets()
            
            # Start cost tracking if enabled
            self.start_cost_tracking()
            
            # Initially hide window but keep it available for mainloop
            self.window.withdraw()
            self.is_visible = False
            
            # Set up window to handle mainloop properly
            self.window.protocol("WM_DELETE_WINDOW", self.on_window_close)
            
            # Make window available but hidden for tray integration
            logger.info("GUI window ready for tray integration with mainloop support")
            
            logger.info("Main window created successfully")
            
        except Exception as e:
            logger.error(f"Error creating window: {e}", exc_info=True)
            raise
    
    def create_widgets(self):
        """Create all GUI widgets"""
        logger.info("Creating GUI widgets...")
        
        try:
            # Main container
            main_frame = ttk.Frame(self.window, padding="20")
            main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
            
            # Configure grid weights
            self.window.columnconfigure(0, weight=1)
            self.window.rowconfigure(0, weight=1)
            main_frame.columnconfigure(0, weight=1)
            
            current_row = 0
            
            # Header section
            current_row = self.create_header_section(main_frame, current_row)
            
            # Status section
            current_row = self.create_status_section(main_frame, current_row)
            
            # Cost tracking section (if enabled)
            if self.billing and self.billing.is_cost_tracking_enabled():
                current_row = self.create_cost_section(main_frame, current_row)
            
            # Settings section
            current_row = self.create_settings_section(main_frame, current_row)
            
            # Recent transcriptions section
            current_row = self.create_recent_section(main_frame, current_row)
            
            # Update initial data
            self.update_recent_transcriptions()
            self.update_status("Ready for transcription")
            
            logger.info("All GUI widgets created successfully")
            
        except Exception as e:
            logger.error(f"Error creating widgets: {e}", exc_info=True)
            raise
    
    def create_header_section(self, parent, row):
        """Create header section with title and branding"""
        header_frame = ttk.Frame(parent)
        header_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        header_frame.columnconfigure(0, weight=1)
        
        # Main title
        title_label = ttk.Label(header_frame, text="🎤 WhisperKey", 
                               font=("Segoe UI", 18, "bold"))
        title_label.grid(row=0, column=0, sticky=tk.W)
        
        # Subtitle
        subtitle_label = ttk.Label(header_frame, 
                                  text="Voice Transcription Assistant with Cost Tracking",
                                  font=("Segoe UI", 10))
        subtitle_label.grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        
        return row + 1
    
    def create_status_section(self, parent, row):
        """Create status display section"""
        status_frame = ttk.LabelFrame(parent, text="Status", padding="15")
        status_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        status_frame.columnconfigure(1, weight=1)
        
        # Status icon and text
        ttk.Label(status_frame, text="🔍", font=("Segoe UI", 12)).grid(row=0, column=0, padx=(0, 10))
        
        self.status_label = ttk.Label(status_frame, text="Ready for transcription", 
                                     font=("Segoe UI", 11, "bold"))
        self.status_label.grid(row=0, column=1, sticky=tk.W)
        
        return row + 1
    
    def create_cost_section(self, parent, row):
        """Create cost tracking section"""
        cost_frame = ttk.LabelFrame(parent, text="Cost Tracking", padding="15")
        cost_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        cost_frame.columnconfigure(1, weight=1)
        
        # Cost display
        ttk.Label(cost_frame, text="💰", font=("Segoe UI", 12)).grid(row=0, column=0, padx=(0, 10))
        
        self.cost_label = ttk.Label(cost_frame, text="Transcription spend (Mo-to-date): $0.00",
                                   font=("Segoe UI", 11))
        self.cost_label.grid(row=0, column=1, sticky=tk.W)
        
        # Refresh button
        refresh_btn = ttk.Button(cost_frame, text="🔄 Refresh", 
                                command=self.refresh_costs, width=12)
        refresh_btn.grid(row=0, column=2, padx=(10, 0))
        
        # Click for details
        details_label = ttk.Label(cost_frame, text="Click for detailed breakdown",
                                 font=("Segoe UI", 9), foreground="gray")
        details_label.grid(row=1, column=1, sticky=tk.W, pady=(5, 0))
        details_label.bind("<Button-1>", self.show_cost_breakdown)
        
        # Update cost display
        self.update_cost_display()
        
        return row + 1
    
    def create_settings_section(self, parent, row):
        """Create settings configuration section"""
        settings_frame = ttk.LabelFrame(parent, text="Configuration", padding="15")
        settings_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        settings_frame.columnconfigure(1, weight=1)
        
        current_row = 0
        
        # Hotkey setting
        ttk.Label(settings_frame, text="🎯 Hotkey:").grid(row=current_row, column=0, 
                                                         sticky=tk.W, padx=(0, 10), pady=5)
        
        hotkey_frame = ttk.Frame(settings_frame)
        hotkey_frame.grid(row=current_row, column=1, sticky=(tk.W, tk.E), pady=5)
        hotkey_frame.columnconfigure(0, weight=1)
        
        self.hotkey_var = tk.StringVar(value=self.app.config.get('hotkey', 'ctrl+alt+enter'))
        hotkey_entry = ttk.Entry(hotkey_frame, textvariable=self.hotkey_var)
        hotkey_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 8))
        
        record_btn = ttk.Button(hotkey_frame, text="📝 Record", 
                               command=self.record_hotkey, width=10)
        record_btn.grid(row=0, column=1)
        
        current_row += 1
        
        # Audio device setting
        ttk.Label(settings_frame, text="🎤 Audio Device:").grid(row=current_row, column=0,
                                                               sticky=tk.W, padx=(0, 10), pady=5)
        
        self.device_combo = ttk.Combobox(settings_frame, width=40)
        self.device_combo.grid(row=current_row, column=1, sticky=(tk.W, tk.E), pady=5)
        self.update_audio_devices()
        
        current_row += 1
        
        # Engine setting
        ttk.Label(settings_frame, text="🤖 Engine:").grid(row=current_row, column=0,
                                                         sticky=tk.W, padx=(0, 10), pady=5)
        
        engine_var = tk.StringVar(value=self.app.config.get('transcription', {}).get('engine', 'openai'))
        self.engine_combo = ttk.Combobox(settings_frame, textvariable=engine_var,
                                        values=['openai', 'vosk'], state='readonly', width=40)
        self.engine_combo.grid(row=current_row, column=1, sticky=(tk.W, tk.E), pady=5)
        
        current_row += 1
        
        # Save button
        save_btn = ttk.Button(settings_frame, text="💾 Save Settings", 
                             command=self.save_settings)
        save_btn.grid(row=current_row, column=0, columnspan=2, pady=(15, 0))
        
        return row + 1
    
    def create_recent_section(self, parent, row):
        """Create recent transcriptions section"""
        recent_frame = ttk.LabelFrame(parent, text="Recent Transcriptions", padding="15")
        recent_frame.grid(row=row, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 0))
        recent_frame.columnconfigure(0, weight=1)
        recent_frame.rowconfigure(1, weight=1)
        
        # Header with instructions
        header_label = ttk.Label(recent_frame, 
                                text="Double-click to copy transcription to clipboard",
                                font=("Segoe UI", 9), foreground="gray")
        header_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        
        # Listbox with scrollbar
        list_frame = ttk.Frame(recent_frame)
        list_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        self.recent_listbox = tk.Listbox(list_frame, height=8, font=("Segoe UI", 10))
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.recent_listbox.yview)
        self.recent_listbox.configure(yscrollcommand=scrollbar.set)
        
        self.recent_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Bind double-click event
        self.recent_listbox.bind("<Double-Button-1>", self.copy_selected_transcription)
        
        # Buttons frame
        buttons_frame = ttk.Frame(recent_frame)
        buttons_frame.grid(row=2, column=0, pady=(10, 0), sticky=(tk.W, tk.E))
        
        ttk.Button(buttons_frame, text="📋 Copy Selected", 
                  command=self.copy_selected_transcription).grid(row=0, column=0, padx=(0, 10))
        
        ttk.Button(buttons_frame, text="📜 Full History", 
                  command=self.show_full_history).grid(row=0, column=1)
        
        return row + 1
    
    # Event handler methods
    def update_status(self, status: str):
        """Update the status label - thread-safe version"""
        def _update_status_main_thread():
            if self.status_label:
                self.status_label.configure(text=status)
                logger.debug(f"Status updated: {status}")
        
        # Ensure GUI operations run on main thread
        if self.window and hasattr(self.window, 'after'):
            self.window.after(0, _update_status_main_thread)
        else:
            _update_status_main_thread()
    
    def update_cost_display(self):
        """Update the cost display with current month-to-date spend - thread-safe version"""
        if not self.billing or not self.billing.is_cost_tracking_enabled():
            return
        
        def _update_cost_display_main_thread():
            try:
                now = datetime.now()
                monthly_spend = self.billing.get_monthly_spend(now.year, now.month)
                
                if self.cost_label:
                    self.cost_label.configure(text=f"Transcription spend (Mo-to-date): ${monthly_spend:.2f}")
                    logger.debug(f"Cost display updated: ${monthly_spend:.2f}")
                    
            except Exception as e:
                logger.error(f"Error updating cost display: {e}")
                if self.cost_label:
                    self.cost_label.configure(text="Cost data unavailable (will retry)")
        
        # Ensure GUI operations run on main thread
        if self.window and hasattr(self.window, 'after'):
            self.window.after(0, _update_cost_display_main_thread)
        else:
            _update_cost_display_main_thread()
    
    def refresh_costs(self):
        """Manual cost refresh triggered by user"""
        if not self.billing or not self.billing.is_cost_tracking_enabled():
            self.update_status("⚠️ Cost tracking is disabled in configuration")
            return
        
        def refresh_callback(success):
            if success:
                self.update_cost_display()
                self.update_status("✅ Cost data refreshed successfully!")
            else:
                self.update_status("❌ Failed to refresh cost data. Check your API key and connection.")
        
        # Run refresh in background thread
        threading.Thread(target=lambda: self.billing.manual_refresh(refresh_callback), daemon=True).start()
        
        # Update status
        self.update_status("Refreshing cost data...")
    
    def show_cost_breakdown(self, event=None):
        """Show detailed cost breakdown dialog"""
        if not self.billing or not self.billing.is_cost_tracking_enabled():
            return
        
        try:
            # Create breakdown window
            breakdown_window = tk.Toplevel(self.window)
            breakdown_window.title("Cost Breakdown")
            breakdown_window.geometry("600x400")
            breakdown_window.transient(self.window)
            
            # Main frame
            main_frame = ttk.Frame(breakdown_window, padding="20")
            main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
            breakdown_window.columnconfigure(0, weight=1)
            breakdown_window.rowconfigure(0, weight=1)
            
            # Title
            ttk.Label(main_frame, text="💰 Cost Breakdown", font=("Segoe UI", 14, "bold")).grid(row=0, column=0, pady=(0, 20))
            
            # Get cost history
            costs = self.billing.get_cost_breakdown(30)
            
            if not costs:
                ttk.Label(main_frame, text="No cost data available. Try refreshing.").grid(row=1, column=0)
                return
            
            # Create treeview for cost data
            columns = ('Date', 'Cost (USD)', 'Last Updated')
            tree = ttk.Treeview(main_frame, columns=columns, show='headings', height=15)
            
            # Configure columns
            tree.heading('Date', text='Date')
            tree.heading('Cost (USD)', text='Cost (USD)')
            tree.heading('Last Updated', text='Last Updated')
            
            tree.column('Date', width=100)
            tree.column('Cost (USD)', width=100)
            tree.column('Last Updated', width=200)
            
            # Add scrollbar
            scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)
            
            # Pack widgets
            tree.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
            scrollbar.grid(row=1, column=1, sticky=(tk.N, tk.S))
            
            main_frame.columnconfigure(0, weight=1)
            main_frame.rowconfigure(1, weight=1)
            
            # Populate data
            total_cost = 0.0
            for cost in costs:
                tree.insert('', tk.END, values=(
                    cost.date,
                    f"${cost.cost_usd:.4f}",
                    cost.last_updated.split('T')[0] if 'T' in cost.last_updated else cost.last_updated
                ))
                total_cost += cost.cost_usd
            
            # Total label
            ttk.Label(main_frame, text=f"Total: ${total_cost:.2f}", 
                     font=("Segoe UI", 12, "bold")).grid(row=2, column=0, pady=(10, 0))
            
        except Exception as e:
            logger.error(f"Error showing cost breakdown: {e}")
            messagebox.showerror("Error", f"Failed to show cost breakdown: {e}")
    
    def update_audio_devices(self):
        """Update the audio device combobox"""
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            
            device_names = []
            for i, device in enumerate(devices):
                if device['max_input_channels'] > 0:  # Input devices only
                    device_names.append(f"{i}: {device['name']}")
            
            if self.device_combo:
                self.device_combo['values'] = device_names
                if device_names:
                    # Set default device
                    default_device = sd.query_devices(kind='input')
                    default_name = f"{default_device['index']}: {default_device['name']}"
                    if default_name in device_names:
                        self.device_combo.set(default_name)
                    else:
                        self.device_combo.set(device_names[0])
                        
            logger.debug(f"Audio devices updated: {len(device_names)} devices found")
            
        except Exception as e:
            logger.error(f"Error updating audio devices: {e}")
            if self.device_combo:
                self.device_combo['values'] = ["Error loading devices"]
    
    def record_hotkey(self):
        """Record a new hotkey combination"""
        try:
            # Update status with instructions instead of popup
            self.update_status("🎯 Hotkey Recording: Press and hold your desired key combination (including mouse buttons)")
            
            # Update button text to show recording state
            record_btn = None
            for widget in self.window.winfo_children():
                if hasattr(widget, 'winfo_children'):
                    for child in widget.winfo_children():
                        if hasattr(child, 'winfo_children'):
                            for grandchild in child.winfo_children():
                                if isinstance(grandchild, ttk.Button) and "Record" in str(grandchild.cget('text')):
                                    record_btn = grandchild
                                    break
            
            if record_btn:
                record_btn.configure(text="🔴 Recording...", state='disabled')
            
            # Update status
            self.update_status("Recording hotkey... Press your key combination now!")
            
            def on_hotkey_recorded(hotkey_str):
                """Callback when hotkey is recorded"""
                try:
                    if hotkey_str:
                        self.hotkey_var.set(hotkey_str)
                        self.update_status(f"✅ Hotkey recorded: {hotkey_str} - Don't forget to save settings!")
                    else:
                        self.update_status("❌ Hotkey recording cancelled - No hotkey was recorded.")
                    
                    # Reset button
                    if record_btn:
                        record_btn.configure(text="📝 Record", state='normal')
                        
                except Exception as e:
                    logger.error(f"Error in hotkey callback: {e}")
                    if record_btn:
                        record_btn.configure(text="📝 Record", state='normal')
            
            # Start recording with auto-stop timer
            self.hotkey_recorder = HotkeyRecorder(on_hotkey_recorded)
            self.hotkey_recorder.start_recording()
            
            # Auto-stop after 10 seconds if no input
            def auto_stop():
                if self.hotkey_recorder and self.hotkey_recorder.recording:
                    self.hotkey_recorder.stop_recording()
                    self.update_status("Hotkey recording timed out")
                    if record_btn:
                        record_btn.configure(text="📝 Record", state='normal')
            
            threading.Timer(10.0, auto_stop).start()
            
        except Exception as e:
            logger.error(f"Error starting hotkey recording: {e}")
            messagebox.showerror("Error", f"Failed to start hotkey recording: {e}")
    
    def save_settings(self):
        """Save current settings to configuration"""
        try:
            # Update config with current values
            if self.hotkey_var:
                self.app.config['hotkey'] = self.hotkey_var.get()
            
            if self.device_combo:
                device_text = self.device_combo.get()
                if ':' in device_text:
                    device_index = int(device_text.split(':')[0])
                    self.app.config['audio_device_index'] = device_index
            
            if self.engine_combo:
                engine = self.engine_combo.get()
                if 'transcription' not in self.app.config:
                    self.app.config['transcription'] = {}
                self.app.config['transcription']['engine'] = engine
            
            # Save to file
            self.app.save_config()
            
            # Update hotkey registration
            self.app.update_hotkey()
            
            self.update_status("✅ Settings saved successfully!")
            logger.info("Settings saved")
            
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            self.update_status(f"❌ Failed to save settings: {e}")
    
    def update_recent_transcriptions(self):
        """Update the recent transcriptions list - thread-safe version"""
        def _update_recent_transcriptions_main_thread():
            try:
                if not self.recent_listbox:
                    return
                
                # Clear current items
                self.recent_listbox.delete(0, tk.END)
                
                # Get recent transcriptions
                recent_records = self.db.get_recent_transcriptions(10)
                
                for record in recent_records:
                    # Format display text
                    timestamp = record.timestamp.split('T')[0] if 'T' in record.timestamp else record.timestamp
                    preview = record.text[:60] + "..." if len(record.text) > 60 else record.text
                    display_text = f"[{timestamp}] {preview}"
                    
                    self.recent_listbox.insert(tk.END, display_text)
                
                if not recent_records:
                    self.recent_listbox.insert(tk.END, "No transcriptions yet")
                    
                logger.debug(f"Recent transcriptions updated: {len(recent_records)} records")
                
            except Exception as e:
                logger.error(f"Error updating recent transcriptions: {e}")
        
        # Ensure GUI operations run on main thread
        if self.window and hasattr(self.window, 'after'):
            self.window.after(0, _update_recent_transcriptions_main_thread)
        else:
            _update_recent_transcriptions_main_thread()
    
    def copy_selected_transcription(self, event=None):
        """Copy selected transcription to clipboard"""
        try:
            if not self.recent_listbox:
                return
            
            selection = self.recent_listbox.curselection()
            if not selection:
                self.update_status("⚠️ Please select a transcription to copy")
                return
            
            index = selection[0]
            recent_records = self.db.get_recent_transcriptions(10)
            
            if index < len(recent_records):
                text = recent_records[index].text
                pyperclip.copy(text)
                self.update_status("✅ Transcription copied to clipboard!")
                
                # Auto-hide window after copying
                threading.Timer(2.0, self.hide_window).start()
            
        except Exception as e:
            logger.error(f"Error copying transcription: {e}")
            messagebox.showerror("Error", f"Failed to copy transcription: {e}")
    
    def show_full_history(self):
        """Show full transcription history in a new window"""
        try:
            # Create history window
            history_window = tk.Toplevel(self.window)
            history_window.title("Transcription History")
            history_window.geometry("900x600")
            history_window.transient(self.window)
            
            # Main frame
            main_frame = ttk.Frame(history_window, padding="20")
            main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
            history_window.columnconfigure(0, weight=1)
            history_window.rowconfigure(0, weight=1)
            
            # Title
            ttk.Label(main_frame, text="📜 Transcription History", 
                     font=("Segoe UI", 14, "bold")).grid(row=0, column=0, pady=(0, 20))
            
            # Create treeview
            columns = ('Date', 'Preview', 'Duration', 'Engine')
            tree = ttk.Treeview(main_frame, columns=columns, show='headings', height=20)
            
            # Configure columns
            tree.heading('Date', text='Date')
            tree.heading('Preview', text='Text Preview')
            tree.heading('Duration', text='Duration (s)')
            tree.heading('Engine', text='Engine')
            
            tree.column('Date', width=100)
            tree.column('Preview', width=400)
            tree.column('Duration', width=100)
            tree.column('Engine', width=100)
            
            # Add scrollbar
            scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)
            
            # Pack widgets
            tree.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
            scrollbar.grid(row=1, column=1, sticky=(tk.N, tk.S))
            
            main_frame.columnconfigure(0, weight=1)
            main_frame.rowconfigure(1, weight=1)
            
            # Load history data
            all_records = self.db.get_all_transcriptions(100)
            
            for record in all_records:
                date = record.timestamp.split('T')[0] if 'T' in record.timestamp else record.timestamp
                preview = record.text[:50] + "..." if len(record.text) > 50 else record.text
                duration = f"{record.duration_seconds:.1f}"
                
                tree.insert('', tk.END, values=(date, preview, duration, record.engine))
            
            # Double-click to copy
            def copy_from_history(event):
                selection = tree.selection()
                if selection:
                    item = tree.item(selection[0])
                    # Find the corresponding record and copy full text
                    date = item['values'][0]
                    for record in all_records:
                        record_date = record.timestamp.split('T')[0] if 'T' in record.timestamp else record.timestamp
                        if record_date == date:
                            pyperclip.copy(record.text)
                            messagebox.showinfo("Copied", "Full transcription copied to clipboard!")
                            break
            
            tree.bind('<Double-Button-1>', copy_from_history)
            
        except Exception as e:
            logger.error(f"Error showing full history: {e}")
            messagebox.showerror("Error", f"Failed to show history: {e}")
    
    def start_cost_tracking(self):
        """Start background cost tracking if enabled"""
        if not self.billing or not self.billing.is_cost_tracking_enabled():
            logger.info("Cost tracking disabled")
            return
        
        def cost_sync_worker():
            """Background worker for cost syncing"""
            while True:
                try:
                    if self.billing.should_sync_costs():
                        logger.info("Starting automatic cost sync")
                        success = self.billing.sync_daily_costs()
                        if success:
                            # Update UI on main thread
                            self.window.after(0, self.update_cost_display)
                        
                    # Check every hour
                    time.sleep(3600)
                    
                except Exception as e:
                    logger.error(f"Error in cost sync worker: {e}")
                    time.sleep(3600)  # Wait an hour before retrying
        
        # Start background thread
        cost_thread = threading.Thread(target=cost_sync_worker, daemon=True)
        cost_thread.start()
        logger.info("Cost tracking background worker started")
    
    # Window management methods
    def show_window(self):
        """Show the GUI window"""
        logger.info("Showing GUI window")
        
        try:
            if not self.window:
                logger.error("No window available to show")
                return
            
            self.window.deiconify()
            self.window.lift()
            self.window.focus_force()
            self.is_visible = True
            
            # Update data when showing
            self.update_recent_transcriptions()
            self.update_cost_display()
            
            logger.info("GUI window shown successfully")
            
        except Exception as e:
            logger.error(f"Error showing window: {e}")
    
    def hide_window(self):
        """Hide the GUI window"""
        logger.info("Hiding GUI window")
        
        try:
            if self.window:
                self.window.withdraw()
            self.is_visible = False
            
        except Exception as e:
            logger.error(f"Error hiding window: {e}")
    
    def toggle_window(self):
        """Toggle window visibility"""
        if self.is_visible:
            self.hide_window()
        else:
            self.show_window()
    
    def on_window_close(self):
        """Handle window close button - minimize to tray instead of exit"""
        logger.info("Window close requested - minimizing to tray")
        self.hide_window()
        self.update_status("💡 WhisperKey minimized to system tray. Right-click tray icon to show window.")
        # Don't actually close the window, just hide it
        return "break"  # Prevent default close behavior
    
    def cleanup(self):
        """Clean up GUI resources"""
        logger.info("Cleaning up GUI resources")
        
        try:
            if self.window:
                self.window.destroy()
                self.window = None
                
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


# Test/demo functionality
def test_complete_gui():
    """Test the complete GUI implementation"""
    logger.info("=== Testing Complete WhisperKey GUI ===")
    
    try:
        # Mock app instance for testing
        class MockApp:
            def __init__(self):
                self.config = {
                    'hotkey': 'ctrl+alt+enter',
                    'audio_device_index': None,
                    'transcription': {
                        'engine': 'openai',
                        'api_key': 'test-key'
                    },
                    'cost_tracking': {
                        'enabled': False  # Disabled for testing
                    }
                }
            
            def save_config(self):
                logger.info("Mock: Config saved")
            
            def update_hotkey(self):
                logger.info("Mock: Hotkey updated")
        
        # Create mock app and GUI
        mock_app = MockApp()
        gui = CompleteWhisperKeyGUI(mock_app)
        
        # Show the GUI
        gui.show_window()
        
        logger.info("GUI is now running. Test the functionality!")
        
        # Run the GUI event loop
        gui.window.mainloop()
        
        logger.info("=== Complete GUI Test Finished ===")
        
    except Exception as e:
        logger.error(f"Error in GUI test: {e}", exc_info=True)


if __name__ == "__main__":
    # Setup logging for standalone testing
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('complete_gui_test.log')
        ]
    )
    
    test_complete_gui()
