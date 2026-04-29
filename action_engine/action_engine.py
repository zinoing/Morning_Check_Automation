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

import pyautogui
import pyautogui as pag

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


def ocr_click(
    session: RunSession,
    find_text: str,
    offset_x: int = 0,
    offset_y: int = 0,
    wait_before: float = 0.5,
    wait_after: float = 0.5,
    timeout: float = 10.0,
    double_click: bool = False,
    on_fail: str = "warn",
) -> ActionResult:
    """
    Find text on screen via OCR and click it (or click with an offset).

    Args:
        find_text   : Text to locate on screen.
        offset_x    : Pixels to offset click from text center (e.g. 300 to
                      click the Status column to the right of a service name).
        offset_y    : Pixels to offset click vertically.
        wait_before : Seconds to wait before searching (let UI settle).
        wait_after  : Seconds to wait after clicking.
        timeout     : Max seconds to wait for text to appear.
        double_click: If True, double-click instead of single click.
        on_fail     : "stop" | "warn" | "skip"
    """
    description = f"OCR click: '{find_text}'"
    time.sleep(wait_before)

    match = wait_for_text(find_text, timeout=timeout)
    if not match:
        shot = _screenshot_on_action("ocr_click_not_found")
        return _log(
            session, "ocr_click", description, False,
            f"Text not found on screen: '{find_text}'", shot, on_fail,
        )

    x = match.center_x + offset_x
    y = match.center_y + offset_y

    try:
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
    except Exception as e:
        shot = _screenshot_on_action("ocr_click_error")
        return _log(session, "ocr_click", description, False, f"Click failed: {e}", shot, on_fail)


def ocr_click_and_type(
    session: RunSession,
    find_text: str,
    type_text: str,
    offset_x: int = 0,
    offset_y: int = 0,
    clear_first: bool = True,
    wait_after: float = 0.5,
    timeout: float = 10.0,
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
    """
    Type text into the currently focused window.
    Use after clicking a field manually or after ocr_click().
    """
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
            parts = keys.split("+")
            pag.hotkey(*parts)
        else:
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
) -> ActionResult:
    """
    Capture and save a named screenshot for the report.

    Args:
        label: Descriptive name embedded in the filename.
    """
    description = f"Screenshot: {label}"
    try:
        shot = _screenshot_on_action(label)
        return _log(session, "take_screenshot", description, True, f"Saved: {shot.name}", shot)
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