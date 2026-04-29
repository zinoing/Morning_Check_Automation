"""
runner.py
Execute a step sequence in a background thread so the GUI stays responsive.
Calls back into the GUI thread via tk.after() for status updates.
"""
import sys
import threading
import time
from pathlib import Path
from typing import Callable

# ── Project path setup ────────────────────────────────────────────────────────
if getattr(sys, "frozen", False):
    _ROOT = Path(sys.executable).parent
else:
    _ROOT = Path(__file__).parent.parent

if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from gui.project_io import resolve_template


# ── Callbacks type hints ──────────────────────────────────────────────────────
# on_step_start(step_index: int)
# on_step_done(step_index: int, status: str, message: str)
# on_run_done(summary: dict)
# on_error(msg: str)


class SequenceRunner:
    """
    Runs the action sequence defined by a list of step config dicts.
    Fires GUI callbacks for live status updates.
    """

    def __init__(
        self,
        steps: list[dict],
        project_name: str,
        on_step_start: Callable,
        on_step_done: Callable,
        on_run_done: Callable,
        on_error: Callable,
        tk_after: Callable,   # root.after(0, fn)
    ):
        self.steps = steps
        self.project_name = project_name
        self.on_step_start = on_step_start
        self.on_step_done = on_step_done
        self.on_run_done = on_run_done
        self.on_error = on_error
        self._after = tk_after
        self._stop_flag = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self):
        self._stop_flag.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_flag.set()

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _run(self):
        try:
            from ocr_core.logger import RunSession
            from action_engine.action_engine import (
                open_app, win_run, maximize_window, ocr_click,
                ocr_click_and_type, type_text, key_press,
                verify_text, wait, take_screenshot, run_batch,
            )
            import types
            ae = types.SimpleNamespace(
                open_app=open_app, win_run=win_run,
                maximize_window=maximize_window, ocr_click=ocr_click,
                ocr_click_and_type=ocr_click_and_type, type_text=type_text,
                key_press=key_press, verify_text=verify_text,
                wait=wait, take_screenshot=take_screenshot,
                run_batch=run_batch,
            )
        except Exception as e:
            msg = f"Import error: {e}"
            self._after(0, lambda m=msg: self.on_error(m))
            return

        session = RunSession(self.project_name)
        start_ts = time.time()
        results = []

        for idx, step in enumerate(self.steps):
            if self._stop_flag.is_set():
                break

            self._after(0, lambda i=idx: self.on_step_start(i))

            try:
                result = self._execute_step(session, ae, step)
                status = result.status.value if result else "SKIP"
                message = result.message if result else "Skipped"
            except Exception as e:
                status = "FAIL"
                message = str(e)

            results.append({"index": idx, "status": status, "message": message})
            self._after(0, lambda i=idx, s=status, m=message: self.on_step_done(i, s, m))

        duration = round(time.time() - start_ts, 1)
        counts = {"PASS": 0, "FAIL": 0, "WARN": 0, "SKIP": 0}
        for r in results:
            key = r["status"] if r["status"] in counts else "SKIP"
            counts[key] += 1

        summary = {
            "total": len(self.steps),
            "duration": duration,
            "pass": counts["PASS"],
            "fail": counts["FAIL"],
            "warn": counts["WARN"],
            "skip": counts["SKIP"],
        }
        self._after(0, lambda s=summary: self.on_run_done(s))

    def _execute_step(self, session, ae, step: dict):
        action = step.get("action", "")

        if action == "capture":
            return ae.take_screenshot(session, step.get("label", "capture"))

        elif action == "click":
            return ae.ocr_click(
                session,
                find_text=step.get("find_text", ""),
                offset_x=int(step.get("offset_x", 0)),
                offset_y=int(step.get("offset_y", 0)),
                timeout=float(step.get("timeout", 10.0)),
                double_click=bool(step.get("double_click", False)),
                on_fail=step.get("on_fail", "warn"),
            )

        elif action == "click_type":
            return ae.ocr_click_and_type(
                session,
                find_text=step.get("find_text", ""),
                type_text=resolve_template(step.get("type_text", "")),
                offset_x=int(step.get("offset_x", 0)),
                clear_first=bool(step.get("clear_first", True)),
                timeout=float(step.get("timeout", 10.0)),
                on_fail=step.get("on_fail", "warn"),
            )

        elif action == "typing":
            text = resolve_template(step.get("value", ""))
            speed_ms = int(step.get("speed_ms", 50))
            interval = speed_ms / 1000.0
            result = ae.type_text(session, text, interval=interval)
            if step.get("press_enter", False):
                ae.key_press(session, "enter")
            return result

        elif action == "key_press":
            return ae.key_press(
                session,
                keys=step.get("keys", ""),
                wait_after=float(step.get("wait_after", 0.5)),
            )

        elif action == "verify":
            return ae.verify_text(
                session,
                find_text=step.get("find_text", ""),
                pass_message=step.get("pass_message", ""),
                fail_message=step.get("fail_message", ""),
                timeout=float(step.get("timeout", 10.0)),
                on_fail=step.get("on_fail", "warn"),
            )

        elif action == "open_app":
            return ae.open_app(
                session,
                target=step.get("target", ""),
                wait_after=float(step.get("wait_after", 2.0)),
                on_fail=step.get("on_fail", "stop"),
            )

        elif action == "win_run":
            return ae.win_run(
                session,
                command=step.get("command", ""),
                wait_after=float(step.get("wait_after", 2.0)),
            )

        elif action == "maximize":
            return ae.maximize_window(session)

        elif action == "wait":
            return ae.wait(
                session,
                seconds=float(step.get("seconds", 1.0)),
                reason=step.get("reason", ""),
            )

        elif action == "run_batch":
            return ae.run_batch(
                session,
                path=step.get("path", ""),
                wait_after=float(step.get("wait_after", 3.0)),
                on_fail=step.get("on_fail", "warn"),
            )

        else:
            raise ValueError(f"Unknown action: {action}")
