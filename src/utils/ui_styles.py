"""
UI Styles for WhisperKey - IntelliJ IDEA Darcula Dark Theme

This file defines the color palette, fonts, and ttk styles for the application
to ensure a consistent and modern dark theme look following IntelliJ IDEA Darcula specifications.
"""

from tkinter import ttk
import tkinter as tk

class AppStyles:
    """
    Defines the IntelliJ IDEA Darcula Dark Theme styling for the WhisperKey application.
    """ 
    # IntelliJ IDEA Darcula Color Palette (strictly followed)
    BACKGROUND_COLOR = "#2B2B2B"        # Dark charcoal
    FOREGROUND_COLOR = "#BBBBBB"        # Soft white/gray
    PRIMARY_ACCENT = "#3C78FF"          # IntelliJ blue
    SECONDARY_ACCENT = "#4E5254"        # Mid-grey (hover states, selections)
    ERROR_HIGHLIGHT = "#CC7832"         # Darcula orange
    INPUT_BACKGROUND = "#3C3F41"        # Dark input fields
    BORDER_COLOR = "#555555"            # Subtle borders
    SELECTION_COLOR = "#4E5254"         # Selection highlight
    CARD_BACKGROUND = "#3C3F41"         # Cards and panels
    ALTERNATING_ROW = "#323232"         # Alternating table rows
    HOVER_COLOR = "#5684F5"             # Lighter hover state
    WHITE_TEXT = "#FFFFFF"              # Pure white text

    # Typography (strictly followed)
    FONT_FAMILY = "Segoe UI"            # Primary font (fallback to Roboto)
    FONT_FAMILY_FALLBACK = "Roboto"     # Fallback font
    FONT_SIZE_DEFAULT = 12              # Default font size
    FONT_SIZE_HEADER = 14               # Header font size (bold)
    
    # UI Element Specifications
    BUTTON_PADDING_V = 6                # Vertical padding for buttons
    BUTTON_PADDING_H = 12               # Horizontal padding for buttons
    PANEL_SPACING = 15                  # Spacing between panels
    BORDER_RADIUS = 4                   # Rounded corners where feasible

    @staticmethod
    def apply(window):
        """Apply IntelliJ IDEA Darcula Dark Theme styles to the application."""
        style = ttk.Style(window)
        
        # Use a theme that supports dark styling
        try:
            style.theme_use('clam')
        except:
            style.theme_use('default')

        # --- Root/General Configuration ---
        style.configure(".",
                        background=AppStyles.BACKGROUND_COLOR,
                        foreground=AppStyles.FOREGROUND_COLOR,
                        font=(AppStyles.FONT_FAMILY, AppStyles.FONT_SIZE_DEFAULT),
                        borderwidth=0,
                        relief="flat")

        # --- Window Background ---
        window.configure(bg=AppStyles.BACKGROUND_COLOR)

        # --- Frame Styling ---
        style.configure("TFrame", 
                        background=AppStyles.BACKGROUND_COLOR,
                        relief="flat",
                        borderwidth=0)

        # --- Label Styling ---
        style.configure("TLabel",
                        background=AppStyles.BACKGROUND_COLOR,
                        foreground=AppStyles.FOREGROUND_COLOR,
                        font=(AppStyles.FONT_FAMILY, AppStyles.FONT_SIZE_DEFAULT))

        # Header labels (bold, 14px)
        style.configure("Header.TLabel",
                        background=AppStyles.BACKGROUND_COLOR,
                        foreground=AppStyles.FOREGROUND_COLOR,
                        font=(AppStyles.FONT_FAMILY, AppStyles.FONT_SIZE_HEADER, "bold"))

        # Accent labels (IntelliJ blue)
        style.configure("Accent.TLabel",
                        background=AppStyles.BACKGROUND_COLOR,
                        foreground=AppStyles.PRIMARY_ACCENT,
                        font=(AppStyles.FONT_FAMILY, AppStyles.FONT_SIZE_DEFAULT))

        # Card title labels (IntelliJ blue, bold)
        style.configure("CardTitle.TLabel",
                        background=AppStyles.CARD_BACKGROUND,
                        foreground=AppStyles.PRIMARY_ACCENT,
                        font=(AppStyles.FONT_FAMILY, AppStyles.FONT_SIZE_HEADER, "bold"))

        # Card value labels (white, bold)
        style.configure("CardValue.TLabel",
                        background=AppStyles.CARD_BACKGROUND,
                        foreground=AppStyles.WHITE_TEXT,
                        font=(AppStyles.FONT_FAMILY, AppStyles.FONT_SIZE_HEADER, "bold"))

        # --- Button Styling (Flat rectangular, IntelliJ blue) ---
        style.configure("TButton",
                        background=AppStyles.PRIMARY_ACCENT,
                        foreground=AppStyles.WHITE_TEXT,
                        font=(AppStyles.FONT_FAMILY, AppStyles.FONT_SIZE_DEFAULT),
                        borderwidth=0,
                        relief="flat",
                        padding=(AppStyles.BUTTON_PADDING_H, AppStyles.BUTTON_PADDING_V))

        style.map("TButton",
                  background=[('active', AppStyles.HOVER_COLOR),
                             ('pressed', AppStyles.PRIMARY_ACCENT)])

        # Recording button (changes to red when recording)
        style.configure("Recording.TButton",
                        background=AppStyles.ERROR_HIGHLIGHT,
                        foreground=AppStyles.WHITE_TEXT,
                        font=(AppStyles.FONT_FAMILY, AppStyles.FONT_SIZE_DEFAULT),
                        borderwidth=0,
                        relief="flat",
                        padding=(AppStyles.BUTTON_PADDING_H, AppStyles.BUTTON_PADDING_V))

        # Toggle buttons (for format toggles)
        style.configure("Toggle.TButton",
                        background=AppStyles.CARD_BACKGROUND,
                        foreground=AppStyles.FOREGROUND_COLOR,
                        font=(AppStyles.FONT_FAMILY, AppStyles.FONT_SIZE_DEFAULT),
                        borderwidth=0,
                        relief="flat",
                        padding=(AppStyles.BUTTON_PADDING_H, AppStyles.BUTTON_PADDING_V))

        style.configure("ToggleSelected.TButton",
                        background=AppStyles.PRIMARY_ACCENT,
                        foreground=AppStyles.WHITE_TEXT,
                        font=(AppStyles.FONT_FAMILY, AppStyles.FONT_SIZE_DEFAULT),
                        borderwidth=0,
                        relief="flat",
                        padding=(AppStyles.BUTTON_PADDING_H, AppStyles.BUTTON_PADDING_V))

        # --- Entry/Input Field Styling ---
        style.configure("TEntry",
                        background=AppStyles.INPUT_BACKGROUND,
                        foreground=AppStyles.FOREGROUND_COLOR,
                        font=(AppStyles.FONT_FAMILY, AppStyles.FONT_SIZE_DEFAULT),
                        borderwidth=1,
                        relief="flat",
                        insertcolor=AppStyles.FOREGROUND_COLOR,
                        selectbackground=AppStyles.PRIMARY_ACCENT,
                        selectforeground=AppStyles.WHITE_TEXT)

        style.map("TEntry",
                  focuscolor=[('focus', AppStyles.PRIMARY_ACCENT)],
                  bordercolor=[('focus', AppStyles.PRIMARY_ACCENT)])

        # --- Combobox Styling ---
        style.configure("TCombobox",
                        background=AppStyles.INPUT_BACKGROUND,
                        foreground=AppStyles.FOREGROUND_COLOR,
                        font=(AppStyles.FONT_FAMILY, AppStyles.FONT_SIZE_DEFAULT),
                        borderwidth=1,
                        relief="flat",
                        arrowcolor=AppStyles.FOREGROUND_COLOR,
                        selectbackground=AppStyles.PRIMARY_ACCENT,
                        selectforeground=AppStyles.WHITE_TEXT)

        style.map("TCombobox",
                  focuscolor=[('focus', AppStyles.PRIMARY_ACCENT)],
                  bordercolor=[('focus', AppStyles.PRIMARY_ACCENT)],
                  arrowcolor=[('active', AppStyles.PRIMARY_ACCENT)])

        # --- Notebook (Tab) Styling ---
        style.configure("TNotebook",
                        background=AppStyles.BACKGROUND_COLOR,
                        borderwidth=0,
                        relief="flat")

        style.configure("TNotebook.Tab",
                        background=AppStyles.CARD_BACKGROUND,
                        foreground=AppStyles.FOREGROUND_COLOR,
                        font=(AppStyles.FONT_FAMILY, AppStyles.FONT_SIZE_DEFAULT),
                        borderwidth=0,
                        relief="flat",
                        padding=(AppStyles.BUTTON_PADDING_H, AppStyles.BUTTON_PADDING_V))

        style.map("TNotebook.Tab",
                  background=[('selected', AppStyles.BACKGROUND_COLOR),
                             ('active', AppStyles.SECONDARY_ACCENT)],
                  foreground=[('selected', AppStyles.WHITE_TEXT),
                             ('active', AppStyles.WHITE_TEXT)])

        # --- Treeview Styling (Tables) ---
        style.configure("Treeview",
                        background=AppStyles.BACKGROUND_COLOR,
                        foreground=AppStyles.FOREGROUND_COLOR,
                        font=(AppStyles.FONT_FAMILY, AppStyles.FONT_SIZE_DEFAULT),
                        borderwidth=0,
                        relief="flat",
                        rowheight=25)

        style.configure("Treeview.Heading",
                        background=AppStyles.CARD_BACKGROUND,
                        foreground=AppStyles.FOREGROUND_COLOR,
                        font=(AppStyles.FONT_FAMILY, AppStyles.FONT_SIZE_DEFAULT, "bold"),
                        borderwidth=1,
                        relief="flat")

        style.map("Treeview",
                  background=[('selected', AppStyles.PRIMARY_ACCENT)],
                  foreground=[('selected', AppStyles.WHITE_TEXT)])

        style.map("Treeview.Heading",
                  background=[('active', AppStyles.SECONDARY_ACCENT)])

        # --- Scrollbar Styling (Thin, minimalist) ---
        style.configure("TScrollbar",
                        background=AppStyles.CARD_BACKGROUND,
                        troughcolor=AppStyles.BACKGROUND_COLOR,
                        borderwidth=0,
                        relief="flat",
                        width=12)

        style.map("TScrollbar",
                  background=[('active', AppStyles.PRIMARY_ACCENT)],
                  troughcolor=[('active', AppStyles.BACKGROUND_COLOR)])

        # --- Listbox Styling (for overview recent transcriptions) ---
        # Note: Listbox styling is handled in the GUI code directly since it's not a ttk widget

        # --- Separator Styling ---
        style.configure("TSeparator",
                        background=AppStyles.BORDER_COLOR)

        # --- Progressbar Styling ---
        style.configure("TProgressbar",
                        background=AppStyles.PRIMARY_ACCENT,
                        troughcolor=AppStyles.CARD_BACKGROUND,
                        borderwidth=0,
                        relief="flat")

    @staticmethod
    def configure_listbox(listbox):
        """Configure a tkinter Listbox widget with Darcula theme."""
        listbox.configure(
            bg=AppStyles.CARD_BACKGROUND,
            fg=AppStyles.FOREGROUND_COLOR,
            font=(AppStyles.FONT_FAMILY, AppStyles.FONT_SIZE_DEFAULT),
            selectbackground=AppStyles.SELECTION_COLOR,
            selectforeground=AppStyles.WHITE_TEXT,
            borderwidth=0,
            relief="flat",
            highlightthickness=0,
            activestyle="none"
        )

    @staticmethod
    def configure_text_widget(text_widget):
        """Configure a tkinter Text widget with Darcula theme."""
        text_widget.configure(
            bg=AppStyles.CARD_BACKGROUND,
            fg=AppStyles.FOREGROUND_COLOR,
            font=(AppStyles.FONT_FAMILY, AppStyles.FONT_SIZE_DEFAULT),
            insertbackground=AppStyles.FOREGROUND_COLOR,
            selectbackground=AppStyles.PRIMARY_ACCENT,
            selectforeground=AppStyles.WHITE_TEXT,
            borderwidth=0,
            relief="flat",
            highlightthickness=0,
            wrap=tk.WORD
        )

    @staticmethod
    def create_card_frame(parent, **kwargs):
        """Create a card-style frame with Darcula theme."""
        frame = tk.Frame(parent, 
                        bg=AppStyles.CARD_BACKGROUND,
                        relief="flat",
                        borderwidth=0,
                        **kwargs)
        return frame

    @staticmethod
    def create_separator_line(parent, **kwargs):
        """Create a subtle separator line."""
        separator = tk.Frame(parent,
                           bg=AppStyles.BORDER_COLOR,
                           height=1,
                           **kwargs)
        return separator

    @staticmethod
    def apply_hover_effect(widget, enter_color=None, leave_color=None):
        """Apply hover effects to widgets."""
        if enter_color is None:
            enter_color = AppStyles.SECONDARY_ACCENT
        if leave_color is None:
            leave_color = AppStyles.CARD_BACKGROUND
            
        def on_enter(event):
            widget.configure(bg=enter_color)
            
        def on_leave(event):
            widget.configure(bg=leave_color)
            
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)
