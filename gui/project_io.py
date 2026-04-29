"""
project_io.py — Phase 3
Save and load project step sequences as YAML files in configs/.
Also handles persistent app settings (settings.json).
"""
import sys
import json
from pathlib import Path
from datetime import datetime

try:
    import yaml
except ImportError:
    yaml = None

# resolve configs/ both in dev and PyInstaller bundle
if getattr(sys, "frozen", False):
    _ROOT = Path(sys.executable).parent
else:
    _ROOT = Path(__file__).parent.parent

CONFIGS_DIR = _ROOT / "configs"
CONFIGS_DIR.mkdir(parents=True, exist_ok=True)


def save_project(name: str, steps: list[dict]) -> Path:
    """Serialize step list to YAML and return the saved path."""
    if yaml is None:
        raise RuntimeError("PyYAML not installed.")
    data = {
        "name": name,
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "steps": steps,
    }
    safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in name).strip()
    path = CONFIGS_DIR / f"{safe_name}.yaml"
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False)
    return path


def load_project(path: str | Path) -> dict:
    """Load a project YAML and return {"name": ..., "steps": [...]}."""
    if yaml is None:
        raise RuntimeError("PyYAML not installed.")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data


def list_projects() -> list[Path]:
    """Return all .yaml files in configs/ sorted by modification time (excludes settings.yaml)."""
    return sorted(
        [p for p in CONFIGS_DIR.glob("*.yaml") if p.stem != "settings"],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


# ── App settings (settings.json) ──────────────────────────────────────────────

_SETTINGS_PATH = CONFIGS_DIR / "settings.json"
_DEFAULTS = {
    "tesseract_path": r"C:\Program Files\Tesseract-OCR\tesseract.exe",
}


def load_settings() -> dict:
    """Load settings.json; return defaults for any missing keys."""
    settings = dict(_DEFAULTS)
    if _SETTINGS_PATH.exists():
        try:
            with open(_SETTINGS_PATH, "r", encoding="utf-8") as f:
                saved = json.load(f)
            settings.update(saved)
        except Exception:
            pass
    return settings


def save_settings(settings: dict) -> None:
    """Persist settings dict to settings.json."""
    current = load_settings()
    current.update(settings)
    with open(_SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(current, f, indent=2, ensure_ascii=False)


# ── Template variable substitution ────────────────────────────────────────────

def resolve_template(text: str) -> str:
    """Replace {{REPORT_DATE}} and similar tokens with runtime values."""
    now = datetime.now()
    replacements = {
        "{{REPORT_DATE}}": now.strftime("%Y-%m-%d"),
        "{{REPORT_TIME}}": now.strftime("%H:%M:%S"),
        "{{REPORT_DATETIME}}": now.strftime("%Y-%m-%d %H:%M:%S"),
        "{{YEAR}}": now.strftime("%Y"),
        "{{MONTH}}": now.strftime("%m"),
        "{{DAY}}": now.strftime("%d"),
    }
    for token, value in replacements.items():
        text = text.replace(token, value)
    return text
