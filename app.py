"""
K-ZERO — Council of 8 Web App
Run locally: python app.py
Deploy: Hugging Face Spaces, Render, Railway
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load environment
load_dotenv()

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).parent))

from runner.visualize import create_app

# Find the latest analysis file, or use a default
transcripts_dir = Path(__file__).parent / "transcripts"
analysis_files = sorted(transcripts_dir.glob("*_analysis.json"))

if analysis_files:
    default_analysis = str(analysis_files[-1])
    print(f"Loading analysis: {analysis_files[-1].name}")
else:
    print("No analysis files found. Run a simulation first:")
    print("  python -m runner.council_runner --rounds 5")
    print("  python -m runner.analyze transcripts/<latest>.json")
    sys.exit(1)

app = create_app(default_analysis)
server = app.server  # For WSGI deployment (gunicorn, etc.)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 7860))  # 7860 = HF Spaces default
    print(f"\n  K-ZERO Dashboard: http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=False)
