"""
GUI module for WhisperKey using tkinter
"""
import tkinter as tk
from tkinter import ttk, messagebox, font
import threading
import time
from typing import Callable, List, Optional
import pyperclip
from pynput import keyboard, mouse
from database import TranscriptionRecord, TranscriptionDatabase


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


class WhisperKeyGUI:
    """Main GUI window for WhisperKey"""
    
    def __init__(self, app_instance):
        self.app = app_instance
        self.db = TranscriptionDatabase()
        self.window = None
        self.root = None
        self.is_visible = False
        self.hotkey_recorder = None
        self._mainloop_thread = None
        
        # Fonts
        self.title_font = None
        self.text_font = None
        self.small_font = None
    
    def create_window(self):
        """Create the main GUI window"""
        if self.window:
            self.show_window()
            return
        
        # Use main window instead of Toplevel for better compatibility
        self.window = tk.Tk()
        self.root = self.window  # Keep reference for compatibility
        self.window.title("WhisperKey - Voice Transcription Assistant")
        self.window.geometry("700x600")
        self.window.resizable(True, True)
        self.window.minsize(600, 500)
        
        # Modern color scheme
        self.colors = {
            'bg_primary': '#2b2b2b',      # Dark background
            'bg_secondary': '#3d3d3d',    # Lighter dark for cards
            'bg_accent': '#4a90e2',       # Blue accent
            'text_primary': '#ffffff',    # White text
            'text_secondary': '#b0b0b0',  # Gray text
            'success': '#28a745',         # Green
            'warning': '#ffc107',         # Yellow
            'danger': '#dc3545'           # Red
        }
        
        # Configure fonts
        self.title_font = font.Font(family="Segoe UI", size=16, weight="bold")
        self.text_font = font.Font(family="Segoe UI", size=10)
        self.small_font = font.Font(family="Segoe UI", size=9)
        self.button_font = font.Font(family="Segoe UI", size=10, weight="bold")
        
        # Configure window with modern dark theme
        self.window.configure(bg=self.colors['bg_primary'])
        self.window.protocol("WM_DELETE_WINDOW", self.hide_window)
        
        # Create main interface
        self.create_widgets()
        self.update_recent_transcriptions()
        
        # Start with window hidden
        self.window.withdraw()
        self.is_visible = False
    
    def create_widgets(self):
        """Create all GUI widgets"""
        # Configure modern ttk style
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure dark theme styles
        style.configure('Dark.TFrame', background=self.colors['bg_primary'])
        style.configure('Card.TFrame', background=self.colors['bg_secondary'], relief='flat', borderwidth=1)
        style.configure('Dark.TLabel', background=self.colors['bg_primary'], foreground=self.colors['text_primary'])
        style.configure('Card.TLabel', background=self.colors['bg_secondary'], foreground=self.colors['text_primary'])
        style.configure('Accent.TButton', background=self.colors['bg_accent'], foreground='white', font=self.button_font)
        style.map('Accent.TButton', background=[('active', '#357abd')])
        
        # Main container with dark theme
        main_frame = ttk.Frame(self.window, padding="20", style='Dark.TFrame')
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Modern title with icon
        title_frame = ttk.Frame(main_frame, style='Dark.TFrame')
        title_frame.grid(row=0, column=0, columnspan=2, pady=(0, 30), sticky=(tk.W, tk.E))
        
        title_label = ttk.Label(title_frame, text="🎤 WhisperKey", font=self.title_font, style='Dark.TLabel')
        title_label.grid(row=0, column=0, sticky=tk.W)
        
        subtitle_label = ttk.Label(title_frame, text="Voice Transcription Assistant", font=self.text_font, style='Dark.TLabel')
        subtitle_label.grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        
        # Status section with modern card design
        status_frame = ttk.Frame(main_frame, style='Card.TFrame', padding="15")
        status_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 20))
        status_frame.columnconfigure(1, weight=1)
        
        status_title = ttk.Label(status_frame, text="🔍 Current Status", font=self.text_font, style='Card.TLabel')
        status_title.grid(row=0, column=0, sticky=tk.W, pady=(0, 8))
        
        self.status_label = ttk.Label(status_frame, text="💤 Idle - Ready for dictation", font=self.button_font, style='Card.TLabel')
        self.status_label.grid(row=1, column=0, sticky=tk.W)
        
        # Settings section with modern card design
        settings_frame = ttk.Frame(main_frame, style='Card.TFrame', padding="15")
        settings_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 20))
        settings_frame.columnconfigure(1, weight=1)
        
        settings_title = ttk.Label(settings_frame, text="⚙️ Configuration", font=self.text_font, style='Card.TLabel')
        settings_title.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 15))
        
        # Hotkey setting
        ttk.Label(settings_frame, text="🎯 Hotkey:", font=self.text_font, style='Card.TLabel').grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(5, 0))
        
        hotkey_inner_frame = ttk.Frame(settings_frame, style='Card.TFrame')
        hotkey_inner_frame.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(5, 0))
        hotkey_inner_frame.columnconfigure(0, weight=1)
        
        self.hotkey_var = tk.StringVar(value=self.app.config.get('hotkey', 'ctrl+alt+enter'))
        self.hotkey_entry = ttk.Entry(hotkey_inner_frame, textvariable=self.hotkey_var, font=self.text_font)
        self.hotkey_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 8))
        
        self.record_hotkey_btn = ttk.Button(hotkey_inner_frame, text="📝 Record", command=self.start_hotkey_recording, style='Accent.TButton')
        self.record_hotkey_btn.grid(row=0, column=1)
        
        # Audio device setting
        ttk.Label(settings_frame, text="🎤 Audio Device:", font=self.text_font, style='Card.TLabel').grid(row=2, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        
        self.device_var = tk.StringVar()
        self.device_combo = ttk.Combobox(settings_frame, textvariable=self.device_var, font=self.text_font)
        self.device_combo.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=(10, 0))
        self.update_audio_devices()
        
        # Transcription engine setting
        ttk.Label(settings_frame, text="🤖 Engine:", font=self.text_font, style='Card.TLabel').grid(row=3, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        
        self.engine_var = tk.StringVar(value=self.app.config.get('transcription', {}).get('engine', 'openai'))
        self.engine_combo = ttk.Combobox(settings_frame, textvariable=self.engine_var, 
                                       values=['openai', 'vosk'], font=self.text_font, state='readonly')
        self.engine_combo.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=(10, 0))
        
        # Save settings button
        save_btn = ttk.Button(settings_frame, text="💾 Save Settings", command=self.save_settings, style='Accent.TButton')
        save_btn.grid(row=4, column=0, columnspan=2, pady=(20, 0))
        
        # Recent transcriptions section with modern card design
        recent_frame = ttk.Frame(main_frame, style='Card.TFrame', padding="15")
        recent_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        recent_frame.columnconfigure(0, weight=1)
        recent_frame.rowconfigure(1, weight=1)
        
        recent_title = ttk.Label(recent_frame, text="📝 Recent Transcriptions", font=self.text_font, style='Card.TLabel')
        recent_title.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))
        
        # Recent transcriptions list with modern styling
        self.recent_listbox = tk.Listbox(
            recent_frame, 
            height=6, 
            font=self.text_font,
            bg=self.colors['bg_primary'],
            fg=self.colors['text_primary'],
            selectbackground=self.colors['bg_accent'],
            selectforeground='white',
            borderwidth=0,
            highlightthickness=0
        )
        self.recent_listbox.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 15))
        self.recent_listbox.bind('<Double-Button-1>', self.copy_selected_transcription)
        self.recent_listbox.bind('<Return>', self.copy_selected_transcription)
        
        # Scrollbar for recent transcriptions
        recent_scrollbar = ttk.Scrollbar(recent_frame, orient="vertical", command=self.recent_listbox.yview)
        recent_scrollbar.grid(row=1, column=1, sticky=(tk.N, tk.S), pady=(0, 15))
        self.recent_listbox.configure(yscrollcommand=recent_scrollbar.set)
        
        # Buttons frame with modern styling
        buttons_frame = ttk.Frame(recent_frame, style='Card.TFrame')
        buttons_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E))
        
        ttk.Button(buttons_frame, text="📋 Copy Selected", command=self.copy_selected_transcription, style='Accent.TButton').grid(row=0, column=0, padx=(0, 8))
        ttk.Button(buttons_frame, text="📚 View All History", command=self.show_full_history, style='Accent.TButton').grid(row=0, column=1, padx=(0, 8))
        ttk.Button(buttons_frame, text="🔄 Refresh", command=self.update_recent_transcriptions, style='Accent.TButton').grid(row=0, column=2)
        
        # Configure main frame grid weights
        main_frame.rowconfigure(3, weight=1)
    
    def update_audio_devices(self):
        """Update the audio device combobox with available devices"""
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            input_devices = []
            
            for i, device in enumerate(devices):
                if device['max_input_channels'] > 0:
                    device_name = f"{i}: {device['name']}"
                    input_devices.append(device_name)
            
            self.device_combo['values'] = input_devices
            if input_devices:
                # Set default device
                default_device = sd.query_devices(kind='input')
                default_name = f"{default_device['index']}: {default_device['name']}"
                if default_name in input_devices:
                    self.device_var.set(default_name)
                else:
                    self.device_var.set(input_devices[0])
                    
        except Exception as e:
            print(f"Error updating audio devices: {e}")
            self.device_combo['values'] = ["Default Device"]
            self.device_var.set("Default Device")
    
    def start_hotkey_recording(self):
        """Start recording a new hotkey combination"""
        self.record_hotkey_btn.configure(text="Recording...", state='disabled')
        self.hotkey_entry.configure(state='disabled')
        
        def on_hotkey_recorded(hotkey_str):
            self.hotkey_var.set(hotkey_str)
            self.record_hotkey_btn.configure(text="Record", state='normal')
            self.hotkey_entry.configure(state='normal')
        
        self.hotkey_recorder = HotkeyRecorder(on_hotkey_recorded)
        self.hotkey_recorder.start_recording()
        
        # Auto-stop after 10 seconds if no input
        def auto_stop():
            time.sleep(10)
            if self.hotkey_recorder and self.hotkey_recorder.recording:
                self.hotkey_recorder.stop_recording()
                self.record_hotkey_btn.configure(text="Record", state='normal')
                self.hotkey_entry.configure(state='normal')
        
        threading.Thread(target=auto_stop, daemon=True).start()
    
    def save_settings(self):
        """Save current settings to configuration"""
        try:
            # Update app config
            self.app.config['hotkey'] = self.hotkey_var.get()
            self.app.config['transcription']['engine'] = self.engine_var.get()
            
            # Extract device index from selection
            device_selection = self.device_var.get()
            if ':' in device_selection:
                device_index = int(device_selection.split(':')[0])
                self.app.config['audio_device_index'] = device_index
            
            # Save to file
            self.app.save_config()
            
            # Update hotkey registration
            self.app.update_hotkey()
            
            messagebox.showinfo("Settings", "Settings saved successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")
    
    def update_recent_transcriptions(self):
        """Update the recent transcriptions list"""
        try:
            recent_records = self.db.get_recent_transcriptions(3)
            
            self.recent_listbox.delete(0, tk.END)
            
            for record in recent_records:
                # Format: "timestamp - first 50 chars of text"
                timestamp = record.timestamp.split('T')[0] if 'T' in record.timestamp else record.timestamp
                preview_text = record.text[:50] + "..." if len(record.text) > 50 else record.text
                display_text = f"{timestamp} - {preview_text}"
                
                self.recent_listbox.insert(tk.END, display_text)
                
                # Store the full record for later retrieval
                self.recent_listbox.insert(tk.END, record.text)  # Hidden full text
                
        except Exception as e:
            print(f"Error updating recent transcriptions: {e}")
    
    def copy_selected_transcription(self, event=None):
        """Copy selected transcription to clipboard"""
        try:
            selection = self.recent_listbox.curselection()
            if selection:
                index = selection[0]
                # Get the actual transcription text
                recent_records = self.db.get_recent_transcriptions(3)
                if index < len(recent_records):
                    text = recent_records[index].text
                    pyperclip.copy(text)
                    self.update_status("Transcription copied to clipboard!")
                    
                    # Auto-hide window after copying
                    threading.Timer(1.5, self.hide_window).start()
                    
        except Exception as e:
            print(f"Error copying transcription: {e}")
    
    def show_full_history(self):
        """Show full transcription history in a new window"""
        history_window = tk.Toplevel(self.window)
        history_window.title("Transcription History")
        history_window.geometry("800x600")
        
        # Create treeview for history
        columns = ('Timestamp', 'Text Preview', 'Duration', 'Engine')
        tree = ttk.Treeview(history_window, columns=columns, show='headings')
        
        # Configure columns
        tree.heading('Timestamp', text='Timestamp')
        tree.heading('Text Preview', text='Text Preview')
        tree.heading('Duration', text='Duration (s)')
        tree.heading('Engine', text='Engine')
        
        tree.column('Timestamp', width=150)
        tree.column('Text Preview', width=400)
        tree.column('Duration', width=100)
        tree.column('Engine', width=100)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(history_window, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack widgets
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Load history data
        try:
            all_records = self.db.get_all_transcriptions(100)  # Last 100 records
            
            for record in all_records:
                timestamp = record.timestamp.split('T')[0] if 'T' in record.timestamp else record.timestamp
                preview = record.text[:50] + "..." if len(record.text) > 50 else record.text
                duration = f"{record.duration_seconds:.1f}"
                
                tree.insert('', tk.END, values=(timestamp, preview, duration, record.engine))
                
        except Exception as e:
            print(f"Error loading history: {e}")
        
        # Double-click to copy
        def copy_from_history(event):
            selection = tree.selection()
            if selection:
                item = tree.item(selection[0])
                # Find the corresponding record and copy full text
                timestamp = item['values'][0]
                try:
                    records = self.db.get_all_transcriptions(100)
                    for record in records:
                        record_date = record.timestamp.split('T')[0] if 'T' in record.timestamp else record.timestamp
                        if record_date == timestamp:
                            pyperclip.copy(record.text)
                            break
                except:
                    pass
        
        tree.bind('<Double-Button-1>', copy_from_history)
    
    def update_status(self, status: str):
        """Update the status label"""
        if self.window and self.status_label:
            self.status_label.configure(text=status)
    
    def show_window(self):
        """Show the GUI window"""
        if not self.window:
            self.create_window()
        
        self.window.deiconify()
        self.window.lift()
        self.window.focus_force()
        self.is_visible = True
        
        # Update recent transcriptions when showing
        self.update_recent_transcriptions()
    
    def hide_window(self):
        """Hide the GUI window"""
        if self.window:
            self.window.withdraw()
        self.is_visible = False
    
    def toggle_window(self):
        """Toggle window visibility"""
        if self.is_visible:
            self.hide_window()
        else:
            self.show_window()
    
    def start_mainloop(self):
        """Start the tkinter mainloop - simplified approach"""
        # With direct Tk() window, no special mainloop needed
        # The window will handle events automatically
        pass
    
    def cleanup(self):
        """Clean up GUI resources"""
        try:
            if self.window:
                self.window.quit()
                self.window.destroy()
            if self.root:
                self.root.quit()
                self.root.destroy()
        except tk.TclError:
            pass  # Window already destroyed
