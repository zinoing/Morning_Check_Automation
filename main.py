"""
main.py — Entry point
Run directly:      python main.py
After packaging:   MorningCheck.exe
"""
import sys
import os
from pathlib import Path

# ── Path setup for both dev and PyInstaller bundle ────────────────────────────
if getattr(sys, "frozen", False):
    # Running as compiled .exe — _MEIPASS is the temp extraction folder
    _BUNDLE = Path(sys._MEIPASS)
    _ROOT   = Path(sys.executable).parent
else:
    _ROOT   = Path(__file__).parent
    _BUNDLE = _ROOT

# Make project modules importable — only root, use package imports everywhere
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# ── Ensure output directories exist ───────────────────────────────────────────
for folder in ["output/screenshots", "output/logs", "output/reports", "configs"]:
    (_ROOT / folder).mkdir(parents=True, exist_ok=True)

# ── Launch GUI ────────────────────────────────────────────────────────────────
from gui.app import SmartWorkerApp

if __name__ == "__main__":
    app = SmartWorkerApp()
    app.run()
