"""
UI Styles for WhisperKey

This file defines the color palette, fonts, and ttk styles for the application
to ensure a consistent and modern look.
"""

from tkinter import ttk

class AppStyles:
    """
    Defines the styling for the WhisperKey application.
    """ 
    # Color Palette (Modern, Sleek)
    PRIMARY_COLOR = "#2C3E50"  # Dark Slate Blue
    SECONDARY_COLOR = "#34495E"  # Wet Asphalt
    BACKGROUND_COLOR = "#ECF0F1"  # Light Gray
    TEXT_COLOR = "#FFFFFF"  # White
    ACCENT_COLOR = "#3498DB"  # Peter River Blue
    SUCCESS_COLOR = "#2ECC71"  # Emerald Green
    WARNING_COLOR = "#F1C40F"  # Sunflower Yellow
    ERROR_COLOR = "#E74C3C"  # Alizarin Red

    # Fonts
    FONT_FAMILY = "Segoe UI"
    FONT_SIZE_NORMAL = 10
    FONT_SIZE_LARGE = 14
    FONT_SIZE_HEADER = 18

    @staticmethod
    def apply(window):
        """Apply styles to the application."""
        style = ttk.Style(window)
        style.theme_use('clam')

        # --- General Widget Styling ---
        style.configure(".",
                        background=AppStyles.BACKGROUND_COLOR,
                        foreground=AppStyles.PRIMARY_COLOR,
                        font=(AppStyles.FONT_FAMILY, AppStyles.FONT_SIZE_NORMAL))

        # --- Frame Styling ---
        style.configure("TFrame", background=AppStyles.BACKGROUND_COLOR)

        # --- Label Styling ---
        style.configure("TLabel",
                        background=AppStyles.BACKGROUND_COLOR,
                        foreground=AppStyles.PRIMARY_COLOR,
                        font=(AppStyles.FONT_FAMILY, AppStyles.FONT_SIZE_NORMAL))

        style.configure("Header.TLabel",
                        font=(AppStyles.FONT_FAMILY, AppStyles.FONT_SIZE_HEADER, "bold"),
                        foreground=AppStyles.PRIMARY_COLOR)

        style.configure("Status.TLabel",
                        font=(AppStyles.FONT_FAMILY, AppStyles.FONT_SIZE_LARGE, "italic"),
                        foreground=AppStyles.SECONDARY_COLOR)

        # --- Button Styling ---
        style.configure("TButton",
                        background=AppStyles.ACCENT_COLOR,
                        foreground=AppStyles.TEXT_COLOR,
                        font=(AppStyles.FONT_FAMILY, AppStyles.FONT_SIZE_NORMAL, "bold"),
                        borderwidth=0,
                        padding=(10, 5))
        style.map("TButton",
                  background=[('active', '#2980B9')],  # Darker blue on hover
                  foreground=[('active', AppStyles.TEXT_COLOR)])

        # --- Notebook (Tabs) Styling ---
        style.configure("TNotebook", background=AppStyles.BACKGROUND_COLOR)
        style.configure("TNotebook.Tab",
                        background=AppStyles.BACKGROUND_COLOR,
                        foreground=AppStyles.PRIMARY_COLOR,
                        font=(AppStyles.FONT_FAMILY, AppStyles.FONT_SIZE_NORMAL, "bold"),
                        padding=(10, 5))
        style.map("TNotebook.Tab",
                  background=[("selected", AppStyles.ACCENT_COLOR)],
                  foreground=[("selected", AppStyles.TEXT_COLOR)])

        # --- Treeview (for tables) Styling ---
        style.configure("Treeview",
                        background="#FFFFFF",
                        foreground=AppStyles.PRIMARY_COLOR,
                        fieldbackground="#FFFFFF",
                        rowheight=25)
        style.map("Treeview",
                  background=[('selected', AppStyles.ACCENT_COLOR)],
                  foreground=[('selected', AppStyles.TEXT_COLOR)])

        style.configure("Treeview.Heading",
                        background=AppStyles.PRIMARY_COLOR,
                        foreground=AppStyles.TEXT_COLOR,
                        font=(AppStyles.FONT_FAMILY, AppStyles.FONT_SIZE_NORMAL, "bold"))
