"""
test_action_engine.py
---------------------
Phase 2 test suite.
Validates every action type works on your Windows environment.

IMPORTANT: This test moves your mouse and types text.
           Do not touch the keyboard or mouse while it runs.
           Move mouse to TOP-LEFT corner of screen to abort (pyautogui failsafe).

Usage:
    cd tests
    python test_action_engine.py
"""

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ocr_core.logger import RunSession, Status
from ocr_core.ocr_engine import get_all_text_positions
from action_engine import (
    open_app,
    win_run,
    maximize_window,
    ocr_click,
    type_text,
    key_press,
    verify_text,
    wait,
    take_screenshot,
)


def _header(title: str):
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")


def run_all():
    print("=" * 60)
    print("  Morning Check — Phase 2 Action Engine Test Suite")
    print("=" * 60)
    print("  ⚠️  Mouse and keyboard will be controlled automatically.")
    print("  ⚠️  Move mouse to TOP-LEFT corner to abort at any time.")
    print("\n  Starting in 3 seconds...")
    time.sleep(3)

    session = RunSession("TEST_SERVER")
    passed = 0
    total  = 0

    # ── Test 1: Screenshot ────────────────────────────────────────────────────
    _header("Test 1: take_screenshot()")
    total += 1
    r = take_screenshot(session, "phase2_test_start")
    if r.status.value == "PASS":
        print(f"  ✅ PASS — saved: {r.screenshot_path}")
        passed += 1
    else:
        print(f"  ❌ FAIL — {r.message}")

    # ── Test 2: Wait ──────────────────────────────────────────────────────────
    _header("Test 2: wait()")
    total += 1
    r = wait(session, 1.0, reason="test pause")
    if r.status.value == "PASS":
        print(f"  ✅ PASS — {r.message}")
        passed += 1
    else:
        print(f"  ❌ FAIL — {r.message}")

    # ── Test 3: Win+R → open Notepad ─────────────────────────────────────────
    _header("Test 3: win_run() → Notepad")
    total += 1
    r = win_run(session, "notepad", wait_after=2.0)
    if r.status.value == "PASS":
        print(f"  ✅ PASS — {r.message}")
        passed += 1
    else:
        print(f"  ❌ FAIL — {r.message}")

    # ── Test 4: Maximize window ───────────────────────────────────────────────
    _header("Test 4: maximize_window()")
    total += 1
    r = maximize_window(session)
    if r.status.value == "PASS":
        print(f"  ✅ PASS — {r.message}")
        passed += 1
    else:
        print(f"  ❌ FAIL — {r.message}")

    # ── Test 5: verify_text — text that should exist in Notepad ──────────────
    _header("Test 5: verify_text() — confirm Notepad is open")
    total += 1
    # "Notepad" appears in the title bar
    r = verify_text(session, "Notepad", pass_message="Notepad confirmed open", timeout=5.0)
    if r.status.value == "PASS":
        print(f"  ✅ PASS — {r.message}")
        passed += 1
    else:
        print(f"  ❌ FAIL — {r.message}")
        print("  📋 OCR DEBUG — all text found on screen right now:")
        ocr_result = get_all_text_positions(min_confidence=40.0)
        words = [m.text for m in ocr_result.matches if m.text.strip()]
        print(f"     {words}")

    # ── Test 6: type_text ─────────────────────────────────────────────────────
    _header("Test 6: type_text() — type into Notepad")
    total += 1
    # Click center of screen first so Notepad is focused
    import pyautogui
    pyautogui.click(pyautogui.size()[0] // 2, pyautogui.size()[1] // 2)
    time.sleep(0.3)
    r = type_text(session, "Morning Check Phase 2 Test")
    if r.status.value == "PASS":
        print(f"  ✅ PASS — {r.message}")
        passed += 1
    else:
        print(f"  ❌ FAIL — {r.message}")

    # ── Test 7: verify typed text appears on screen ───────────────────────────
    _header("Test 7: verify_text() — confirm typed text is visible")
    total += 1
    r = verify_text(session, "Morning Check", timeout=5.0)
    if r.status.value == "PASS":
        print(f"  ✅ PASS — {r.message}")
        passed += 1
    else:
        print(f"  ❌ FAIL — {r.message}")

    # ── Test 8: key_press — select all and delete ─────────────────────────────
    _header("Test 8: key_press() — Ctrl+A then Delete")
    total += 1
    r1 = key_press(session, "ctrl+a")
    r2 = key_press(session, "delete")
    if r1.status.value == "PASS" and r2.status.value == "PASS":
        print(f"  ✅ PASS — Ctrl+A and Delete sent")
        passed += 1
    else:
        print(f"  ❌ FAIL")

    # ── Test 9: ocr_click — click the Format menu in Notepad ─────────────────
    _header("Test 9: ocr_click() — click Notepad menu item")
    total += 1
    # "File" menu is always visible in Notepad title bar
    r = ocr_click(session, "File", timeout=5.0, on_fail="warn")
    if r.status.value == "PASS":
        print(f"  ✅ PASS — {r.message}")
        passed += 1
    else:
        print(f"  ⚠️  WARN — {r.message} (may need to adjust OCR confidence)")

    # Close the menu if opened
    key_press(session, "escape")
    time.sleep(0.5)

    # ── Test 10: Close Notepad without saving ─────────────────────────────────
    _header("Test 10: Close Notepad (cleanup)")
    total += 1
    r = key_press(session, "alt+f4", wait_after=1.0)
    # "Don't Save" dialog may appear — press Tab to select Don't Save then Enter
    time.sleep(0.5)
    key_press(session, "tab")
    key_press(session, "enter")
    if r.status.value == "PASS":
        print(f"  ✅ PASS — Notepad closed")
        passed += 1
    else:
        print(f"  ❌ FAIL — {r.message}")

    # ── Final screenshot ──────────────────────────────────────────────────────
    take_screenshot(session, "phase2_test_end")

    # ── Summary ───────────────────────────────────────────────────────────────
    summary = session.summary()
    print(f"\n{'='*60}")
    print(f"  Results: {passed}/{total} tests passed")
    print(f"  Log saved to: output/logs/")
    print(f"  Screenshots: output/screenshots/")
    if passed == total:
        print("  ✅ Phase 2 Action Engine is ready — proceed to Phase 3")
    else:
        print("  ⚠️  Review failing tests before proceeding")
    print("=" * 60)


if __name__ == "__main__":
    run_all()