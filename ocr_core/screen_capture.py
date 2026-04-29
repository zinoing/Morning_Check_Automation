"""
screen_capture.py
-----------------
Phase 1 - Step 1.2 / 1.3
Handles full screen capture using mss and image preprocessing
to maximise Tesseract accuracy on Windows UI.
"""

import os
import time
from datetime import datetime
from pathlib import Path

try:
    import mss
    import mss.tools
except ImportError:
    raise ImportError("mss not installed. Run: pip install mss")

try:
    from PIL import Image, ImageEnhance, ImageFilter
except ImportError:
    raise ImportError("Pillow not installed. Run: pip install Pillow")


# ── Output folder ────────────────────────────────────────────────────────────
SCREENSHOT_DIR = Path(__file__).parent.parent / "output" / "screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


# ── Capture ──────────────────────────────────────────────────────────────────

def get_main_monitor() -> dict:
    """
    Find and return the main display monitor dict.
    The main display in Windows always has left=0, top=0.
    Works correctly regardless of dual/multi-monitor setup.
    """
    with mss.mss() as sct:
        for m in sct.monitors[1:]:
            if m["left"] == 0 and m["top"] == 0:
                return m
        return sct.monitors[1]  # fallback


def capture_screen() -> Image.Image:
    """
    Capture the main display and return a PIL Image.
    Auto-detects the main display regardless of dual-monitor arrangement.

    Returns:
        PIL Image in RGB mode.
    """
    with mss.mss() as sct:
        monitor = get_main_monitor()
        raw = sct.grab(monitor)
        img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
    return img


def capture_region(left: int, top: int, width: int, height: int) -> Image.Image:
    """
    Capture a specific region of the screen.

    Args:
        left, top: Top-left corner coordinates.
        width, height: Size of the region.

    Returns:
        PIL Image in RGB mode.
    """
    with mss.mss() as sct:
        region = {"left": left, "top": top, "width": width, "height": height}
        raw = sct.grab(region)
        img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
    return img


def save_screenshot(img: Image.Image, label: str = "screenshot") -> Path:
    """
    Save a PIL Image to the screenshots output folder with a timestamp.

    Args:
        img: PIL Image to save.
        label: Descriptive label embedded in the filename.

    Returns:
        Path to the saved file.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{label}_{timestamp}.png"
    path = SCREENSHOT_DIR / filename
    img.save(str(path))
    return path


# ── Preprocessing ─────────────────────────────────────────────────────────────

def preprocess_for_ocr(
    img: Image.Image,
    scale: float = 2.0,
    contrast: float = 2.0,
    sharpen: bool = True,
    binarize: bool = True,
    binarize_threshold: int = 150,
) -> Image.Image:
    """
    Preprocess a PIL Image to improve Tesseract accuracy on Windows UI.

    Pipeline:
        1. Upscale  - Tesseract works best at 300 DPI equivalent; scaling up
                      compensates for 96 DPI screens and Windows DPI scaling.
        2. Grayscale
        3. Contrast boost
        4. Sharpen  - helps with subpixel-rendered fonts
        5. Binarize - convert to pure black/white (best for Tesseract)

    Args:
        img: Source PIL Image (RGB).
        scale: Upscale multiplier. 2.0 is safe for most screens.
        contrast: Contrast enhancement factor. 2.0 works well for UI.
        sharpen: Whether to apply a sharpening filter.
        binarize: Whether to convert to pure black/white.
        binarize_threshold: Pixels below this value become black (0–255).

    Returns:
        Preprocessed PIL Image ready for Tesseract.
    """
    # 1. Upscale using high-quality resampling
    new_w = int(img.width * scale)
    new_h = int(img.height * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)

    # 2. Grayscale
    img = img.convert("L")

    # 3. Contrast boost
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(contrast)

    # 4. Sharpen
    if sharpen:
        img = img.filter(ImageFilter.SHARPEN)

    # 5. Binarize (threshold → pure black or white)
    if binarize:
        img = img.point(lambda p: 0 if p < binarize_threshold else 255, "1")
        img = img.convert("L")  # back to grayscale so Tesseract accepts it

    return img


def capture_and_preprocess(
    region: dict = None,
    **preprocess_kwargs,
) -> tuple[Image.Image, Image.Image]:
    """
    Convenience function: capture the main display (or a region) and return
    both the raw image and the preprocessed image ready for Tesseract.

    Args:
        region: Optional dict with keys left/top/width/height.
        **preprocess_kwargs: Passed through to preprocess_for_ocr().

    Returns:
        Tuple of (raw_image, preprocessed_image).
    """
    if region:
        raw = capture_region(**region)
    else:
        raw = capture_screen()

    processed = preprocess_for_ocr(raw, **preprocess_kwargs)
    return raw, processed