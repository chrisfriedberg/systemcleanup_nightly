import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import os
import ctypes
import sys
import logging
from logging.handlers import RotatingFileHandler
import queue
import time

# Global variables and logger setup
log_queue = queue.Queue()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# File handler for logging
file_handler = RotatingFileHandler('cleanup.log', maxBytes=1024*1024, backupCount=5)
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)

# Queue handler for GUI logging
class QueueHandler(logging.Handler):
    def __init__(self, queue):
        super().__init__()
        self.queue = queue
    
    def emit(self, record):
        self.queue.put(record)

queue_handler = QueueHandler(log_queue)
queue_handler.setFormatter(file_formatter)

# Add handlers to logger
logger.addHandler(file_handler)
logger.addHandler(queue_handler)

# Stats object to store cleanup results
class Stats:
    def __init__(self):
        self.sfc_result = "No integrity violations found"

stats = Stats()

def perform_cleanup_task(update_callback, complete_callback, stop_event):
    """
    Basic cleanup task - this is a placeholder implementation.
    You can replace this with your actual cleanup logic.
    """
    try:
        logger.info("Starting cleanup process...")
        update_callback("Initializing cleanup...")
        
        # Simulate cleanup steps
        steps = [
            ("Clearing temporary files...", 20),
            ("Cleaning cache directories...", 40),
            ("Running system file check...", 60),
            ("Optimizing system files...", 80),
            ("Finalizing cleanup...", 100)
        ]
        
        for step_name, progress in steps:
            if stop_event.is_set():
                logger.info("Cleanup terminated by user")
                return
            
            update_callback(f"{step_name} {progress}%")
            logger.info(step_name)
            time.sleep(2)  # Simulate work being done
        
        # Simulate SFC result
        stats.sfc_result = "No integrity violations found"
        logger.info("Cleanup completed successfully")
        
        # Call completion callback
        update_callback("Cleanup completed!")
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        update_callback(f"Error: {e}")
    finally:
        # Call completion callback
        if hasattr(complete_callback, '__call__'):
            complete_callback()

class CleanupApp:
    def __init__(self, master):
        self.master = master
        master.title("Nightly Cleanup Tool")
        master.geometry("700x500")
        master.resizable(True, True)

        self.cleanup_thread = None
        self.stop_requested = threading.Event()

        # Create widgets
        self.create_widgets()
        
        # Start log queue processor
        self.master.after(100, self.process_log_queue)

    def create_widgets(self):
        # Log text area
        self.log_text = scrolledtext.ScrolledText(
            self.master, 
            wrap=tk.WORD, 
            state='disabled', 
            height=20, 
            width=80, 
            bg='#2b2b2b', 
            fg='#cccccc', 
            font=("Consolas", 10)
        )
        self.log_text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # Progress bar
        self.progress_bar = ttk.Progressbar(self.master, mode='determinate', length=200)
        self.progress_bar.pack(pady=5)

        # Status label
        self.status_label = ttk.Label(self.master, text="Ready to run cleanup.")
        self.status_label.pack(pady=5)

        # Button frame
        self.button_frame = ttk.Frame(self.master)
        self.button_frame.pack(pady=10)

        # Buttons
        self.start_button = ttk.Button(
            self.button_frame, 
            text="Start Cleanup", 
            command=self.start_cleanup
        )
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.terminate_button = ttk.Button(
            self.button_frame, 
            text="Terminate", 
            command=self.terminate_cleanup, 
            state='disabled'
        )
        self.terminate_button.pack(side=tk.LEFT, padx=5)

        self.close_button = ttk.Button(
            self.button_frame, 
            text="Close", 
            command=self.close_app
        )
        self.close_button.pack(side=tk.LEFT, padx=5)

    def process_log_queue(self):
        """Process log messages from the queue and display them in the GUI."""
        # Use the formatter from the logger's handlers
        formatter = None
        for handler in logger.handlers:
            if hasattr(handler, 'formatter') and handler.formatter:
                formatter = handler.formatter
                break

        while not log_queue.empty():
            record = log_queue.get()
            if formatter:
                msg = formatter.format(record)
            else:
                msg = record.getMessage()
            
            self.log_text.config(state='normal')
            self.log_text.insert(tk.END, msg + "\n")
            self.log_text.see(tk.END)
            self.log_text.config(state='disabled')
        
        # Schedule next check
        self.master.after(100, self.process_log_queue)

    def update_status(self, message):
        """Update the status label and log the message."""
        self.status_label.config(text=message)
        logger.info(message)
        
        # Extract progress percentage from message if present
        if "%" in message:
            try:
                # Find percentage in the message
                parts = message.split()
                for part in parts:
                    if "%" in part:
                        progress = float(part.replace("%", ""))
                        self.progress_bar["value"] = progress
                        break
            except (ValueError, IndexError):
                pass

    def start_cleanup(self):
        """Start the cleanup process in a separate thread."""
        if self.cleanup_thread and self.cleanup_thread.is_alive():
            self.update_status("Cleanup already running...")
            return

        # Clear previous logs in GUI
        self.log_text.config(state='normal')
        self.log_text.delete('1.0', tk.END)
        self.log_text.config(state='disabled')

        # Update UI
        self.update_status("Cleanup started. Please wait...")
        self.progress_bar["value"] = 0
        self.start_button.config(state='disabled')
        self.terminate_button.config(state='normal')
        self.stop_requested.clear()

        # Start cleanup thread
        self.cleanup_thread = threading.Thread(
            target=perform_cleanup_task,
            args=(self.update_status, self.cleanup_complete_callback, self.stop_requested)
        )
        self.cleanup_thread.daemon = True
        self.cleanup_thread.start()

    def cleanup_complete_callback(self):
        """Called when cleanup is complete."""
        self.progress_bar["value"] = 100
        self.start_button.config(state='normal')
        self.terminate_button.config(state='disabled')
        self.update_status("Cleanup complete! Check log for details.")
        
        # Show SFC result in a popup
        messagebox.showinfo("SFC Result", f"SFC /scannow result: {stats.sfc_result}")
        
        # Show splash screen
        splash = SplashScreen(self.master)

    def terminate_cleanup(self):
        """Terminate the cleanup process immediately."""
        self.update_status("Terminating process immediately!")
        self.master.update()
        os._exit(1)

    def close_app(self):
        """Close the application."""
        self.master.destroy()

