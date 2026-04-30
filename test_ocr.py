from ocr_core.ocr_engine import wait_for_text
import traceback

try:
    result = wait_for_text("Recycle Bin", timeout=5.0)
    print("result:", result)
except Exception:
    traceback.print_exc()