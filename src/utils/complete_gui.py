"""
Complete WhisperKey GUI implementation with cost tracking and tabbed interface
Built using the working progressive test foundation
"""
import logging
import threading
import time
import tkinter as tk
from datetime import datetime, timedelta
from tkinter import ttk, messagebox
from typing import Callable

import pyperclip
from pynput import keyboard, mouse

from .billing import OpenAIBillingAPI
from .ui_styles import AppStyles
# Import WhisperKey components (all tested to work individually)
from .database import TranscriptionDatabase

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
    """Complete GUI with all WhisperKey functionality + cost tracking in tabbed interface"""

    def __init__(self, app_instance):
        logger.info("=== Initializing Complete WhisperKey GUI ===")

        self.app = app_instance
        self.db = TranscriptionDatabase()
        self.window = None
        self.is_visible = False

        # Add click debouncing to prevent spam clicking issues
        self.last_click_time = 0
        self.click_debounce_delay = 0.3  # 300ms debounce

        # Cost tracking
        self.billing = None
        if hasattr(app_instance, 'config'):
            import os
            api_key = os.getenv('OPENAI_API_KEY') or app_instance.config.get('transcription', {}).get('api_key', '')
            if api_key:
                self.billing = OpenAIBillingAPI(api_key, app_instance.config)
                logger.info("[OK] Billing module initialized")
            else:
                logger.warning("[WARN] No API key found for billing")

        # GUI components
        self.status_label = None
        self.notebook = None
        self.cost_labels = {}

        # Initialize GUI
        self.create_window()
        AppStyles.apply(self.window)
        logger.info("=== Complete WhisperKey GUI Initialized ===")

    def create_window(self):
        """Create the main GUI window using proven working approach"""
        logger.info("Creating main window...")

        try:
            # Use direct Tk() approach that worked in progressive test
            self.window = tk.Tk()
            self.window.title("WhisperKey")
            self.window.geometry("800x650")
            self.window.minsize(700, 500)

            # Configure modern style
            style = ttk.Style()
            style.theme_use('clam')

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

            # Create all widgets
            self.create_widgets()

            # Start cost tracking if enabled
            self.start_cost_tracking()

            # Initially hide window but keep it available for mainloop
            self.window.withdraw()
            self.is_visible = False

            # Set up window to handle mainloop properly
            self.window.protocol("WM_DELETE_WINDOW", self.on_window_close)

            logger.info("Main window created successfully")

        except Exception as e:
            logger.error(f"Error creating window: {e}", exc_info=True)
            raise

    def create_widgets(self):
        """Create all GUI widgets with tabbed interface"""
        logger.info("Creating GUI widgets...")

        try:
            # Main container
            main_frame = ttk.Frame(self.window, padding="10")
            main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

            # Configure grid weights
            self.window.columnconfigure(0, weight=1)
            self.window.rowconfigure(0, weight=1)
            main_frame.columnconfigure(0, weight=1)
            main_frame.rowconfigure(1, weight=1)

            # Header section
            self.create_header_section(main_frame, 0)

            # Tabbed interface
            self.notebook = ttk.Notebook(main_frame)
            self.notebook.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))

            # Create tabs
            self.create_overview_tab()
            self.create_settings_tab()
            self.create_transcriptions_tab()
            self.create_cost_tracking_tab()

            # Update initial data
            self.update_recent_transcriptions()
            self.update_status("Ready for transcription")
            self.update_cost_display()

            logger.info("All GUI widgets created successfully")

        except Exception as e:
            logger.error(f"Error creating widgets: {e}", exc_info=True)
            raise

    def create_header_section(self, parent, row):
        """Create header section with title and status"""
        header_frame = ttk.Frame(parent, padding=(10, 20))
        header_frame.grid(row=row, column=0, columnspan=2, sticky="ew")
        parent.grid_columnconfigure(0, weight=1)

        # Title
        title_label = ttk.Label(
            header_frame,
            text="WhisperKey",
            style="Header.TLabel"
        )
        title_label.pack(side="left", anchor="w")

        # Status Label
        self.status_label = ttk.Label(
            header_frame,
            text="Status: Idle",
            style="Status.TLabel",
            anchor="e"
        )
        self.status_label.pack(side="right", anchor="e")

        return row + 1

    def create_overview_tab(self):
        """Create overview tab with quick actions and status"""
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text="Overview")

        # Configure grid
        tab_frame.columnconfigure(0, weight=1)
        tab_frame.rowconfigure(2, weight=1)

        # Quick actions section
        actions_frame = ttk.LabelFrame(tab_frame, text="Quick Actions", padding="15")
        actions_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        actions_frame.columnconfigure(1, weight=1)

        # Regular recording button
        record_btn = ttk.Button(actions_frame, text="Start Recording",
                                command=self.manual_record, width=20)
        record_btn.grid(row=0, column=0, padx=(0, 10), pady=5)

        # Realtime transcription button
        self.realtime_btn = ttk.Button(actions_frame, text="Start Realtime",
                                       command=self.toggle_realtime, width=20)
        self.realtime_btn.grid(row=0, column=1, padx=(0, 10), pady=5)

        # Settings button
        settings_btn = ttk.Button(actions_frame, text="Settings",
                                  command=lambda: self.notebook.select(1), width=20)
        settings_btn.grid(row=0, column=2, pady=5)

        # Current hotkeys display
        hotkeys_frame = ttk.LabelFrame(tab_frame, text="Hotkeys", padding="15")
        hotkeys_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        # Get current hotkeys from config
        record_hotkey = self.app.config.get('hotkey', 'ctrl+alt+enter')
        realtime_hotkey = self.app.config.get('realtime_hotkey', 'ctrl+alt+shift+enter')

        ttk.Label(hotkeys_frame, text=f"Recording: {record_hotkey}",
                  font=("Segoe UI", 10)).grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Label(hotkeys_frame, text=f"Realtime: {realtime_hotkey}",
                  font=("Segoe UI", 10)).grid(row=1, column=0, sticky=tk.W, pady=2)

        # Recent transcriptions preview
        recent_frame = ttk.LabelFrame(tab_frame, text="Recent Transcriptions", padding="15")
        recent_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        recent_frame.columnconfigure(0, weight=1)
        recent_frame.rowconfigure(0, weight=1)

        # Create overview listbox
        self.overview_listbox = tk.Listbox(recent_frame, height=8, font=("Segoe UI", 10))
        scrollbar_overview = ttk.Scrollbar(recent_frame, orient="vertical", command=self.overview_listbox.yview)
        self.overview_listbox.configure(yscrollcommand=scrollbar_overview.set)

        self.overview_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar_overview.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # Bind double-click event
        self.overview_listbox.bind("<Double-Button-1>", self.copy_selected_transcription)

    def create_settings_tab(self):
        """Create settings configuration tab with improved styling."""
        settings_frame = ttk.Frame(self.notebook, padding="20")
        self.notebook.add(settings_frame, text='Settings')
        settings_frame.grid_columnconfigure(0, weight=1)

        # --- General Settings ---
        general_frame = ttk.LabelFrame(settings_frame, text="General", padding="15")
        general_frame.grid(row=0, column=0, padx=5, pady=10, sticky="ew")
        general_frame.grid_columnconfigure(1, weight=1)

        # --- Hotkey Settings ---
        hotkey_frame = ttk.LabelFrame(settings_frame, text="Hotkeys", padding="15")
        hotkey_frame.grid(row=1, column=0, padx=5, pady=10, sticky="ew")
        hotkey_frame.grid_columnconfigure(1, weight=1)

        ttk.Label(hotkey_frame, text="Record Hotkey:").grid(row=0, column=0, sticky="w", pady=5)
        self.hotkey_entry = ttk.Entry(hotkey_frame)
        self.hotkey_entry.insert(0, self.app.config.get('hotkey', ''))
        self.hotkey_entry.grid(row=0, column=1, padx=5, sticky="ew")
        self.record_hotkey_button = ttk.Button(hotkey_frame, text="Record", style="TButton", command=self.record_hotkey)
        self.record_hotkey_button.grid(row=0, column=2, padx=5)

        ttk.Label(hotkey_frame, text="Realtime Hotkey:").grid(row=1, column=0, sticky="w", pady=5)
        self.realtime_hotkey_entry = ttk.Entry(hotkey_frame)
        self.realtime_hotkey_entry.insert(0, self.app.config.get('realtime_hotkey', ''))
        self.realtime_hotkey_entry.grid(row=1, column=1, padx=5, sticky="ew")
        self.record_realtime_hotkey_button = ttk.Button(hotkey_frame, text="Record", style="TButton", command=self.record_realtime_hotkey)
        self.record_realtime_hotkey_button.grid(row=1, column=2, padx=5)

        # --- Audio Device Settings ---
        audio_frame = ttk.LabelFrame(settings_frame, text="Audio", padding="15")
        audio_frame.grid(row=2, column=0, padx=5, pady=10, sticky="ew")
        audio_frame.grid_columnconfigure(0, weight=1)

        ttk.Label(audio_frame, text="Input Device:").grid(row=0, column=0, sticky="w")

        self.audio_device_menu = ttk.Combobox(audio_frame)
        self.audio_device_menu.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.audio_device_menu.bind('<<ComboboxSelected>>', self.on_audio_device_select)
        self.refresh_audio_devices()


        # --- Transcription Settings ---
        transcription_frame = ttk.LabelFrame(settings_frame, text="Transcription Models", padding="15")
        transcription_frame.grid(row=3, column=0, padx=5, pady=10, sticky="ew")
        transcription_frame.grid_columnconfigure(1, weight=1)

        # Recorded Transcription Model
        ttk.Label(transcription_frame, text="Recorded Model:").grid(row=0, column=0, sticky="w", pady=5)
        self.recorded_model_entry = ttk.Entry(transcription_frame)
        self.recorded_model_entry.insert(0, self.app.config['transcription']['model'])
        self.recorded_model_entry.grid(row=0, column=1, padx=5, sticky="ew")

        # Real-time Transcription Model
        ttk.Label(transcription_frame, text="Real-time Model:").grid(row=1, column=0, sticky="w", pady=5)
        self.realtime_model_entry = ttk.Entry(transcription_frame)
        self.realtime_model_entry.insert(0, self.app.config.get('realtime', {}).get('model', ''))
        self.realtime_model_entry.grid(row=1, column=1, padx=5, sticky="ew")

        # --- Save Button ---
        button_frame = ttk.Frame(settings_frame)
        button_frame.grid(row=4, column=0, pady=20, sticky="e")
        save_button = ttk.Button(button_frame, text="Save Settings", style="TButton", command=self.save_settings)
        save_button.pack()

    def on_audio_device_select(self, event=None):
        """Handle selection of an audio device."""
        try:
            selection = self.audio_device_menu.get()
            # Extract device ID from string like "Microphone (ID: 2)"
            device_id_str = selection.split('ID: ')[-1].replace(')', '')
            if device_id_str.isdigit():
                device_id = int(device_id_str)
                self.app.config['audio_device_index'] = device_id
                self.update_status(f"Audio device set to ID: {device_id}")
                logger.info(f"Audio device selection changed to index {device_id}")
        except Exception as e:
            logger.error(f"Error handling audio device selection: {e}", exc_info=True)
            self.update_status("Error selecting audio device.")

    def create_transcriptions_tab(self):
        """Create transcriptions history tab with enhanced details."""
        tab_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(tab_frame, text="Transcriptions")

        # Configure grid
        tab_frame.columnconfigure(0, weight=1)
        tab_frame.rowconfigure(2, weight=1) # Make space for search

        # Controls frame
        controls_frame = ttk.Frame(tab_frame)
        controls_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        controls_frame.columnconfigure(1, weight=1)

        ttk.Label(controls_frame, text="Transcription History", style="Header.TLabel").grid(row=0, column=0, sticky="w")

        # Buttons
        button_frame = ttk.Frame(controls_frame)
        button_frame.grid(row=0, column=1, sticky="e")

        ttk.Button(button_frame, text="Copy Selected", style="TButton", command=self.copy_selected_transcription).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(button_frame, text="Refresh", style="TButton", command=self.update_recent_transcriptions).grid(row=0, column=1)

        # Search and Filter Frame
        search_frame = ttk.Frame(tab_frame)
        search_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        search_frame.columnconfigure(0, weight=1)

        self.search_entry = ttk.Entry(search_frame)
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.search_entry.bind("<Return>", lambda event: self.search_transcriptions())

        search_button = ttk.Button(search_frame, text="Search", style="TButton", command=self.search_transcriptions)
        search_button.grid(row=0, column=1)

        # Transcriptions list
        list_frame = ttk.Frame(tab_frame)
        list_frame.grid(row=2, column=0, sticky="nsew")
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        # Create treeview with new columns
        columns = ('timestamp', 'preview', 'tokens', 'cost', 'duration', 'engine')
        self.transcriptions_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)

        # Configure columns
        self.transcriptions_tree.heading('timestamp', text='Timestamp')
        self.transcriptions_tree.heading('preview', text='Text Preview')
        self.transcriptions_tree.heading('tokens', text='Tokens (In/Out)')
        self.transcriptions_tree.heading('cost', text='Est. Cost ($)')
        self.transcriptions_tree.heading('duration', text='Duration (s)')
        self.transcriptions_tree.heading('engine', text='Engine')

        self.transcriptions_tree.column('timestamp', width=150, anchor='w')
        self.transcriptions_tree.column('preview', width=300, anchor='w')
        self.transcriptions_tree.column('tokens', width=100, anchor='center')
        self.transcriptions_tree.column('cost', width=80, anchor='e')
        self.transcriptions_tree.column('duration', width=80, anchor='e')
        self.transcriptions_tree.column('engine', width=100, anchor='w')

        # Add scrollbar
        tree_scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.transcriptions_tree.yview)
        self.transcriptions_tree.configure(yscrollcommand=tree_scrollbar.set)

        # Pack widgets
        self.transcriptions_tree.grid(row=0, column=0, sticky="nsew")
        tree_scrollbar.grid(row=0, column=1, sticky="ns")

        # Bind double-click event
        self.transcriptions_tree.bind("<Double-Button-1>", self.copy_from_tree)

    def create_cost_tracking_tab(self):
        """Create comprehensive cost tracking tab"""
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text="Cost Tracking")

        # Configure grid
        tab_frame.columnconfigure(0, weight=1)
        tab_frame.rowconfigure(2, weight=1)

        # Header with refresh button
        header_frame = ttk.Frame(tab_frame, padding="10")
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))
        header_frame.columnconfigure(0, weight=1)

        title_frame = ttk.Frame(header_frame)
        title_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))
        title_frame.columnconfigure(0, weight=1)

        ttk.Label(title_frame, text="Cost Tracking & Usage Analytics",
                  font=("Segoe UI", 14, "bold")).grid(row=0, column=0, sticky=tk.W)

        refresh_btn = ttk.Button(title_frame, text="Refresh Data",
                                 command=self.refresh_costs)
        refresh_btn.grid(row=0, column=1, sticky=tk.E)

        # Summary cards
        summary_frame = ttk.Frame(tab_frame, padding="10")
        summary_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))

        # Create summary cards
        self.create_cost_summary_cards(summary_frame)

        # Detailed breakdown
        details_frame = ttk.LabelFrame(tab_frame, text="Detailed Usage Breakdown", padding="10")
        details_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=(0, 10))
        details_frame.columnconfigure(0, weight=1)
        details_frame.rowconfigure(0, weight=1)

        # Create notebook for time periods
        self.cost_notebook = ttk.Notebook(details_frame)
        self.cost_notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Create cost breakdown tabs
        self.create_daily_costs_tab()
        self.create_weekly_costs_tab()
        self.create_monthly_costs_tab()

    def create_cost_summary_cards(self, parent):
        """Create summary cards for cost overview"""
        # Configure grid for 3 cards
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)
        parent.columnconfigure(2, weight=1)

        # Today's usage
        today_frame = ttk.LabelFrame(parent, text="Today", padding="15")
        today_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))

        self.cost_labels['today_cost'] = ttk.Label(today_frame, text="$0.00",
                                                   font=("Segoe UI", 16, "bold"))
        self.cost_labels['today_cost'].grid(row=0, column=0)

        self.cost_labels['today_requests'] = ttk.Label(today_frame, text="0 requests",
                                                       font=("Segoe UI", 9))
        self.cost_labels['today_requests'].grid(row=1, column=0)

        # This month's usage
        month_frame = ttk.LabelFrame(parent, text="This Month", padding="15")
        month_frame.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)

        self.cost_labels['month_cost'] = ttk.Label(month_frame, text="$0.00",
                                                   font=("Segoe UI", 16, "bold"))
        self.cost_labels['month_cost'].grid(row=0, column=0)

        self.cost_labels['month_requests'] = ttk.Label(month_frame, text="0 requests",
                                                       font=("Segoe UI", 9))
        self.cost_labels['month_requests'].grid(row=1, column=0)

        # Total usage
        total_frame = ttk.LabelFrame(parent, text="All Time", padding="15")
        total_frame.grid(row=0, column=2, sticky=(tk.W, tk.E), padx=(5, 0))

        self.cost_labels['total_cost'] = ttk.Label(total_frame, text="$0.00",
                                                   font=("Segoe UI", 16, "bold"))
        self.cost_labels['total_cost'].grid(row=0, column=0)

        self.cost_labels['total_requests'] = ttk.Label(total_frame, text="0 requests",
                                                       font=("Segoe UI", 9))
        self.cost_labels['total_requests'].grid(row=1, column=0)

    def create_daily_costs_tab(self):
        """Create daily cost breakdown tab"""
        tab_frame = ttk.Frame(self.cost_notebook)
        self.cost_notebook.add(tab_frame, text="Daily")

        # Configure grid
        tab_frame.columnconfigure(0, weight=1)
        tab_frame.rowconfigure(0, weight=1)

        # Create treeview for daily costs
        columns = ('Date', 'Cost (USD)', 'Details', 'Last Updated')
        self.daily_tree = ttk.Treeview(tab_frame, columns=columns, show='headings')

        # Configure columns
        self.daily_tree.heading('Date', text='Date')
        self.daily_tree.heading('Cost (USD)', text='Cost (USD)')
        self.daily_tree.heading('Details', text='Usage Details')
        self.daily_tree.heading('Last Updated', text='Last Updated')

        self.daily_tree.column('Date', width=100)
        self.daily_tree.column('Cost (USD)', width=100)
        self.daily_tree.column('Details', width=300)
        self.daily_tree.column('Last Updated', width=150)

        # Add scrollbar
        daily_scrollbar = ttk.Scrollbar(tab_frame, orient="vertical", command=self.daily_tree.yview)
        self.daily_tree.configure(yscrollcommand=daily_scrollbar.set)

        # Pack widgets
        self.daily_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        daily_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # Bind double-click for detailed view
        self.daily_tree.bind("<Double-Button-1>", self.show_daily_details)

    def create_weekly_costs_tab(self):
        """Create weekly cost summary tab"""
        tab_frame = ttk.Frame(self.cost_notebook)
        self.cost_notebook.add(tab_frame, text="Weekly")

        # Configure grid
        tab_frame.columnconfigure(0, weight=1)
        tab_frame.rowconfigure(0, weight=1)

        # Create treeview for weekly costs
        columns = ('Week', 'Total Cost', 'Avg Daily', 'Days Active')
        self.weekly_tree = ttk.Treeview(tab_frame, columns=columns, show='headings')

        # Configure columns
        self.weekly_tree.heading('Week', text='Week of')
        self.weekly_tree.heading('Total Cost', text='Total Cost (USD)')
        self.weekly_tree.heading('Avg Daily', text='Avg Daily (USD)')
        self.weekly_tree.heading('Days Active', text='Days Active')

        self.weekly_tree.column('Week', width=120)
        self.weekly_tree.column('Total Cost', width=120)
        self.weekly_tree.column('Avg Daily', width=120)
        self.weekly_tree.column('Days Active', width=100)

        # Add scrollbar
        weekly_scrollbar = ttk.Scrollbar(tab_frame, orient="vertical", command=self.weekly_tree.yview)
        self.weekly_tree.configure(yscrollcommand=weekly_scrollbar.set)

        # Pack widgets
        self.weekly_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        weekly_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

    def create_monthly_costs_tab(self):
        """Create monthly cost summary tab"""
        tab_frame = ttk.Frame(self.cost_notebook)
        self.cost_notebook.add(tab_frame, text="Monthly")

        # Configure grid
        tab_frame.columnconfigure(0, weight=1)
        tab_frame.rowconfigure(0, weight=1)

        # Create treeview for monthly costs
        columns = ('Month', 'Total Cost', 'Days Active', 'Avg Daily', 'Trend')
        self.monthly_tree = ttk.Treeview(tab_frame, columns=columns, show='headings')

        # Configure columns
        self.monthly_tree.heading('Month', text='Month')
        self.monthly_tree.heading('Total Cost', text='Total Cost (USD)')
        self.monthly_tree.heading('Days Active', text='Days Active')
        self.monthly_tree.heading('Avg Daily', text='Avg Daily (USD)')
        self.monthly_tree.heading('Trend', text='Trend')

        self.monthly_tree.column('Month', width=100)
        self.monthly_tree.column('Total Cost', width=120)
        self.monthly_tree.column('Days Active', width=100)
        self.monthly_tree.column('Avg Daily', width=120)
        self.monthly_tree.column('Trend', width=80)

        # Add scrollbar
        monthly_scrollbar = ttk.Scrollbar(tab_frame, orient="vertical", command=self.monthly_tree.yview)
        self.monthly_tree.configure(yscrollcommand=monthly_scrollbar.set)

        # Pack widgets
        self.monthly_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        monthly_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

    # Event handler methods
    def manual_record(self):
        """Manually trigger recording"""
        self.app.toggle_recording()

    def toggle_realtime(self):
        """Toggle realtime transcription"""
        if not self.app.realtime_transcriber:
            messagebox.showwarning("Not Available",
                                   "Realtime transcription is not available. Check your configuration.")
            return

        if not self.app.is_realtime_active:
            # Start realtime
            self.app.start_realtime_transcription()
            self.realtime_btn.configure(text="Stop Realtime")
        else:
            # Stop realtime
            self.app.stop_realtime_transcription()
            self.realtime_btn.configure(text="Start Realtime")

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

                if self.cost_labels['month_cost']:
                    self.cost_labels['month_cost'].configure(text=f"${monthly_spend:.2f}")
                    logger.debug(f"Cost display updated: ${monthly_spend:.2f}")

            except Exception as e:
                logger.error(f"Error updating cost display: {e}")
                if self.cost_labels['month_cost']:
                    self.cost_labels['month_cost'].configure(text="Cost data unavailable (will retry)")

        # Ensure GUI operations run on main thread
        if self.window and hasattr(self.window, 'after'):
            self.window.after(0, _update_cost_display_main_thread)
        else:
            _update_cost_display_main_thread()

    def refresh_costs(self):
        """Manual cost refresh triggered by user"""
        if not self.billing or not self.billing.is_cost_tracking_enabled():
            self.update_status("[WARN] Cost tracking is disabled in configuration")
            return

        def refresh_callback(success):
            if success:
                self.update_cost_display()
                self.update_status("[OK] Cost data refreshed successfully!")
            else:
                self.update_status("[ERROR] Failed to refresh cost data. Check your API key and connection.")

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
            ttk.Label(main_frame, text="Cost Breakdown", font=("Segoe UI", 14, "bold")).grid(row=0, column=0,
                                                                                           pady=(0, 20))

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
            # Update status with instructions
            self.update_status("Hotkey Recording: Press and hold your desired key combination (including mouse buttons)")

            # Update button text to show recording state
            self.record_hotkey_button.configure(text="Recording...", state='disabled')

            def on_hotkey_recorded(hotkey_str):
                """Callback when hotkey is recorded"""
                try:
                    if hotkey_str:
                        # Clear the entry and insert the new hotkey
                        self.hotkey_entry.delete(0, tk.END)
                        self.hotkey_entry.insert(0, hotkey_str)
                        self.update_status(f"[OK] Hotkey recorded: {hotkey_str} - Don't forget to save settings!")
                    else:
                        self.update_status("[WARN] Hotkey recording cancelled - No hotkey was recorded.")

                    # Reset button
                    self.record_hotkey_button.configure(text="Record", state='normal')

                except Exception as e:
                    logger.error(f"Error in hotkey callback: {e}")
                    self.record_hotkey_button.configure(text="Record", state='normal')

            # Start recording with auto-stop timer
            self.hotkey_recorder = HotkeyRecorder(on_hotkey_recorded)
            self.hotkey_recorder.start_recording()

            # Auto-stop after 10 seconds if no input
            def auto_stop():
                if self.hotkey_recorder and self.hotkey_recorder.recording:
                    self.hotkey_recorder.stop_recording()
                    self.update_status("Hotkey recording timed out")
                    self.record_hotkey_button.configure(text="Record", state='normal')

            threading.Timer(10.0, auto_stop).start()

        except Exception as e:
            logger.error(f"Error starting hotkey recording: {e}")
            messagebox.showerror("Error", f"Failed to start hotkey recording: {e}")

    def record_realtime_hotkey(self):
        """Record a new realtime hotkey combination"""
        try:
            # Update status with instructions
            self.update_status("Realtime Hotkey Recording: Press and hold your desired key combination (including mouse buttons)")

            # Update button text to show recording state
            self.record_realtime_hotkey_button.configure(text="Recording...", state='disabled')

            def on_hotkey_recorded(hotkey_str):
                """Callback when hotkey is recorded"""
                try:
                    if hotkey_str:
                        # Clear the entry and insert the new hotkey
                        self.realtime_hotkey_entry.delete(0, tk.END)
                        self.realtime_hotkey_entry.insert(0, hotkey_str)
                        self.update_status(f"[OK] Realtime hotkey recorded: {hotkey_str} - Don't forget to save settings!")
                    else:
                        self.update_status("[WARN] Hotkey recording cancelled - No hotkey was recorded.")

                    # Reset button
                    self.record_realtime_hotkey_button.configure(text="Record", state='normal')

                except Exception as e:
                    logger.error(f"Error in realtime hotkey callback: {e}")
                    self.record_realtime_hotkey_button.configure(text="Record", state='normal')

            # Start recording with auto-stop timer
            self.hotkey_recorder = HotkeyRecorder(on_hotkey_recorded)
            self.hotkey_recorder.start_recording()

            # Auto-stop after 10 seconds if no input
            def auto_stop():
                if self.hotkey_recorder and self.hotkey_recorder.recording:
                    self.hotkey_recorder.stop_recording()
                    self.update_status("Realtime hotkey recording timed out")
                    self.record_realtime_hotkey_button.configure(text="Record", state='normal')

            threading.Timer(10.0, auto_stop).start()

        except Exception as e:
            logger.error(f"Error starting realtime hotkey recording: {e}")
            messagebox.showerror("Error", f"Failed to start realtime hotkey recording: {e}")

    def refresh_audio_devices(self):
        """Refresh the list of available audio devices."""
        logger.info("Refreshing audio devices...")
        try:
            devices = self.app.recorder.get_audio_devices()
            device_names = [f"{d['name']} (ID: {d['index']})" for d in devices]
            self.audio_device_menu['values'] = device_names

            current_device_index = self.app.config.get('audio_device_index')
            for i, device in enumerate(devices):
                if device['index'] == current_device_index:
                    self.audio_device_menu.current(i)
                    break
            logger.info(f"Found {len(devices)} audio devices.")
        except Exception as e:
            logger.error(f"Error refreshing audio devices: {e}", exc_info=True)
            self.update_status("Error: Could not refresh audio devices.")

    def save_settings(self):
        """Save current settings to configuration"""
        try:
            # Update config with current values from the entry fields
            self.app.config['hotkey'] = self.hotkey_entry.get()
            self.app.config['realtime_hotkey'] = self.realtime_hotkey_entry.get()

            # Audio device is now saved on select, so we just save models here
            self.app.config['transcription']['model'] = self.recorded_model_entry.get()
            self.app.config.setdefault('realtime', {})['model'] = self.realtime_model_entry.get()

            # Save the entire config to file
            self.app.save_config()

            # Update hotkey registration after saving
            if hasattr(self.app, 'setup_hotkey'):
                self.app.setup_hotkey()
            else:
                logger.warning("App doesn't have setup_hotkey method")

            self.update_status("[OK] Settings saved successfully!")
            logger.info("Settings saved")

        except Exception as e:
            logger.error(f"Error saving settings: {e}", exc_info=True)
            self.update_status(f"[ERROR] Failed to save settings: {e}")

    def update_hotkey(self):
        """Update hotkey registration after config change - fixed method"""
        try:
            if hasattr(self.app, 'setup_hotkey'):
                self.app.setup_hotkey()
                logger.info("Hotkeys updated successfully")
            else:
                logger.warning("App doesn't have setup_hotkey method")
        except Exception as e:
            logger.error(f"Error updating hotkeys: {e}")

    def get_daily_cost(self, date_str):
        """Get cost for a specific date"""
        if not self.billing:
            return 0.0
        try:
            costs = self.billing.get_cost_breakdown(90)
            for cost in costs:
                if cost.date == date_str:
                    return cost.cost_usd
            return 0.0
        except:
            return 0.0

    def update_recent_transcriptions(self):
        """Update the recent transcriptions in both overview tab and transcriptions tab"""
        try:
            logger.info("Updating recent transcriptions...")

            # Clear existing items in overview listbox
            if hasattr(self, 'overview_listbox') and self.overview_listbox:
                self.overview_listbox.delete(0, tk.END)

                # Get recent transcription records
                records = self.db.get_recent_transcriptions(10)
                logger.info(f"Retrieved {len(records)} recent transcription records for overview")

                # Add to overview listbox
                for record in records:
                    try:
                        date = record.timestamp.split('T')[0] if 'T' in record.timestamp else record.timestamp
                        preview = record.text[:50] + "..." if len(record.text) > 50 else record.text
                        self.overview_listbox.insert(tk.END, f"{date}: {preview}")
                    except Exception as e:
                        logger.error(f"Error processing overview record: {e}")

            # Update the full transcriptions tree
            self.update_transcriptions_tree()

            logger.info("Recent transcriptions updated successfully")

        except Exception as e:
            logger.error(f"Error updating recent transcriptions: {e}", exc_info=True)

    def copy_selected_transcription(self, event=None):
        """Copy selected transcription from overview listbox"""
        try:
            # Get selected item
            selected_idx = self.overview_listbox.curselection()
            if not selected_idx:
                self.update_status("[WARN] Please select a transcription to copy")
                return

            selected_text = self.overview_listbox.get(selected_idx)

            # Extract date from selected text (format: "YYYY-MM-DD: text...")
            if ": " in selected_text:
                date_str = selected_text.split(": ")[0]

                # Find matching record in database
                records = self.db.get_recent_transcriptions(50)
                for record in records:
                    record_date = record.timestamp.split('T')[0] if 'T' in record.timestamp else record.timestamp
                    if record_date == date_str:
                        # Copy full text to clipboard
                        pyperclip.copy(record.text)
                        self.update_status("[OK] Transcription copied to clipboard!")
                        return

            # Fallback: copy the selected text as is
            pyperclip.copy(selected_text)
            self.update_status("[OK] Text copied to clipboard")

        except Exception as e:
            logger.error(f"Error copying selected transcription: {e}")
            self.update_status("[ERROR] Error copying transcription")

    def start_cost_tracking(self):
        """Start cost tracking background tasks if enabled"""
        try:
            if not self.billing or not self.billing.is_cost_tracking_enabled():
                logger.info("Cost tracking is not enabled, skipping background tasks")
                return
                
            logger.info("Starting cost tracking background tasks")
            
            # Initial update of cost data
            self.update_cost_tracking_data()
            
            # Set up periodic refresh if auto-sync is enabled
            if hasattr(self.app, 'config') and self.app.config.get('cost_tracking', {}).get('auto_sync', True):
                def periodic_refresh():
                    if self.window:  # Only continue if window still exists
                        try:
                            logger.info("Running periodic cost data refresh")
                            self.billing.manual_refresh(lambda success: 
                                logger.info(f"Periodic cost refresh {'succeeded' if success else 'failed'}"))
                            self.update_cost_tracking_data()
                            
                            # Schedule next refresh (every hour)
                            self.window.after(3600000, periodic_refresh)  # 3600000 ms = 1 hour
                        except Exception as e:
                            logger.error(f"Error in periodic cost refresh: {e}")
                
                # Start first refresh after 5 minutes (to avoid startup delays)
                self.window.after(300000, periodic_refresh)  # 300000 ms = 5 minutes
                logger.info("Scheduled periodic cost data refresh")
            
            logger.info("Cost tracking background tasks started")
            
        except Exception as e:
            logger.error(f"Error starting cost tracking: {e}")

    def update_cost_tracking_data(self):
        """Update all cost tracking displays with detailed logging"""
        if not self.billing or not self.billing.is_cost_tracking_enabled():
            logger.info("Cost tracking not enabled, skipping data update")
            return

        def _update_cost_tracking_main_thread():
            try:
                now = datetime.now()
                logger.info(f"Updating cost tracking data for {now.strftime('%Y-%m-%d')}")

                # Update summary cards with detailed logging
                today_cost = 0.0
                month_cost = 0.0
                total_cost = 0.0

                if hasattr(self.billing, 'get_daily_cost'):
                    today_cost = self.billing.get_daily_cost(now.strftime('%Y-%m-%d'))
                    logger.info(f"Today's cost: ${today_cost:.4f}")

                if hasattr(self.billing, 'get_monthly_spend'):
                    month_cost = self.billing.get_monthly_spend(now.year, now.month)
                    logger.info(f"Monthly cost: ${month_cost:.4f}")

                # Get total cost from all records
                all_costs = []
                if hasattr(self.billing, 'get_cost_breakdown'):
                    all_costs = self.billing.get_cost_breakdown(365)  # Last year
                    total_cost = sum(cost.cost_usd for cost in all_costs)
                    logger.info(f"Total cost from {len(all_costs)} records: ${total_cost:.4f}")

                # Count transcriptions for today and month with detailed logging
                all_transcriptions = self.db.get_all_transcriptions(1000)
                logger.info(f"Found {len(all_transcriptions)} total transcriptions in database")

                today_transcriptions = len([r for r in all_transcriptions
                                            if r.timestamp.startswith(now.strftime('%Y-%m-%d'))])
                month_transcriptions = len([r for r in all_transcriptions
                                            if r.timestamp.startswith(now.strftime('%Y-%m'))])
                total_transcriptions = len(all_transcriptions)

                logger.info(
                    f"Transcription counts - Today: {today_transcriptions}, Month: {month_transcriptions}, Total: {total_transcriptions}")

                # Update labels with error checking
                if 'today_cost' in self.cost_labels and self.cost_labels['today_cost']:
                    self.cost_labels['today_cost'].configure(text=f"${today_cost:.2f}" if today_cost is not None else "$0.00")
                    self.cost_labels['today_requests'].configure(text=f"{today_transcriptions} requests")
                    logger.debug("Updated today's cost labels")

                if 'month_cost' in self.cost_labels and self.cost_labels['month_cost']:
                    self.cost_labels['month_cost'].configure(text=f"${month_cost:.2f}" if month_cost is not None else "$0.00")
                    self.cost_labels['month_requests'].configure(text=f"{month_transcriptions} requests")
                    logger.debug("Updated monthly cost labels")

                if 'total_cost' in self.cost_labels and self.cost_labels['total_cost']:
                    self.cost_labels['total_cost'].configure(text=f"${total_cost:.2f}" if total_cost is not None else "$0.00")
                    self.cost_labels['total_requests'].configure(text=f"{total_transcriptions} requests")
                    logger.debug("Updated total cost labels")

                # Update detailed trees
                self.update_daily_costs_tree()
                self.update_weekly_costs_tree()
                self.update_monthly_costs_tree()
                self.update_transcriptions_tree()

                logger.info("Cost tracking data update completed")

            except Exception as e:
                logger.error(f"Error updating cost tracking data: {e}", exc_info=True)

        # Ensure GUI operations run on main thread
        if self.window and hasattr(self.window, 'after'):
            self.window.after(0, _update_cost_tracking_main_thread)
        else:
            _update_cost_tracking_main_thread()

    def search_transcriptions(self):
        """Search and filter transcriptions based on user input."""
        query = self.search_entry.get()
        if not query:
            self.update_transcriptions_tree()
            return

        try:
            results = self.db.search_transcriptions(query)
            self.update_transcriptions_tree(records=results)
            self.update_status(f"Found {len(results)} matching transcriptions.")
        except Exception as e:
            logger.error(f"Error during transcription search: {e}")
            self.update_status("Error during search.")

    def update_transcriptions_tree(self, records=None):
        """Update the transcriptions tree view with token and cost data."""
        try:
            logger.info("Updating transcriptions tree...")

            # Clear existing items
            if hasattr(self, 'transcriptions_tree') and self.transcriptions_tree:
                for item in self.transcriptions_tree.get_children():
                    self.transcriptions_tree.delete(item)

                # Get all transcriptions if no specific records are provided
                if records is None:
                    records = self.db.get_all_transcriptions(100)
                logger.info(f"Retrieved {len(records)} records for transcriptions tree")

                # Add to treeview
                for record in records:
                    try:
                        # Format timestamp
                        try:
                            ts = datetime.fromisoformat(record.timestamp).strftime('%Y-%m-%d %H:%M:%S')
                        except (ValueError, TypeError):
                            ts = record.timestamp

                        preview = record.text[:70] + "..." if len(record.text) > 70 else record.text
                        tokens = f"{record.input_tokens}/{record.output_tokens}"
                        cost = f"{record.cost:.6f}"
                        duration = f"{record.duration_seconds:.2f}"

                        self.transcriptions_tree.insert('', tk.END, values=(
                            ts,
                            preview,
                            tokens,
                            cost,
                            duration,
                            record.engine
                        ))
                    except Exception as e:
                        logger.error(f"Error processing tree record: {e}")

            logger.info("Transcriptions tree updated successfully")

        except Exception as e:
            logger.error(f"Error updating transcriptions tree: {e}", exc_info=True)

    # Window management methods
    def show_window(self):
        """Show the GUI window with debounced click handling"""
        current_time = time.time()

        # Check if we're within the debounce period
        if current_time - self.last_click_time < self.click_debounce_delay:
            logger.debug("Click ignored due to debouncing")
            return

        self.last_click_time = current_time

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
            self.update_cost_tracking_data()  # This will populate all the data

            logger.info("GUI window shown successfully")

        except Exception as e:
            logger.error(f"Error showing window: {e}")

    def hide_window(self):
        """Hide the GUI window with debounced click handling"""
        current_time = time.time()

        # Check if we're within the debounce period
        if current_time - self.last_click_time < self.click_debounce_delay:
            logger.debug("Hide click ignored due to debouncing")
            return

        self.last_click_time = current_time

        logger.info("Hiding GUI window")

        try:
            if self.window:
                self.window.withdraw()
            self.is_visible = False

        except Exception as e:
            logger.error(f"Error hiding window: {e}")

    def toggle_window(self):
        """Toggle window visibility with debounced click handling"""
        current_time = time.time()

        # Check if we're within the debounce period
        if current_time - self.last_click_time < self.click_debounce_delay:
            logger.debug("Toggle ignored due to debouncing")
            return

        self.last_click_time = current_time

        if self.is_visible:
            self.hide_window()
        else:
            self.show_window()

    def on_window_close(self):
        """Handle window close button - minimize to tray instead of exit"""
        logger.info("Window close requested - minimizing to tray")
        self.hide_window()
        self.update_status("WhisperKey minimized to system tray. Right-click tray icon to show window.")
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

    def copy_from_tree(self, event=None):
        """Copy selected transcription from tree view"""
        try:
            selection = self.transcriptions_tree.selection()
            if not selection:
                self.update_status("[WARN] Please select a transcription to copy")
                return

            item = self.transcriptions_tree.item(selection[0])
            date = item['values'][0]

            # Find the corresponding record and copy full text
            all_records = self.db.get_all_transcriptions(100)
            for record in all_records:
                record_date = record.timestamp.split('T')[0] if 'T' in record.timestamp else record.timestamp
                if record_date == date:
                    pyperclip.copy(record.text)
                    self.update_status("[OK] Transcription copied to clipboard!")
                    break

        except Exception as e:
            logger.error(f"Error copying from tree: {e}")

    def show_daily_details(self, event=None):
        """Show detailed breakdown for a selected day"""
        try:
            selection = self.daily_tree.selection()
            if not selection:
                return

            item = self.daily_tree.item(selection[0])
            date = item['values'][0]

            # Get detailed cost data for this date
            costs = self.billing.get_cost_breakdown(90) if self.billing else []

            for cost in costs:
                if cost.date == date:
                    # Parse the raw JSON for details
                    import json
                    try:
                        raw_data = json.loads(cost.raw_json)
                        line_items = raw_data.get('line_items', [])

                        # Create detail window
                        detail_window = tk.Toplevel(self.window)
                        detail_window.title(f"Cost Details - {date}")
                        detail_window.geometry("500x400")
                        detail_window.transient(self.window)

                        # Main frame
                        main_frame = ttk.Frame(detail_window, padding="20")
                        main_frame.pack(fill="both", expand=True)

                        # Title
                        ttk.Label(main_frame, text=f"Cost Details for {date}",
                                  font=("Segoe UI", 14, "bold")).pack(pady=(0, 20))

                        # Create treeview for line items
                        columns = ('Service', 'Cost (USD)')
                        tree = ttk.Treeview(main_frame, columns=columns, show='headings', height=10)

                        tree.heading('Service', text='Service/Line Item')
                        tree.heading('Cost (USD)', text='Cost (USD)')

                        tree.column('Service', width=300)
                        tree.column('Cost (USD)', width=150)

                        # Add scrollbar
                        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=tree.yview)
                        tree.configure(yscrollcommand=scrollbar.set)

                        # Pack widgets
                        tree.pack(side="left", fill="both", expand=True)
                        scrollbar.pack(side="right", fill="y")

                        main_frame.columnconfigure(0, weight=1)
                        main_frame.rowconfigure(0, weight=1)

                        # Populate line items
                        total = 0.0
                        for item in line_items:
                            service = item.get('line_item', 'Unknown')
                            cost_val = item.get('cost', 0.0)
                            tree.insert('', tk.END, values=(service, f"${cost_val:.4f}"))
                            total += cost_val

                        # Total label
                        ttk.Label(main_frame, text=f"Total: ${total:.2f}",
                                  font=("Segoe UI", 12, "bold")).pack(pady=(10, 0))

                    except Exception as e:
                        logger.error(f"Error parsing cost details: {e}")
                        messagebox.showerror("Error", f"Failed to parse cost details: {e}")
                    break

        except Exception as e:
            logger.error(f"Error showing daily details: {e}")

    def update_daily_costs_tree(self):
        """Update the daily costs tree view"""
        try:
            # Clear existing items
            for item in self.daily_tree.get_children():
                self.daily_tree.delete(item)

            if not self.billing:
                return

            # Get cost data
            costs = self.billing.get_cost_breakdown(30)

            for cost in costs:
                # Parse raw data for details
                try:
                    import json
                    raw_data = json.loads(cost.raw_json)
                    line_items = raw_data.get('line_items', [])
                    details = f"{len(line_items)} services used"
                except:
                    details = "Details available"

                last_updated = cost.last_updated.split('T')[0] if 'T' in cost.last_updated else cost.last_updated

                self.daily_tree.insert('', tk.END, values=(
                    cost.date,
                    f"${cost.cost_usd:.4f}",
                    details,
                    last_updated
                ))

        except Exception as e:
            logger.error(f"Error updating daily costs tree: {e}")

    def update_weekly_costs_tree(self):
        """Update the weekly costs tree view"""
        try:
            # Clear existing items
            for item in self.weekly_tree.get_children():
                self.weekly_tree.delete(item)

            if not self.billing:
                return

            # Get cost data and group by week
            costs = self.billing.get_cost_breakdown(90)
            weekly_data = {}

            for cost in costs:
                # Get week start date (Monday)
                date_obj = datetime.strptime(cost.date, '%Y-%m-%d')
                week_start = date_obj - timedelta(days=date_obj.weekday())
                week_key = week_start.strftime('%Y-%m-%d')

                if week_key not in weekly_data:
                    weekly_data[week_key] = {'total': 0.0, 'days': 0}

                weekly_data[week_key]['total'] += cost.cost_usd
                weekly_data[week_key]['days'] += 1

            # Add to tree
            for week_start, data in sorted(weekly_data.items(), reverse=True):
                avg_daily = data['total'] / data['days'] if data['days'] > 0 else 0

                self.weekly_tree.insert('', tk.END, values=(
                    week_start,
                    f"${data['total']:.2f}",
                    f"${avg_daily:.2f}",
                    data['days']
                ))

        except Exception as e:
            logger.error(f"Error updating weekly costs tree: {e}")

    def update_monthly_costs_tree(self):
        """Update the monthly costs tree view"""
        try:
            # Clear existing items
            for item in self.monthly_tree.get_children():
                self.monthly_tree.delete(item)

            if not self.billing:
                return

            # Get cost data and group by month
            costs = self.billing.get_cost_breakdown(365)
            monthly_data = {}

            for cost in costs:
                month_key = cost.date[:7]  # YYYY-MM

                if month_key not in monthly_data:
                    monthly_data[month_key] = {'total': 0.0, 'days': 0}

                monthly_data[month_key]['total'] += cost.cost_usd
                monthly_data[month_key]['days'] += 1

            # Calculate trends
            sorted_months = sorted(monthly_data.keys())

            for i, (month, data) in enumerate(sorted(monthly_data.items(), reverse=True)):
                avg_daily = data['total'] / data['days'] if data['days'] > 0 else 0

                # Calculate trend
                trend = "→"
                if i < len(sorted_months) - 1:
                    prev_month = sorted_months[
                        sorted_months.index(month) - 1] if month in sorted_months and sorted_months.index(
                        month) > 0 else None
                    if prev_month and prev_month in monthly_data:
                        prev_total = monthly_data[prev_month]['total']
                        if data['total'] > prev_total * 1.1:
                            trend = "↗"
                        elif data['total'] < prev_total * 0.9:
                            trend = "↘"

                self.monthly_tree.insert('', tk.END, values=(
                    month,
                    f"${data['total']:.2f}",
                    data['days'],
                    f"${avg_daily:.2f}",
                    trend
                ))

        except Exception as e:
            logger.error(f"Error updating monthly costs tree: {e}")

    # Additional helper methods for missing references
    @property
    def recent_listbox(self):
        """Get the current active listbox (overview or transcriptions)"""
        return getattr(self, 'overview_listbox', None)
