"""
action_engine.py
----------------
Phase 2 - Action Engine
Executes every action type needed across the 9 servers.

Each action:
  - Returns an ActionResult (success, message, screenshot_path)
  - Logs to the RunSession
  - Handles its own retry and error logic

Available actions:
  - open_app()         : launch .exe, .msc, .bat, URL
  - ocr_click()        : find text via OCR → click it
  - ocr_click_and_type(): find text via OCR → click → type
  - type_text()        : type into currently focused window
  - key_press()        : send keyboard shortcut
  - verify_text()      : OCR check → pass/fail logged
  - wait()             : pause N seconds
  - take_screenshot()  : save named screenshot
  - run_batch()        : execute .bat or .ps1
  - maximize_window()  : maximize the foreground window
  - win_run()          : open Win+R and run a command
"""

import sys
import time
import subprocess
import webbrowser
from pathlib import Path
from typing import Optional
import traceback
import pyperclip
import win32gui
import win32con

import ctypes
import pyautogui
import pyautogui as pag
import pygetwindow as gw

# ── Project path setup ────────────────────────────────────────────────────────
_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ocr_core.ocr_engine import find_text_on_screen, verify_text_exists, wait_for_text
from ocr_core.screen_capture import capture_screen, save_screenshot
from ocr_core.logger import RunSession, Status, ActionResult

# ── pyautogui safety settings ─────────────────────────────────────────────────
pag.FAILSAFE = True        # move mouse to top-left corner to abort
pag.PAUSE    = 0.3         # small pause between every pyautogui call

# ── Windows keybd_event API (bypasses SendInput limitations) ─────────────────
# pyautogui uses SendInput which can be blocked by UIPI or certain apps.
# keybd_event is a lower-level API that works more reliably for hotkeys.
_user32 = ctypes.windll.user32

# Virtual key codes
_VK = {
    "alt":     0x12,
    "ctrl":    0x11,
    "shift":   0x10,
    "win":     0x5B,
    "enter":   0x0D,
    "escape":  0x1B,
    "tab":     0x09,
    "delete":  0x2E,
    "f1":      0x70, "f2": 0x71, "f3": 0x72, "f4":  0x73,
    "f5":      0x74, "f6": 0x75, "f7": 0x76, "f8":  0x77,
    "f9":      0x78, "f10":0x79, "f11":0x7A, "f12": 0x7B,
    "up":      0x26, "down": 0x28, "left": 0x25, "right": 0x27,
    "home":    0x24, "end": 0x23, "pageup": 0x21, "pagedown": 0x22,
    "space":   0x20, "backspace": 0x08,
}

KEYEVENTF_KEYUP = 0x0002

def _vk(key: str) -> int:
    """Get virtual key code for a key name."""
    key = key.lower()
    if key in _VK:
        return _VK[key]
    # Single character keys: use VkKeyScan
    if len(key) == 1:
        return _user32.VkKeyScanW(ord(key)) & 0xFF
    raise ValueError(f"Unknown key: {key!r}")

def _kb_send(key: str, key_up: bool = False):
    """Send a single key event via keybd_event."""
    vk = _vk(key)
    flags = KEYEVENTF_KEYUP if key_up else 0
    _user32.keybd_event(vk, 0, flags, 0)

def _hotkey_api(*keys: str):
    """
    Press a hotkey combination using keybd_event Windows API.
    More reliable than pyautogui for system-level shortcuts like Alt+F4.
    """
    for k in keys:
        _kb_send(k, key_up=False)
    time.sleep(0.05)
    for k in reversed(keys):
        _kb_send(k, key_up=True)


# ═════════════════════════════════════════════════════════════════════════════
# Internal helpers
# ═════════════════════════════════════════════════════════════════════════════

def _screenshot_on_action(label: str) -> Optional[Path]:
    """Take a screenshot and return its path."""
    img = capture_screen()
    return save_screenshot(img, label)


def _log(
    session: RunSession,
    action: str,
    description: str,
    success: bool,
    message: str,
    screenshot: Optional[Path] = None,
    on_fail: str = "warn",
) -> ActionResult:
    """
    Log an action result.
    on_fail: "warn" | "stop" | "skip"
    """
    if success:
        status = Status.PASS
    else:
        status = Status.FAIL if on_fail == "stop" else Status.WARN
    return session.log(action, description, status, message, screenshot)


# ═════════════════════════════════════════════════════════════════════════════
# Actions
# ═════════════════════════════════════════════════════════════════════════════

