"""
ocr_core — Phase 1 OCR engine package.
Import from here for clean access across the project.
"""
from .screen_capture import capture_screen, capture_region, save_screenshot, preprocess_for_ocr, capture_and_preprocess
from .ocr_engine import get_all_text_positions, find_text_on_screen, find_all_occurrences, verify_text_exists, wait_for_text, TextMatch, OCRResult
from .logger import RunSession, Status, ActionResult

__all__ = [
    "capture_screen", "capture_region", "save_screenshot",
    "preprocess_for_ocr", "capture_and_preprocess",
    "get_all_text_positions", "find_text_on_screen",
    "find_all_occurrences", "verify_text_exists", "wait_for_text",
    "TextMatch", "OCRResult",
    "RunSession", "Status", "ActionResult",
]