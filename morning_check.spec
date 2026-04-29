# morning_check.spec
# Build command: pyinstaller morning_check.spec
#
# Requirements before building:
#   pip install pyinstaller
#   Tesseract must be installed separately (not bundled here).
#   Copy tesseract.exe + tessdata/ next to the output .exe after building,
#   or point Settings → Tesseract Path to its install location.

import sys
from pathlib import Path

ROOT = Path(SPECPATH)

block_cipher = None

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        # Bundle the entire gui package
        (str(ROOT / "gui"),           "gui"),
        # Bundle OCR and action modules
        (str(ROOT / "ocr_core"),      "ocr_core"),
        (str(ROOT / "action_engine"), "action_engine"),
        # Bundle configs and output skeleton
        (str(ROOT / "configs"),       "configs"),
    ],
    hiddenimports=[
        "pytesseract",
        "PIL",
        "PIL.Image",
        "PIL.ImageTk",
        "PIL.ImageEnhance",
        "PIL.ImageFilter",
        "mss",
        "mss.tools",
        "pyautogui",
        "pyscreeze",
        "yaml",
        "openpyxl",
        "tkinter",
        "tkinter.ttk",
        "tkinter.filedialog",
        "tkinter.messagebox",
        "tkinter.simpledialog",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MorningCheck",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # no black console window — GUI only
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,              # set to "assets/icon.ico" if you add one
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="MorningCheck",
)
