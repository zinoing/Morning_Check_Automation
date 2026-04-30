"""
ocr_engine.py
-------------
Phase 1 - Steps 1.4 / 1.5 / 1.6
Core OCR functions using Tesseract:
  - find_text_on_screen()     → locate text, return screen coordinates
  - verify_text_exists()      → True/False check
  - get_all_text_positions()  → full text map of the screen
"""

import os
import re
import time
import json
from pathlib import Path
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    import pytesseract
    from pytesseract import Output
except ImportError:
    raise ImportError("pytesseract not installed. Run: pip install pytesseract")

try:
    from PIL import Image
except ImportError:
    raise ImportError("Pillow not installed. Run: pip install Pillow")

import sys as _sys
from pathlib import Path as _Path
_root = str(_Path(__file__).parent.parent)
if _root not in _sys.path:
    _sys.path.insert(0, _root)

from ocr_core.screen_capture import capture_and_preprocess, capture_screen, preprocess_for_ocr


# ── Tesseract path (bundled alongside .exe or system install) ─────────────────
# When packaged with PyInstaller, tesseract.exe sits next to the .exe.
# During development, point to your local Tesseract install.
_SETTINGS_PATH = Path(__file__).parent.parent / "configs" / "settings.json"
with open(_SETTINGS_PATH, encoding="utf-8") as _f:
    _settings = json.load(_f)
pytesseract.pytesseract.tesseract_cmd = _settings.get(
    "tesseract_path"
)


# ── Tesseract config ──────────────────────────────────────────────────────────
# PSM 6 = assume a single uniform block of text (best for full-screen UI)
# PSM 3 = fully automatic page segmentation (use for complex layouts)
TESS_CONFIG_DEFAULT = "--psm 6 --oem 3"
TESS_CONFIG_SPARSE  = "--psm 11 --oem 3"   # sparse text; good for buttons/icons
TESS_LANG           = "eng"                 # change to "eng+kor" for Korean UI


# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class TextMatch:
    """Represents a single OCR text match with its screen position."""
    text: str
    screen_x: int       # left edge on screen (already scaled back)
    screen_y: int       # top edge on screen
    width: int
    height: int
    confidence: float

    @property
    def center_x(self) -> int:
        return self.screen_x + self.width // 2

    @property
    def center_y(self) -> int:
        return self.screen_y + self.height // 2

    def __repr__(self):
        return (
            f"TextMatch(text={self.text!r}, "
            f"center=({self.center_x}, {self.center_y}), "
            f"conf={self.confidence:.1f}%)"
        )


@dataclass
class OCRResult:
    """Full OCR result from one screen capture."""
    matches: list[TextMatch] = field(default_factory=list)
    raw_text: str = ""
    screenshot_path: Optional[Path] = None

    def all_text(self) -> str:
        """Return all detected text joined into one string."""
        return " ".join(m.text for m in self.matches if m.text.strip())


# ── Internal helpers ──────────────────────────────────────────────────────────

def _run_tesseract(img: Image.Image, config: str = TESS_CONFIG_DEFAULT) -> dict:
    """Run Tesseract on a PIL Image and return the full data dict."""
    return pytesseract.image_to_data(
        img,
        lang=TESS_LANG,
        config=config,
        output_type=Output.DICT,
    )


def _data_to_matches(
    data: dict,
    scale: float,
    min_confidence: float,
    region_offset: tuple[int, int] = (0, 0),
) -> list[TextMatch]:
    """
    Convert Tesseract data dict to a list of TextMatch objects.
    Scales coordinates back to real screen pixels.
    """
    matches = []
    n = len(data["text"])
    for i in range(n):
        conf = float(data["conf"][i])
        text = data["text"][i].strip()
        if not text or conf < min_confidence:
            continue

        # Scale bounding box back to original screen coordinates
        x = int(data["left"][i]   / scale) + region_offset[0]
        y = int(data["top"][i]    / scale) + region_offset[1]
        w = int(data["width"][i]  / scale)
        h = int(data["height"][i] / scale)

        matches.append(TextMatch(
            text=text,
            screen_x=x,
            screen_y=y,
            width=w,
            height=h,
            confidence=conf,
        ))
    return matches


# ── Public API ────────────────────────────────────────────────────────────────

