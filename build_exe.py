"""
Build K-ZERO standalone .exe for Windows.

Usage: python build_exe.py

Produces: dist/kzero.exe (~50MB)
The .exe auto-downloads Ollama + model on first run.
"""

import subprocess
import sys

# Collect all data files that need to be bundled
data_files = [
    # Character data (personality, voice, axioms, clash, memory)
    ("characters", "characters"),
    # Config files
    ("config", "config"),
    # Scenarios
    ("scenarios", "scenarios"),
    # Profiles
    ("profiles", "profiles"),
    # Runner modules
    ("runner", "runner"),
    # App module
    ("app.py", "."),
]

# Build the --add-data arguments
add_data_args = []
for src, dst in data_files:
    add_data_args.extend(["--add-data", f"{src};{dst}"])

cmd = [
    sys.executable, "-m", "PyInstaller",
    "--onefile",
    "--name", "kzero",
    "--console",  # Show console for status messages
    *add_data_args,
    "--hidden-import", "dash",
    "--hidden-import", "plotly",
    "--hidden-import", "openai",
    "--hidden-import", "anthropic",
    "--hidden-import", "dotenv",
    "--hidden-import", "rich",
    "--hidden-import", "numpy",
    "launcher.py",
]

print("Building K-ZERO standalone .exe...")
print(f"Command: {' '.join(cmd[:10])}...")
subprocess.run(cmd, check=True)
print("\nDone! Find your .exe at: dist/kzero.exe")
print("Share it — users just double-click, no Python needed.")
