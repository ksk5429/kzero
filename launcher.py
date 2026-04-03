"""
K-ZERO Launcher — One-click standalone for Windows.

Downloads Ollama + model on first run. Starts everything. Opens browser.
No Python, no pip, no terminal needed. Just double-click.

Build: pyinstaller --onefile --name kzero --icon=icon.ico launcher.py
"""

import os
import platform
import shutil
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

OLLAMA_VERSION = "0.19.0"
OLLAMA_URL = f"https://github.com/ollama/ollama/releases/download/v{OLLAMA_VERSION}/OllamaSetup.exe"
MODEL = "qwen2.5:7b"
APP_PORT = 7860


def _print(msg):
    """Print with K-ZERO branding."""
    print(f"  [K-ZERO] {msg}")


def _check_ollama():
    """Check if Ollama is installed and running."""
    ollama_path = shutil.which("ollama")
    if ollama_path:
        _print(f"Ollama found: {ollama_path}")
        return True

    # Check common install paths on Windows
    common_paths = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe",
        Path("C:/Program Files/Ollama/ollama.exe"),
        Path(os.environ.get("USERPROFILE", "")) / "AppData" / "Local" / "Programs" / "Ollama" / "ollama.exe",
    ]
    for p in common_paths:
        if p.exists():
            _print(f"Ollama found: {p}")
            # Add to PATH for this session
            os.environ["PATH"] = str(p.parent) + os.pathsep + os.environ.get("PATH", "")
            return True

    return False


def _install_ollama():
    """Download and install Ollama silently."""
    _print("Ollama not found. Downloading...")
    installer_path = Path(os.environ.get("TEMP", ".")) / "OllamaSetup.exe"

    try:
        _print(f"Downloading from {OLLAMA_URL}...")
        urllib.request.urlretrieve(OLLAMA_URL, str(installer_path))
        _print("Download complete. Installing (this may take a minute)...")

        # Run installer silently
        subprocess.run([str(installer_path), "/VERYSILENT", "/NORESTART"], check=True, timeout=300)
        _print("Ollama installed successfully.")

        # Add to PATH
        ollama_dir = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama"
        if ollama_dir.exists():
            os.environ["PATH"] = str(ollama_dir) + os.pathsep + os.environ.get("PATH", "")

        return True
    except Exception as e:
        _print(f"Auto-install failed: {e}")
        _print("Please install Ollama manually: https://ollama.com/download")
        input("Press Enter after installing Ollama...")
        return _check_ollama()


def _start_ollama_server():
    """Start Ollama server if not already running."""
    try:
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2)
        _print("Ollama server already running.")
        return True
    except Exception:
        pass

    _print("Starting Ollama server...")
    try:
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0,
        )
        # Wait for server to start
        for _ in range(30):
            time.sleep(1)
            try:
                urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2)
                _print("Ollama server started.")
                return True
            except Exception:
                pass
        _print("Ollama server failed to start.")
        return False
    except FileNotFoundError:
        _print("Cannot find ollama command. Is it installed?")
        return False


def _check_model():
    """Check if the model is available, pull if not."""
    try:
        import json
        resp = urllib.request.urlopen("http://localhost:11434/api/tags", timeout=5)
        data = json.loads(resp.read())
        model_names = [m["name"] for m in data.get("models", [])]

        if MODEL in model_names or f"{MODEL}:latest" in model_names:
            _print(f"Model {MODEL} ready.")
            return True

        _print(f"Model {MODEL} not found. Pulling (this may take a few minutes)...")
        subprocess.run(["ollama", "pull", MODEL], check=True, timeout=600)
        _print(f"Model {MODEL} pulled successfully.")
        return True
    except Exception as e:
        _print(f"Model check failed: {e}")
        _print(f"Run manually: ollama pull {MODEL}")
        return False


def _setup_env():
    """Set up environment variables for the app."""
    os.environ["LLM_API_KEY"] = "ollama"
    os.environ["LLM_BASE_URL"] = "http://localhost:11434/v1"
    os.environ["COUNCIL_MODEL"] = MODEL
    os.environ["COUNCIL_TEMPERATURE"] = "0.85"
    os.environ["COUNCIL_MAX_TOKENS"] = "120"


def _find_app_dir():
    """Find the app directory (handles both dev and PyInstaller builds)."""
    # PyInstaller bundles files in _MEIPASS
    if hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS)
    return Path(__file__).parent


def main():
    print()
    print("  ╔═══════════════════════════════════════╗")
    print("  ║      K-ZERO · Council of 8            ║")
    print("  ║  8 minds. 1 question. Infinite chaos.  ║")
    print("  ╚═══════════════════════════════════════╝")
    print()

    # Step 1: Check/install Ollama
    if not _check_ollama():
        if not _install_ollama():
            _print("Cannot proceed without Ollama. Exiting.")
            input("Press Enter to exit...")
            sys.exit(1)

    # Step 2: Start Ollama server
    if not _start_ollama_server():
        _print("Cannot start Ollama server. Exiting.")
        input("Press Enter to exit...")
        sys.exit(1)

    # Step 3: Check/pull model
    if not _check_model():
        _print("Cannot proceed without model. Exiting.")
        input("Press Enter to exit...")
        sys.exit(1)

    # Step 4: Set up environment
    _setup_env()

    # Step 5: Launch the web app
    _print(f"Starting K-ZERO web app on port {APP_PORT}...")

    app_dir = _find_app_dir()
    sys.path.insert(0, str(app_dir))
    os.chdir(str(app_dir))

    # Open browser after a short delay
    import threading

    def open_browser():
        time.sleep(3)
        webbrowser.open(f"http://localhost:{APP_PORT}")
        _print(f"Browser opened: http://localhost:{APP_PORT}")

    threading.Thread(target=open_browser, daemon=True).start()

    _print("K-ZERO is running. Press Ctrl+C or close this window to stop.")
    _print(f"Open http://localhost:{APP_PORT} in your browser.")
    print()

    # Import and run the Dash app with proper cleanup on exit
    import signal
    import atexit

    def _cleanup():
        """Kill all child threads and simulation on exit."""
        _print("Shutting down...")
        try:
            import app as app_module
            app_module._sim_stop = True
            app_module._sim_running = False
            app_module._sim_done = True
        except Exception:
            pass
        # Force kill any remaining threads
        os._exit(0)

    atexit.register(_cleanup)
    signal.signal(signal.SIGINT, lambda s, f: _cleanup())
    signal.signal(signal.SIGTERM, lambda s, f: _cleanup())

    # On Windows, also handle console close
    if platform.system() == "Windows":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32

            def _console_handler(event):
                if event in (0, 2, 5, 6):  # CTRL_C, CTRL_CLOSE, CTRL_LOGOFF, CTRL_SHUTDOWN
                    _cleanup()
                    return True
                return False

            handler_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_ulong)
            kernel32.SetConsoleCtrlHandler(handler_type(_console_handler), True)
        except Exception:
            pass

    try:
        from app import app as dash_app
        dash_app.run(host="0.0.0.0", port=APP_PORT, debug=False)
    except (KeyboardInterrupt, SystemExit):
        _cleanup()
    except Exception as e:
        _print(f"App error: {e}")
        input("Press Enter to exit...")
        _cleanup()


if __name__ == "__main__":
    main()
