"""
diagnose_tesseract.py
Run this to find exactly where Tesseract is and why it's not being found.
"""

import os
import sys
import subprocess
from pathlib import Path

print("=" * 60)
print("  Tesseract Diagnostic")
print("=" * 60)

# 1. Check all possible paths
paths_to_check = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    r"C:\Users\CHOJIN\AppData\Local\Programs\Tesseract-OCR\tesseract.exe",
    r"C:\Users\CHOJIN\AppData\Local\Tesseract-OCR\tesseract.exe",
]

print("\n[1] Checking known paths:")
for p in paths_to_check:
    exists = Path(p).exists()
    print(f"  {'✅' if exists else '❌'}  {p}")

# 2. Search entire AppData for tesseract.exe
print("\n[2] Searching AppData for tesseract.exe ...")
appdata = Path(os.environ.get("LOCALAPPDATA", r"C:\Users\CHOJIN\AppData\Local"))
found = list(appdata.rglob("tesseract.exe"))
if found:
    for f in found:
        print(f"  ✅ FOUND: {f}")
else:
    print("  ❌ Not found in AppData")

# 3. Search Program Files
print("\n[3] Searching Program Files for tesseract.exe ...")
for pf in [r"C:\Program Files", r"C:\Program Files (x86)"]:
    found2 = list(Path(pf).rglob("tesseract.exe"))
    for f in found2:
        print(f"  ✅ FOUND: {f}")

# 4. Check system PATH
print("\n[4] Checking system PATH:")
for p in os.environ.get("PATH", "").split(";"):
    if "tesseract" in p.lower():
        print(f"  ✅ In PATH: {p}")
        break
else:
    print("  ❌ 'tesseract' not found in PATH")

# 5. Try calling tesseract directly
print("\n[5] Trying to call tesseract from command line:")
try:
    result = subprocess.run(["tesseract", "--version"], capture_output=True, text=True)
    print(f"  ✅ Works via PATH:\n  {result.stdout.strip()}")
except FileNotFoundError:
    print("  ❌ Cannot call 'tesseract' from command line")

# 6. Try setting path manually and testing pytesseract
print("\n[6] Testing pytesseract with explicit path:")
try:
    import pytesseract
    from PIL import Image

    found_paths = list(Path(os.environ.get("LOCALAPPDATA", "")).rglob("tesseract.exe"))
    if found_paths:
        tess_path = str(found_paths[0])
        pytesseract.pytesseract.tesseract_cmd = tess_path
        print(f"  Setting path to: {tess_path}")
        version = pytesseract.get_tesseract_version()
        print(f"  ✅ pytesseract works! Version: {version}")
        print(f"\n  👉 ADD THIS LINE to ocr_engine.py:")
        print(f'     pytesseract.pytesseract.tesseract_cmd = r"{tess_path}"')
    else:
        print("  ❌ Could not find tesseract.exe anywhere")
        print("\n  👉 Please reinstall Tesseract from:")
        print("     https://github.com/UB-Mannheim/tesseract/wiki")
except Exception as e:
    print(f"  ❌ Error: {e}")

print("\n" + "=" * 60)