def open_app(
    session: RunSession,
    target: str,
    wait_after: float = 2.0,
    on_fail: str = "stop",
) -> ActionResult:
    """
    Open an application, .msc console, batch file, or URL.

    Args:
        target : Path to .exe/.bat/.msc, or a URL starting with http.
        wait_after : Seconds to wait after launching (for app to load).
        on_fail    : "stop" | "warn" | "skip"

    Examples:
        open_app(session, "services.msc")
        open_app(session, r"C:\\tools\\check.bat")
        open_app(session, "https://intranet.company.com")
    """
    description = f"Open: {target}"
    try:
        if target.startswith("http://") or target.startswith("https://"):
            webbrowser.open(target)
        elif target.endswith(".msc"):
            subprocess.Popen(["mmc", target], shell=False)
        elif target.endswith(".bat") or target.endswith(".cmd"):
            subprocess.Popen(["cmd", "/c", target], shell=False)
        elif target.endswith(".ps1"):
            subprocess.Popen(
                ["powershell", "-ExecutionPolicy", "Bypass", "-File", target],
                shell=False,
            )
        else:
            subprocess.Popen([target], shell=True)

        time.sleep(wait_after)
        shot = _screenshot_on_action(f"open_app_{Path(target).stem}")
        return _log(session, "open_app", description, True, f"Launched: {target}", shot, on_fail)

    except Exception as e:
        shot = _screenshot_on_action("open_app_error")
        return _log(session, "open_app", description, False, f"Failed to open: {e}", shot, on_fail)


def win_run(
    session: RunSession,
    command: str,
    wait_after: float = 2.0,
    on_fail: str = "stop",
) -> ActionResult:
    """
    Open Win+R dialog and run a command.
    Useful for: services.msc, devmgmt.msc, eventvwr.msc, etc.

    Args:
        command   : Command to type into the Run dialog.
        wait_after: Seconds to wait for the window to open.
    """
    description = f"Win+R: {command}"
    try:
        pag.hotkey("win", "r")
        time.sleep(0.8)
        pag.typewrite(command, interval=0.05)
        pag.press("enter")
        time.sleep(wait_after)
        shot = _screenshot_on_action(f"win_run_{command.replace('.', '_')}")
        return _log(session, "win_run", description, True, f"Ran: {command}", shot, on_fail)
    except Exception as e:
        shot = _screenshot_on_action("win_run_error")
        return _log(session, "win_run", description, False, f"Failed: {e}", shot, on_fail)


def maximize_window(
    session: RunSession,
    wait_after: float = 0.5,
) -> ActionResult:
    """
    Maximize the currently focused window.
    Always call this after opening an app to ensure full-screen OCR accuracy.
    """
    description = "Maximize foreground window"
    try:
        pag.hotkey("win", "up")   # Windows snap maximise
        time.sleep(wait_after)
        return _log(session, "maximize_window", description, True, "Window maximized")
    except Exception as e:
        return _log(session, "maximize_window", description, False, f"Failed: {e}", on_fail="warn")


def close_window(
    session: RunSession,
    wait_after: float = 1.0,
) -> ActionResult:
    """
    Close the currently active window using Alt+F4 via Windows keybd_event API.
    keybd_event bypasses pyautogui SendInput limitations and works reliably
    for system-level shortcuts that SendInput cannot deliver.
    """
    description = "Close active window"
    try:
        _hotkey_api("alt", "f4")
        time.sleep(wait_after)
        return _log(session, "close_window", description, True, "Window closed")
    except Exception as e:
        return _log(session, "close_window", description, False, f"Failed: {e}", on_fail="warn")

def type_secure(text: str):
    """보안 다이얼로그에서도 동작하는 타이핑 — 클립보드 경유"""
    pyperclip.copy(text)
    time.sleep(0.3)
    _hotkey_api("ctrl", "v")  # 이미 있는 keybd_event 기반 함수
    time.sleep(0.3)
    pyperclip.copy("")  # 보안을 위해 클립보드 즉시 비우기

