"""
test_ocr_core.py
----------------
Phase 1 - Step 1.7
Test suite to validate the OCR core on real Windows UI elements.

Run this FIRST on each server to confirm Tesseract accuracy before
running any automation configs.

Usage:
    python test_ocr_core.py

Each test prints PASS / FAIL and saves screenshots for inspection.
"""

import sys
import time
from pathlib import Path

# Add project root so 'ocr_core' package is found.
# Works whether you run from tests/, morning_check/, or anywhere else.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ocr_core import (
    capture_screen,
    preprocess_for_ocr,
    save_screenshot,
    get_all_text_positions,
    find_text_on_screen,
    verify_text_exists,
    wait_for_text,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _result(name: str, passed: bool, detail: str = ""):
    icon = "✅ PASS" if passed else "❌ FAIL"
    print(f"  {icon}  {name}")
    if detail:
        print(f"         {detail}")


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_screen_capture():
    """Test 1: Can we capture the screen at all?"""
    print("\n[Test 1] Screen capture")
    img = capture_screen()
    ok = img is not None and img.width > 0 and img.height > 0
    _result("capture_screen()", ok, f"Captured {img.width}x{img.height} px")

    path = save_screenshot(img, "test_raw_capture")
    _result("save_screenshot()", path.exists(), str(path))
    return ok


def test_preprocessing():
    """Test 2: Preprocessing pipeline runs without errors."""
    print("\n[Test 2] Preprocessing pipeline")
    img = capture_screen()
    processed = preprocess_for_ocr(img)
    ok = processed is not None
    _result("preprocess_for_ocr()", ok, f"Output size: {processed.width}x{processed.height}")
    save_screenshot(processed, "test_preprocessed")
    return ok


def test_get_all_text():
    """Test 3: Can Tesseract extract any text from the current screen?"""
    print("\n[Test 3] Full screen OCR — get all text positions")
    print("         (Make sure your desktop/taskbar is visible)")
    time.sleep(1)

    result = get_all_text_positions(min_confidence=40.0)
    count = len(result.matches)
    ok = count > 0
    _result(
        "get_all_text_positions()",
        ok,
        f"Found {count} words. Sample: {[m.text for m in result.matches[:10]]}"
    )
    return ok


def test_find_desktop_text():
    """
    Test 4: Find a piece of text visible on the current screen.
    Edit TARGET to match something actually visible (e.g. taskbar clock, desktop icon).
    """
    print("\n[Test 4] find_text_on_screen()")
    TARGET = "Recycle"   # Change to any text visible on YOUR screen right now

    match = find_text_on_screen(TARGET)
    ok = match is not None
    if ok:
        _result(
            f"find_text_on_screen({TARGET!r})",
            True,
            f"Found at center ({match.center_x}, {match.center_y}), conf={match.confidence:.1f}%",
        )
    else:
        _result(
            f"find_text_on_screen({TARGET!r})",
            False,
            f"Not found. Try changing TARGET to text visible on your screen.",
        )
    return ok


def test_verify_text():
    """Test 5: Boolean verify function."""
    print("\n[Test 5] verify_text_exists()")
    TARGET = "Recycle"  # Same as Test 4 — change to match visible text

    found = verify_text_exists(TARGET)
    _result(f"verify_text_exists({TARGET!r})", found)
    return found


def test_multiword_search():
    """Test 6: Multi-word phrase search (bounding box merge)."""
    print("\n[Test 6] Multi-word search")
    TARGET = "Recycle Bin"  # Change to a 2+ word phrase visible on your screen

    match = find_text_on_screen(TARGET)
    ok = match is not None
    if ok:
        _result(
            f"Multi-word: {TARGET!r}",
            True,
            f"Center=({match.center_x},{match.center_y}), W={match.width}, H={match.height}",
        )
    else:
        _result(f"Multi-word: {TARGET!r}", False, "Not found. Adjust TARGET.")
    return ok


def test_dpi_scaling():
    """
    Test 7: Verify that bounding box coordinates match actual screen positions.
    After running, open the saved screenshot and check whether the green box
    (drawn at the returned coordinates) lines up with the detected text.
    """
    print("\n[Test 7] DPI / coordinate accuracy check")
    try:
        from PIL import ImageDraw
    except ImportError:
        print("         Skipped: Pillow ImageDraw not available")
        return True

    result = get_all_text_positions(min_confidence=60.0)
    raw = capture_screen()
    draw = ImageDraw.Draw(raw)

    for m in result.matches[:20]:   # draw boxes for first 20 words
        draw.rectangle(
            [m.screen_x, m.screen_y, m.screen_x + m.width, m.screen_y + m.height],
            outline="lime",
            width=2,
        )
        draw.text((m.screen_x, m.screen_y - 12), m.text, fill="lime")

    path = save_screenshot(raw, "test_dpi_bounding_boxes")
    _result(
        "Bounding box overlay saved",
        path.exists(),
        f"Open {path} and verify green boxes align with text",
    )
    return path.exists()


def test_wait_for_text():
    """Test 8: wait_for_text() with a short timeout on visible text."""
    print("\n[Test 8] wait_for_text() — polling")
    TARGET = "Recycle"   # Must be visible within 5 seconds

    match = wait_for_text(TARGET, timeout=5.0, poll_interval=1.0)
    ok = match is not None
    _result(f"wait_for_text({TARGET!r}, timeout=5s)", ok)
    return ok


# ── Run all tests ─────────────────────────────────────────────────────────────

def run_all():
    print("=" * 60)
    print("  Morning Check — Phase 1 OCR Core Test Suite")
    print("=" * 60)

    tests = [
        test_screen_capture,
        test_preprocessing,
        test_get_all_text,
        test_find_desktop_text,
        test_verify_text,
        test_multiword_search,
        test_dpi_scaling,
        test_wait_for_text,
    ]

    passed = 0
    for t in tests:
        try:
            if t():
                passed += 1
        except Exception as e:
            print(f"  ❌ EXCEPTION in {t.__name__}: {e}")

    total = len(tests)
    print(f"\n{'='*60}")
    print(f"  Results: {passed}/{total} tests passed")
    if passed == total:
        print("  ✅ Phase 1 OCR Core is ready — proceed to Phase 2")
    else:
        print("  ⚠️  Fix failing tests before proceeding")
        print("  Hint: Check output/screenshots/ for bounding box images")
    print("=" * 60)


if __name__ == "__main__":
    run_all()