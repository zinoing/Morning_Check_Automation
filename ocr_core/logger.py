"""
logger.py
---------
Structured logging for the morning check automation.
Produces both console output (live feedback) and a log file per run.
Each action result is stored and later used by the report builder.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


# ── Log output folder ─────────────────────────────────────────────────────────
LOG_DIR = Path(__file__).parent.parent / "output" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


# ── Status enum ───────────────────────────────────────────────────────────────

class Status(Enum):
    PASS    = "PASS"
    FAIL    = "FAIL"
    WARN    = "WARN"
    INFO    = "INFO"
    SKIP    = "SKIP"


# ── Action result dataclass ───────────────────────────────────────────────────

@dataclass
class ActionResult:
    """Stores the outcome of a single automation step."""
    step_index: int
    action: str
    description: str
    status: Status
    message: str
    screenshot_path: Optional[Path] = None
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%H:%M:%S"))

    def to_dict(self) -> dict:
        return {
            "step": self.step_index,
            "action": self.action,
            "description": self.description,
            "status": self.status.value,
            "message": self.message,
            "screenshot": str(self.screenshot_path) if self.screenshot_path else "",
            "timestamp": self.timestamp,
        }


# ── Console formatter with colours ────────────────────────────────────────────

class ColouredFormatter(logging.Formatter):
    COLOURS = {
        "DEBUG":    "\033[37m",   # white
        "INFO":     "\033[36m",   # cyan
        "WARNING":  "\033[33m",   # yellow
        "ERROR":    "\033[31m",   # red
        "CRITICAL": "\033[41m",   # red background
    }
    RESET = "\033[0m"
    STATUS_COLOURS = {
        "PASS": "\033[32m",   # green
        "FAIL": "\033[31m",   # red
        "WARN": "\033[33m",   # yellow
        "SKIP": "\033[37m",   # grey
        "INFO": "\033[36m",   # cyan
    }

    def format(self, record: logging.LogRecord) -> str:
        colour = self.COLOURS.get(record.levelname, "")
        msg = super().format(record)
        # Highlight status tags like [PASS] [FAIL]
        for tag, col in self.STATUS_COLOURS.items():
            msg = msg.replace(f"[{tag}]", f"{col}[{tag}]{self.RESET}")
        return f"{colour}{msg}{self.RESET}"


# ── Logger setup ──────────────────────────────────────────────────────────────

def setup_logger(server_name: str) -> logging.Logger:
    """
    Set up and return a logger that writes to both console and a log file.

    Args:
        server_name: Used in the log filename.

    Returns:
        Configured logging.Logger instance.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOG_DIR / f"{server_name}_{timestamp}.log"

    logger = logging.getLogger(f"morning_check.{server_name}")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(ColouredFormatter(
        fmt="%(asctime)s  %(message)s",
        datefmt="%H:%M:%S",
    ))

    # File handler (plain text, no colour codes)
    fh = logging.FileHandler(str(log_file), encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        fmt="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%H:%M:%S",
    ))

    logger.addHandler(ch)
    logger.addHandler(fh)
    return logger


# ── Run session collector ─────────────────────────────────────────────────────

class RunSession:
    """
    Tracks all action results for a single server run.
    Used by the report builder in Phase 4.
    """

    def __init__(self, server_name: str):
        self.server_name = server_name
        self.start_time = datetime.now()
        self.results: list[ActionResult] = []
        self.logger = setup_logger(server_name)
        self._step = 0

        self.logger.info(f"{'='*60}")
        self.logger.info(f"  Morning Check Started — {server_name}")
        self.logger.info(f"  {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"{'='*60}")

    def log(self, action, description, status, message, screenshot_path=None) -> ActionResult:
        self._step += 1
        result = ActionResult(
            step_index=self._step,
            action=action,
            description=description,
            status=status,
            message=message,
            screenshot_path=screenshot_path,
        )
        self.results.append(result)

        tag = f"[{status.value}]"
        header = f"Step {self._step:02d} {tag:8s} {action:25s} {description}"
        self.logger.info(header)

        if message:
            for line in message.splitlines():
                self.logger.info(f"           ↳ {line}")

        if screenshot_path:
            self.logger.debug(f"            {screenshot_path}")

        return result

    def summary(self) -> dict:
        """Return a summary dict of the run for the report builder."""
        counts = {"PASS": 0, "FAIL": 0, "WARN": 0, "INFO": 0, "SKIP": 0}
        for r in self.results:
            key = r.status.value if hasattr(r.status, "value") else str(r.status)
            counts[key] = counts.get(key, 0) + 1
        duration = (datetime.now() - self.start_time).seconds

        self.logger.info(f"{'='*60}")
        self.logger.info(
            f"  Run complete in {duration}s — "
            f"PASS:{counts['PASS']}  "
            f"FAIL:{counts['FAIL']}  "
            f"WARN:{counts['WARN']}  "
            f"SKIP:{counts['SKIP']}"
        )
        self.logger.info(f"{'='*60}")

        return {
            "server_name": self.server_name,
            "start_time": self.start_time.isoformat(),
            "duration_seconds": duration,
            "total_steps": self._step,
            "pass": counts['PASS'],
            "fail": counts['FAIL'],
            "warn": counts['WARN'],
            "skip": counts['SKIP'],
            "results": [r.to_dict() for r in self.results],
        }