def focus_window(
    session: RunSession,
    title_contains: str,
    wait_after: float = 0.5,
    on_fail: str = "warn",
) -> ActionResult:
    """
    타이틀에 특정 문자열이 포함된 창으로 포커스 이동.
    예: focus_window(session, "53.91.155.167")
    """
    description = f"Focus window: '{title_contains}'"
    try:
        windows = gw.getWindowsWithTitle(title_contains)
        if not windows:
            return _log(session, "focus_window", description, False,
                       f"Window not found: '{title_contains}'", on_fail=on_fail)
        
        win = windows[0]
        win.restore()          # 최소화 상태면 복원
        win.activate()         # 포커스 이동
        time.sleep(wait_after)
        return _log(session, "focus_window", description, True,
                   f"Focused: '{win.title}'")
    except Exception as e:
        return _log(session, "focus_window", description, False,
                   f"Failed: {e}", on_fail=on_fail)

def ocr_click(
    session: RunSession,
    find_text: str,
    offset_x: int = 0,
    offset_y: int = 0,
    wait_before: float = 0.5,
    wait_after: float = 0.5,
    timeout: float = 10.0,
    double_click: bool = False,
    case_sensitive: bool = False,
    fuzzy_match: bool = True,
    on_fail: str = "warn",
) -> ActionResult:
    description = f"OCR click: '{find_text}'"
    time.sleep(wait_before)

    try:                                          # ← wait_for_text도 try 안으로
        match = wait_for_text(find_text, timeout=timeout, case_sensitive=case_sensitive, exact= not fuzzy_match,)
        if not match:
            shot = _screenshot_on_action("ocr_click_not_found")
            return _log(
                session, "ocr_click", description, False,
                f"Text not found: '{find_text}'", shot, on_fail,
            )

        x = match.center_x + offset_x
        y = match.center_y + offset_y

        if double_click:
            pag.doubleClick(x, y)
        else:
            pag.click(x, y)

        time.sleep(wait_after)
        shot = _screenshot_on_action(f"ocr_click_{find_text[:20].replace(' ', '_')}")
        return _log(
            session, "ocr_click", description, True,
            f"Clicked '{find_text}' at ({x}, {y})", shot, on_fail,
        )

    except Exception:                             # ← str(e) 대신 전체 traceback
        shot = _screenshot_on_action("ocr_click_error")
        return _log(
            session, "ocr_click", description, False,
            traceback.format_exc(),               # ← 핵심 변경
            shot, on_fail,
        )


def ocr_click_and_type(
    session: RunSession,
    find_text: str,
    type_text: str,
    offset_x: int = 0,
    offset_y: int = 0,
    clear_first: bool = True,
    wait_after: float = 0.5,
    timeout: float = 10.0,
    case_sensitive: bool = False,
    fuzzy_match: bool = True,
    on_fail: str = "warn",
) -> ActionResult:
    """
    Find a field via OCR, click it, then type text into it.
    Useful for: login forms, search boxes, input fields.

    Args:
        find_text  : Label or placeholder text near the input field.
        type_text  : Text to type after clicking.
        clear_first: If True, Ctrl+A → Delete before typing (clears existing text).
        offset_x   : Click offset from found text (to hit the input box itself).
    """
    description = f"OCR click+type: '{find_text}' → '{type_text}'"

    # First click the field
    click_result = ocr_click(
        session, find_text,
        offset_x=offset_x, offset_y=offset_y,
        timeout=timeout, on_fail=on_fail,
        case_sensitive=case_sensitive, fuzzy_match=fuzzy_match,
    )
    if click_result.status == Status.FAIL:
        return click_result

    try:
        if clear_first:
            pag.hotkey("ctrl", "a")
            pag.press("delete")
            time.sleep(0.2)

        pag.typewrite(type_text, interval=0.05)
        time.sleep(wait_after)
        shot = _screenshot_on_action(f"type_{find_text[:15].replace(' ', '_')}")
        return _log(
            session, "ocr_click_and_type", description, True,
            f"Typed into '{find_text}'", shot, on_fail,
        )
    except Exception as e:
        shot = _screenshot_on_action("type_error")
        return _log(session, "ocr_click_and_type", description, False, f"Type failed: {e}", shot, on_fail)

def type_text(
    session: RunSession,
    text: str,
    interval: float = 0.05,
    wait_after: float = 0.3,
    on_fail: str = "warn",
) -> ActionResult:
    description = f"Type: '{text}'"
    try:
        pag.typewrite(text, interval=interval)
        time.sleep(wait_after)
        return _log(session, "type_text", description, True, f"Typed: '{text}'")
    except Exception as e:
        return _log(session, "type_text", description, False, f"Failed: {e}", on_fail=on_fail)