class SplashScreen:
    def __init__(self, parent):
        self.window = tk.Toplevel(parent)
        self.window.title("Cleanup Complete")

        # Calculate window position (center of screen)
        self.window.update_idletasks()
        window_width = 400
        window_height = 320
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
        
        self.window.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.window.grab_set()
        self.window.attributes('-topmost', True)
        self.window.overrideredirect(True)

        # Create main frame
        main_frame = ttk.Frame(self.window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)

        # Success icon
        icon_label = ttk.Label(main_frame, text="✓", font=("Arial", 72))
        icon_label.grid(row=0, column=0, pady=(10, 0), sticky="n")

        # Finished text
        finished_label = ttk.Label(main_frame, text="FINISHED", font=("Arial", 24, "bold"))
        finished_label.grid(row=1, column=0, pady=(10, 0), sticky="n")

        # Close button
        close_button = ttk.Button(main_frame, text="Close", command=self.close_window)
        close_button.grid(row=2, column=0, pady=(30, 10), sticky="s")

        # Style
        style = ttk.Style()
        style.configure("Splash.TFrame", background="#f0f0f0")
        main_frame.configure(style="Splash.TFrame")

        # Bind escape key
        self.window.bind('<Escape>', lambda e: self.close_window())

    def close_window(self):
        """Close the splash screen and main application."""
        self.window.destroy()
        self.window.master.destroy()

def run_as_admin():
    """Relaunch the script with admin rights if not already running as admin."""
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
    except:
        is_admin = False
    
    if not is_admin:
        # Relaunch as admin
        params = ' '.join([f'"{arg}"' for arg in sys.argv])
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, params, None, 1
        )
        sys.exit(0)

def main():
    """Main function to run the application."""
    # Check for admin privileges
    run_as_admin()
    
    # Create and run the GUI
    root = tk.Tk()
    app = CleanupApp(root)
    
    # Configure the QueueHandler formatter
    for handler in logger.handlers:
        if isinstance(handler, RotatingFileHandler):
            gui_formatter = handler.formatter
            break
    else:
        gui_formatter = logging.Formatter('%(levelname)s: %(message)s')

    for handler in logger.handlers:
        if isinstance(handler, QueueHandler):
            handler.setFormatter(gui_formatter)
            break

    # Start the GUI main loop
    root.mainloop()

if __name__ == "__main__":
    main() 