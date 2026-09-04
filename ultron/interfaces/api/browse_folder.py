import os
import sys
import logging
import traceback

logger = logging.getLogger(__name__)

def select_folder_dialog(initial_dir: str = None, headless: bool = False) -> dict:
    """
    Opens native OS folder browser dialog.
    Headless/display errors are caught specifically and return fallback=True.
    Unexpected programming errors are logged with stack trace.
    """
    if headless or os.environ.get("ULTRON_HEADLESS") == "1":
        norm_init = os.path.normpath(initial_dir or os.getcwd()).replace("\\", "/")
        return {"path": norm_init, "cancelled": False, "fallback": False}

    if not initial_dir or not os.path.isdir(initial_dir):
        initial_dir = os.getcwd()

    # Primary Windows Path: Use native PowerShell FolderBrowserDialog (works across threads & services)
    if sys.platform == "win32":
        try:
            import subprocess
            import base64
            abs_init = os.path.abspath(initial_dir).replace("'", "''")
            ps_script = f"""
Add-Type -AssemblyName System.Windows.Forms
$dialog = New-Object System.Windows.Forms.FolderBrowserDialog
if (Test-Path -LiteralPath '{abs_init}') {{
    $dialog.SelectedPath = '{abs_init}'
}}
$dialog.Description = 'Select Repository Folder for Ultron'
$dialog.ShowNewFolderButton = $false
$topForm = New-Object System.Windows.Forms.Form
$topForm.TopMost = $true
$topForm.StartPosition = [System.Windows.Forms.FormStartPosition]::CenterScreen
try {{
    $res = $dialog.ShowDialog($topForm)
    if ($res -eq [System.Windows.Forms.DialogResult]::OK) {{
        Write-Output $dialog.SelectedPath
    }}
}} finally {{
    $dialog.Dispose()
    $topForm.Dispose()
}}
"""
            encoded = base64.b64encode(ps_script.encode("utf-16le")).decode("ascii")
            result = subprocess.run(
                ["powershell", "-Sta", "-NoProfile", "-EncodedCommand", encoded],
                capture_output=True,
                text=True,
                timeout=120
            )
            selected_path = result.stdout.strip()
            if not selected_path:
                return {"path": "", "cancelled": True, "fallback": False}
            norm_path = os.path.normpath(selected_path).replace("\\", "/")
            return {"path": norm_path, "cancelled": False, "fallback": False}
        except subprocess.TimeoutExpired:
            logger.info("Folder dialog timed out after 120s.")
            return {"path": "", "cancelled": True, "fallback": False}
        except Exception as e:
            logger.info("PowerShell folder dialog failed (%s), trying Tkinter fallback.", e)

    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        try:
            root.lift()
            root.attributes("-topmost", True)
            root.focus_force()
            root.update()
        except Exception:
            pass

        selected_path = filedialog.askdirectory(
            parent=root,
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