def key_press(
    session: RunSession,
    keys: str,
    wait_after: float = 0.5,
    on_fail: str = "warn",
) -> ActionResult:
    """
    Press a key or keyboard shortcut.

    Args:
        keys: Single key ("enter", "tab", "escape") or
              hotkey combo ("ctrl+a", "alt+f4", "win+r").

    Examples:
        key_press(session, "enter")
        key_press(session, "ctrl+a")
        key_press(session, "alt+f4")
    """
    description = f"Key press: {keys}"
    try:
        if "+" in keys:
            # Use keybd_event API for combos — more reliable than pyautogui
            # SendInput for system shortcuts (Alt+F4, Win+R, Ctrl+A, etc.)
            parts = keys.split("+")
            _hotkey_api(*parts)
        else:
            # Single keys: pyautogui is fine
            pag.press(keys)

        time.sleep(wait_after)
        return _log(session, "key_press", description, True, f"Pressed: {keys}")
    except Exception as e:
        return _log(session, "key_press", description, False, f"Failed: {e}", on_fail=on_fail)


def verify_text(
    session: RunSession,
    find_text: str,
    pass_message: str = "",
    fail_message: str = "",
    wait_before: float = 0.5,
    timeout: float = 10.0,
    on_fail: str = "warn",
) -> ActionResult:
    """
    OCR check — verify that text exists on screen. Logs PASS or FAIL/WARN.
    Core function for morning checks (e.g. confirm service is "Running").

    Args:
        find_text    : Text to look for on screen.
        pass_message : Custom message on success.
        fail_message : Custom message on failure.
        timeout      : Max seconds to wait for text to appear.
        on_fail      : "warn" (yellow) | "stop" (red, halts run) | "skip"
    """
    description = f"Verify: '{find_text}'"
    time.sleep(wait_before)

    match = wait_for_text(find_text, timeout=timeout)
    shot = _screenshot_on_action(f"verify_{find_text[:20].replace(' ', '_')}")

    if match:
        msg = pass_message or f"'{find_text}' confirmed on screen"
        return _log(session, "verify_text", description, True, msg, shot, on_fail)
    else:
        msg = fail_message or f"'{find_text}' NOT found on screen"
        return _log(session, "verify_text", description, False, msg, shot, on_fail)


def wait(
    session: RunSession,
    seconds: float,
    reason: str = "",
) -> ActionResult:
    """
    Pause execution for N seconds.
    Use after opening slow-loading apps or triggering batch jobs.
    """
    description = f"Wait {seconds}s{' — ' + reason if reason else ''}"
    time.sleep(seconds)
    return _log(session, "wait", description, True, f"Waited {seconds}s")


def take_screenshot(
    session: RunSession,
    label: str,
    save_dir: str = "",
) -> ActionResult:
    """
    Capture the full screen and save as a PNG.

    Args:
        label   : Name embedded in the filename.
        save_dir: Directory to save into. Defaults to output/screenshots.
    """
    description = f"Screenshot: {label}"
    try:
        img = capture_screen()
        timestamp = __import__("datetime").datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{label}_{timestamp}.png"
        if save_dir:
            out = Path(save_dir) / filename
            out.parent.mkdir(parents=True, exist_ok=True)
        else:
            from ocr_core.screen_capture import SCREENSHOT_DIR
            out = SCREENSHOT_DIR / filename
        img.save(str(out))
        return _log(session, "take_screenshot", description, True, f"Saved: {out.name}", out)
    except Exception as e:
        return _log(session, "take_screenshot", description, False, f"Failed: {e}", on_fail="warn")


def run_batch(
    session: RunSession,
    path: str,
    wait_after: float = 3.0,
    on_fail: str = "warn",
) -> ActionResult:
    """
    Execute a .bat or .ps1 file and wait for it to complete.

    Args:
        path      : Full path to the batch or PowerShell file.
        wait_after: Seconds to wait after execution starts.
    """
    description = f"Run batch: {path}"
    try:
        p = Path(path)
        if not p.exists():
            return _log(session, "run_batch", description, False, f"File not found: {path}", on_fail=on_fail)

        if path.endswith(".ps1"):
            subprocess.Popen(["powershell", "-ExecutionPolicy", "Bypass", "-File", path])
        else:
            subprocess.Popen(["cmd", "/c", path])

        time.sleep(wait_after)
        shot = _screenshot_on_action(f"batch_{p.stem}")
        return _log(session, "run_batch", description, True, f"Executed: {p.name}", shot, on_fail)
    except Exception as e:
        shot = _screenshot_on_action("batch_error")
        return _log(session, "run_batch", description, False, f"Failed: {e}", shot, on_fail)