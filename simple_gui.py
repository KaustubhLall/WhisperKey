"""
Simple GUI implementation with extensive logging for debugging
"""
import tkinter as tk
from tkinter import ttk
import logging
import threading
import time

# Setup detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('gui_debug.log')
    ]
)
logger = logging.getLogger("simple_gui")

class SimpleWhisperKeyGUI:
    """Simple GUI with extensive logging for debugging"""
    
    def __init__(self):
        logger.info("=== Starting SimpleWhisperKeyGUI initialization ===")
        self.window = None
        self.is_visible = False
        
        try:
            logger.info("Step 1: Creating tkinter window")
            self.create_window()
            logger.info("Step 1: SUCCESS - Window created")
            
            logger.info("Step 2: Creating widgets")
            self.create_simple_widgets()
            logger.info("Step 2: SUCCESS - Widgets created")
            
            logger.info("=== SimpleWhisperKeyGUI initialization complete ===")
            
        except Exception as e:
            logger.error(f"CRITICAL ERROR during initialization: {e}", exc_info=True)
            raise
    
    def create_window(self):
        """Create the main window with logging"""
        logger.debug("Creating Tk() window...")
        
        try:
            self.window = tk.Tk()
            logger.debug("SUCCESS: tk.Tk() created")
            
            logger.debug("Setting window title...")
            self.window.title("WhisperKey - Simple Debug GUI")
            logger.debug("SUCCESS: Title set")
            
            logger.debug("Setting window geometry...")
            self.window.geometry("400x300")
            logger.debug("SUCCESS: Geometry set")
            
            logger.debug("Setting window properties...")
            self.window.resizable(True, True)
            self.window.minsize(300, 200)
            logger.debug("SUCCESS: Window properties set")
            
            logger.debug("Setting window protocol...")
            self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
            logger.debug("SUCCESS: Protocol set")
            
            logger.debug("Initially hiding window...")
            self.window.withdraw()
            self.is_visible = False
            logger.debug("SUCCESS: Window hidden")
            
        except Exception as e:
            logger.error(f"ERROR in create_window: {e}", exc_info=True)
            raise
    
    def create_simple_widgets(self):
        """Create minimal widgets with logging"""
        logger.debug("Creating main frame...")
        
        try:
            # Main frame
            main_frame = ttk.Frame(self.window, padding="20")
            main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
            logger.debug("SUCCESS: Main frame created and placed")
            
            # Configure grid
            self.window.columnconfigure(0, weight=1)
            self.window.rowconfigure(0, weight=1)
            logger.debug("SUCCESS: Grid configured")
            
            # Title label
            title_label = ttk.Label(main_frame, text="WhisperKey Debug GUI", font=("Arial", 16, "bold"))
            title_label.grid(row=0, column=0, pady=(0, 20))
            logger.debug("SUCCESS: Title label created")
            
            # Status label
            self.status_label = ttk.Label(main_frame, text="Status: GUI Loaded Successfully!")
            self.status_label.grid(row=1, column=0, pady=(0, 20))
            logger.debug("SUCCESS: Status label created")
            
            # Simple button
            test_button = ttk.Button(main_frame, text="Test Button", command=self.test_button_click)
            test_button.grid(row=2, column=0, pady=(0, 10))
            logger.debug("SUCCESS: Test button created")
            
            # Show/Hide button
            toggle_button = ttk.Button(main_frame, text="Hide Window", command=self.toggle_window)
            toggle_button.grid(row=3, column=0)
            logger.debug("SUCCESS: Toggle button created")
            
            logger.debug("All widgets created successfully")
            
        except Exception as e:
            logger.error(f"ERROR in create_simple_widgets: {e}", exc_info=True)
            raise
    
    def test_button_click(self):
        """Test button callback with logging"""
        logger.info("Test button clicked!")
        try:
            self.status_label.configure(text=f"Button clicked at {time.strftime('%H:%M:%S')}")
            logger.debug("Status label updated successfully")
        except Exception as e:
            logger.error(f"ERROR in test_button_click: {e}", exc_info=True)
    
    def show_window(self):
        """Show the window with logging"""
        logger.info("Attempting to show window...")
        
        try:
            if not self.window:
                logger.error("ERROR: Window is None!")
                return
            
            logger.debug("Calling deiconify()...")
            self.window.deiconify()
            logger.debug("SUCCESS: deiconify() called")
            
            logger.debug("Calling lift()...")
            self.window.lift()
            logger.debug("SUCCESS: lift() called")
            
            logger.debug("Calling focus_force()...")
            self.window.focus_force()
            logger.debug("SUCCESS: focus_force() called")
            
            self.is_visible = True
            logger.info("Window shown successfully")
            
            # Force update
            logger.debug("Calling update_idletasks()...")
            self.window.update_idletasks()
            logger.debug("SUCCESS: update_idletasks() called")
            
        except Exception as e:
            logger.error(f"ERROR in show_window: {e}", exc_info=True)
    
    def hide_window(self):
        """Hide the window with logging"""
        logger.info("Attempting to hide window...")
        
        try:
            if self.window:
                logger.debug("Calling withdraw()...")
                self.window.withdraw()
                logger.debug("SUCCESS: withdraw() called")
                
                self.is_visible = False
                logger.info("Window hidden successfully")
            else:
                logger.warning("Window is None, cannot hide")
                
        except Exception as e:
            logger.error(f"ERROR in hide_window: {e}", exc_info=True)
    
    def toggle_window(self):
        """Toggle window visibility with logging"""
        logger.info(f"Toggling window (currently visible: {self.is_visible})")
        
        if self.is_visible:
            self.hide_window()
        else:
            self.show_window()
    
    def on_closing(self):
        """Handle window closing with logging"""
        logger.info("Window close requested")
        self.hide_window()
    
    def cleanup(self):
        """Clean up resources with logging"""
        logger.info("Starting cleanup...")
        
        try:
            if self.window:
                logger.debug("Destroying window...")
                self.window.destroy()
                logger.debug("SUCCESS: Window destroyed")
                self.window = None
            
            logger.info("Cleanup completed successfully")
            
        except Exception as e:
            logger.error(f"ERROR in cleanup: {e}", exc_info=True)


def test_simple_gui():
    """Test function to create and show the simple GUI"""
    logger.info("=== Starting Simple GUI Test ===")
    
    try:
        # Create GUI
        logger.info("Creating SimpleWhisperKeyGUI instance...")
        gui = SimpleWhisperKeyGUI()
        logger.info("SUCCESS: GUI instance created")
        
        # Show window
        logger.info("Showing GUI window...")
        gui.show_window()
        logger.info("SUCCESS: GUI window shown")
        
        # Keep alive for testing
        logger.info("GUI is now running. Window should be visible.")
        logger.info("Check if window appears. Press Ctrl+C to exit.")
        
        # Simple event loop
        while True:
            try:
                if gui.window:
                    gui.window.update_idletasks()
                    gui.window.update()
                time.sleep(0.01)  # 100 FPS update rate
            except tk.TclError:
                logger.info("Window closed by user")
                break
            except KeyboardInterrupt:
                logger.info("Interrupted by user")
                break
        
        # Cleanup
        logger.info("Cleaning up...")
        gui.cleanup()
        logger.info("=== Simple GUI Test Complete ===")
        
    except Exception as e:
        logger.error(f"CRITICAL ERROR in test: {e}", exc_info=True)


if __name__ == "__main__":
    test_simple_gui()