def get_all_text_positions(
    scale: float = 2.0,
    min_confidence: float = 50.0,
    config: str = TESS_CONFIG_DEFAULT,
    region: dict = None,
) -> OCRResult:
    """
    Capture the screen (or a region), run OCR, and return every detected
    word with its screen position.

    Args:
        scale: Upscale factor for preprocessing (2.0 recommended).
        min_confidence: Minimum Tesseract confidence % to include a word.
        config: Tesseract PSM/OEM config string.
        region: Optional dict with left/top/width/height for partial capture.

    Returns:
        OCRResult with all detected TextMatch objects.
    """
    raw, processed = capture_and_preprocess(
        region=region,
        scale=scale,
    )
    region_offset = (region["left"], region["top"]) if region else (0, 0)

    data = _run_tesseract(processed, config)
    matches = _data_to_matches(data, scale, min_confidence, region_offset)
    raw_text = pytesseract.image_to_string(processed, lang=TESS_LANG, config=config)

    return OCRResult(matches=matches, raw_text=raw_text)


def find_text_on_screen(
    target: str,
    exact: bool = False,
    case_sensitive: bool = False,
    scale: float = 2.0,
    min_confidence: float = 50.0,
    region: dict = None,
) -> Optional[TextMatch]:
    """
    Find the first occurrence of target text on screen.

    Supports both exact word matching and substring/fuzzy matching.
    For multi-word targets (e.g. "IBM WebSphere"), scans adjacent words
    and merges their bounding boxes.

    Args:
        target: Text string to search for.
        exact: If True, requires whole-word exact match.
        case_sensitive: Default False (recommended for UI text).
        scale: Preprocessing scale factor.
        min_confidence: Minimum confidence threshold.
        region: Optional screen region to limit search.

    Returns:
        TextMatch with screen coordinates, or None if not found.
    """
    result = get_all_text_positions(scale=scale, min_confidence=min_confidence, region=region)

    compare = (lambda a, b: a == b) if case_sensitive else (lambda a, b: a.lower() == b.lower())
    contains = (lambda a, b: b in a) if case_sensitive else (lambda a, b: b.lower() in a.lower())

    words = target.split()

    if len(words) == 1:
        # Single word search
        for m in result.matches:
            if exact:
                if compare(m.text, target):
                    return m
            else:
                if contains(m.text, target):
                    return m
        return None

    # Multi-word: find sequence of adjacent matches
    texts = [m.text for m in result.matches]
    for i in range(len(result.matches) - len(words) + 1):
        window = result.matches[i : i + len(words)]
        window_texts = [m.text for m in window]
        # Check if all words match in sequence
        if all(
            compare(wt, ww) if exact else contains(wt, ww)
            for wt, ww in zip(window_texts, words)
        ):
            # Merge bounding boxes
            x = min(m.screen_x for m in window)
            y = min(m.screen_y for m in window)
            right  = max(m.screen_x + m.width  for m in window)
            bottom = max(m.screen_y + m.height for m in window)
            avg_conf = sum(m.confidence for m in window) / len(window)

            return TextMatch(
                text=" ".join(wt for wt in window_texts),
                screen_x=x,
                screen_y=y,
                width=right - x,
                height=bottom - y,
                confidence=avg_conf,
            )
    return None


def find_all_occurrences(
    target: str,
    case_sensitive: bool = False,
    scale: float = 2.0,
    min_confidence: float = 50.0,
    region: dict = None,
) -> list[TextMatch]:
    """
    Find ALL occurrences of a text string on screen (e.g. multiple rows
    with the same status label).

    Returns:
        List of TextMatch objects (empty list if none found).
    """
    result = get_all_text_positions(scale=scale, min_confidence=min_confidence, region=region)
    found = []
    for m in result.matches:
        if case_sensitive:
            if target in m.text:
                found.append(m)
        else:
            if target.lower() in m.text.lower():
                found.append(m)
    return found


def verify_text_exists(
    target: str,
    scale: float = 2.0,
    min_confidence: float = 50.0,
    region: dict = None,
) -> bool:
    """
    Check whether a specific text string is visible on screen.

    Args:
        target: Text to look for.
        scale, min_confidence, region: Same as find_text_on_screen().

    Returns:
        True if found, False otherwise.
    """
    return find_text_on_screen(
        target,
        scale=scale,
        min_confidence=min_confidence,
        region=region,
    ) is not None


def wait_for_text(
    target: str,
    timeout: float = 15.0,
    poll_interval: float = 1.5,
    min_confidence: float = 50.0,
    case_sensitive: bool = False,
    exact: bool = False,
) -> Optional[TextMatch]:
    """
    Poll the screen until target text appears or timeout is reached.

    Args:
        target: Text expected to appear.
        timeout: Max seconds to wait.
        poll_interval: Seconds between each check.
        case_sensitive: If True, match exact case.
        exact: If True, require whole-word match (no partial/fuzzy).

    Returns:
        TextMatch if found within timeout, None if timed out.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        match = find_text_on_screen(
            target,
            exact=exact,
            case_sensitive=case_sensitive,
            min_confidence=min_confidence,
        )
        if match:
            return match
        time.sleep(poll_interval)
    return None