import os
import sys
import logging
import traceback

logger = logging.getLogger(__name__)

def select_folder_dialog(initial_dir: str = None) -> dict:
    """
    Opens native OS folder browser dialog.
    Headless/display errors are caught specifically and return fallback=True.
    Unexpected programming errors are logged with stack trace.
    """
    if os.environ.get("ULTRON_HEADLESS") == "1":
        return {"path": "", "cancelled": True, "fallback": True}

    if not initial_dir or not os.path.isdir(initial_dir):
        initial_dir = os.getcwd()

    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        # Keep window on top for Windows OS dialog focus
        try:
            root.attributes("-topmost", True)
        except Exception:
            pass

        selected_path = filedialog.askdirectory(
            initialdir=initial_dir,
            title="Select Project Directory for Ultron RKM"
        )
        try:
            root.destroy()
        except Exception:
            pass

        if not selected_path:
            return {"path": "", "cancelled": True, "fallback": False}

        norm_path = os.path.normpath(selected_path).replace("\\", "/")
        return {"path": norm_path, "cancelled": False, "fallback": False}

    except (ImportError, RuntimeError, AttributeError) as e:
        # GUI/display library unavailable
        logger.info("Native GUI dialog unavailable (%s). Falling back to inline input.", e)
        return {"path": "", "cancelled": True, "fallback": True, "error": f"Native GUI dialog unavailable: {e}"}

    except Exception as e:
        # Catch _tkinter.TclError or display-connection errors specifically
        err_str = str(e)
        if "TclError" in type(e).__name__ or "display" in err_str.lower() or "screen" in err_str.lower():
            logger.info("Headless environment detected (%s). Falling back to inline input.", e)
            return {"path": "", "cancelled": True, "fallback": True, "error": "Native GUI dialog unavailable on headless system."}

        # Unexpected programming exception -> log traceback
        logger.error("Unexpected error in folder selection dialog:\n%s", traceback.format_exc())
        return {"path": "", "cancelled": True, "fallback": True, "error": f"Folder dialog error: {e}"}
