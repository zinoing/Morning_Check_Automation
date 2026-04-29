# Morning Check Automation

---

## Project Structure

```
morning_check/
├── ocr_core/
│   ├── screen_capture.py     ← capture + preprocess screenshots
│   ├── ocr_engine.py         ← Tesseract: find text, verify, get all positions
│   ├── logger.py             ← structured logging + run session tracking
│   └── __init__.py
├── action_engine/
│   ├── action_engine.py      ← all action types (click, type, verify, etc.)
│   └── __init__.py
├── tests/
│   ├── test_ocr_core.py      ← Phase 1 validation
│   ├── test_action_engine.py ← Phase 2 validation
│   └── diagnose_tesseract.py ← Tesseract path diagnostic
├── configs/                  ← server YAML files (Phase 3)
├── output/
│   ├── screenshots/          ← auto-created
│   ├── reports/              ← auto-created (Phase 4)
│   └── logs/                 ← auto-created
└── requirements.txt
```

---

## Phase Roadmap

| Phase | Status | Description |
|---|---|---|
| **Phase 1** | ✅ Complete | OCR Core (capture, preprocess, find text) |
| **Phase 2** | ✅ Complete | Action Engine (click, type, open app, verify) |
| Phase 3 | ⬜ Pending | Config System (YAML per server) |
| Phase 4 | ⬜ Pending | Report Builder (Excel output) |
| Phase 5 | ⬜ Pending | PyInstaller packaging |

---

## Setup

### Step 1 — Install Tesseract (Windows)

1. Download from: https://github.com/UB-Mannheim/tesseract/wiki
2. Your confirmed install path: `C:\Users\CHOJIN\AppData\Local\Programs\Tesseract-OCR\`
3. If your server UI includes Korean text, during install tick:
   **Additional language data → Korean**

### Step 2 — Install Python dependencies

```bash
pip install -r requirements.txt
```

### Step 3 — Validate Phase 1

```bash
cd tests
python test_ocr_core.py
```

### Step 4 — Validate Phase 2

```bash
cd tests
python test_action_engine.py
```

⚠️ Mouse and keyboard will be controlled automatically during this test.
Move mouse to the **top-left corner** of the screen to abort at any time.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `TesseractNotFoundError` | Check path in `ocr_engine.py` line 39 |
| Words found but boxes misaligned | Try `scale=1.5` instead of `2.0` |
| Low word count on screen | Lower `min_confidence` to `30.0` |
| Korean characters not detected | Install kor language pack, set `TESS_LANG = "eng+kor"` in `ocr_engine.py` |
| `mss` import error | `pip install mss` |
| Status always showing FAIL | Use `r.status.value == "PASS"` not `r.status == Status.PASS` |

---

## Phase 2 — Action Reference

All actions take `session` as the first argument (a `RunSession` object).
Every action returns an `ActionResult` with `.status`, `.message`, and `.screenshot_path`.

---

### `open_app` — Launch any application

```python
open_app(session, "services.msc")                      # Windows service manager
open_app(session, r"C:\tools\check.bat")               # batch file
open_app(session, "https://intranet.company.com")      # URL in browser
open_app(session, r"C:\Program Files\app\app.exe")     # any executable
```

| Parameter | Default | Description |
|---|---|---|
| `target` | required | Path to app/file or URL |
| `wait_after` | `2.0` | Seconds to wait after launching |
| `on_fail` | `"stop"` | `"stop"` / `"warn"` / `"skip"` |

---

### `win_run` — Open Win+R and run a command

```python
win_run(session, "services.msc")    # service manager
win_run(session, "eventvwr.msc")    # event viewer
win_run(session, "devmgmt.msc")     # device manager
win_run(session, "notepad")         # any run command
```

| Parameter | Default | Description |
|---|---|---|
| `command` | required | Command to type into Run dialog |
| `wait_after` | `2.0` | Seconds to wait for window to open |
| `on_fail` | `"stop"` | `"stop"` / `"warn"` / `"skip"` |

---

### `maximize_window` — Maximize the foreground window

```python
maximize_window(session)
```

Always call this right after `open_app` or `win_run` to ensure OCR gets a
full-size clean screen to read.

---

### `ocr_click` — Find text on screen and click it

```python
ocr_click(session, "Start")                           # click button labeled Start
ocr_click(session, "IBM WebSphere", offset_x=300)     # click 300px right of text
ocr_click(session, "Login", double_click=True)         # double click
ocr_click(session, "Submit", timeout=15.0)             # wait up to 15s for text
```

| Parameter | Default | Description |
|---|---|---|
| `find_text` | required | Text to locate on screen |
| `offset_x` | `0` | Pixels to offset click horizontally (useful for table columns) |
| `offset_y` | `0` | Pixels to offset click vertically |
| `wait_before` | `0.5` | Seconds to wait before searching |
| `wait_after` | `0.5` | Seconds to wait after clicking |
| `timeout` | `10.0` | Max seconds to wait for text to appear |
| `double_click` | `False` | Double-click instead of single click |
| `on_fail` | `"warn"` | `"stop"` / `"warn"` / `"skip"` |

---

### `ocr_click_and_type` — Find a field, click it, then type

```python
ocr_click_and_type(session, "Username", "admin")
ocr_click_and_type(session, "Search", "monthly_report", offset_x=150)
ocr_click_and_type(session, "Password", "mypassword", clear_first=True)
```

| Parameter | Default | Description |
|---|---|---|
| `find_text` | required | Label or placeholder text near the input field |
| `type_text` | required | Text to type after clicking |
| `offset_x` | `0` | Offset to hit the input box (when label is beside the field) |
| `clear_first` | `True` | Ctrl+A → Delete before typing |
| `wait_after` | `0.5` | Seconds to wait after typing |
| `timeout` | `10.0` | Max seconds to wait for field to appear |
| `on_fail` | `"warn"` | `"stop"` / `"warn"` / `"skip"` |

---

### `type_text` — Type into currently focused window

```python
type_text(session, "monthly_report")
type_text(session, "admin@company.com")
```

| Parameter | Default | Description |
|---|---|---|
| `text` | required | Text to type |
| `interval` | `0.05` | Seconds between each keystroke |
| `wait_after` | `0.3` | Seconds to wait after typing |

---

### `key_press` — Press a key or keyboard shortcut

```python
key_press(session, "enter")       # Enter
key_press(session, "tab")         # Tab
key_press(session, "escape")      # Escape
key_press(session, "ctrl+a")      # Select all
key_press(session, "ctrl+c")      # Copy
key_press(session, "ctrl+v")      # Paste
key_press(session, "alt+f4")      # Close window
key_press(session, "win+up")      # Maximize window
```

| Parameter | Default | Description |
|---|---|---|
| `keys` | required | Single key or `+`-separated combo |
| `wait_after` | `0.5` | Seconds to wait after pressing |

---

### `verify_text` — Check if text is visible → logs PASS or WARN/FAIL

```python
verify_text(session, "Running",
    pass_message="Service is running",
    fail_message="Service is DOWN",
    on_fail="warn")      # yellow warning, run continues

verify_text(session, "Connected",
    on_fail="stop")      # red failure, run halts immediately
```

| Parameter | Default | Description |
|---|---|---|
| `find_text` | required | Text to look for on screen |
| `pass_message` | `""` | Custom log message on success |
| `fail_message` | `""` | Custom log message on failure |
| `wait_before` | `0.5` | Seconds to wait before checking |
| `timeout` | `10.0` | Max seconds to wait for text to appear |
| `on_fail` | `"warn"` | `"stop"` / `"warn"` / `"skip"` |

**`on_fail` values:**

| Value | Log colour | Effect |
|---|---|---|
| `"warn"` | 🟡 Yellow | Logs warning, run continues |
| `"stop"` | 🔴 Red | Logs failure, run halts |
| `"skip"` | ⚪ Grey | Silent, run continues |

---

### `wait` — Pause execution for N seconds

```python
wait(session, 2.0)
wait(session, 5.0, reason="Waiting for batch job to complete")
```

| Parameter | Default | Description |
|---|---|---|
| `seconds` | required | How long to pause |
| `reason` | `""` | Description shown in log |

---

### `take_screenshot` — Save a named screenshot for the report

```python
take_screenshot(session, "services_status")
take_screenshot(session, "after_batch_run")
take_screenshot(session, "login_confirmed")
```

Files are saved to `output/screenshots/` with a timestamp appended automatically.

---

### `run_batch` — Execute a .bat or .ps1 file

```python
run_batch(session, r"C:\scripts\morning_check.bat", wait_after=5.0)
run_batch(session, r"C:\scripts\check_db.ps1",      wait_after=10.0)
```

| Parameter | Default | Description |
|---|---|---|
| `path` | required | Full path to the .bat or .ps1 file |
| `wait_after` | `3.0` | Seconds to wait after execution starts |
| `on_fail` | `"warn"` | `"stop"` / `"warn"` / `"skip"` |

---

## Example — Full Server Check Sequence

```python
# Open service manager
win_run(session, "services.msc", wait_after=3.0)
maximize_window(session)

# Verify a service is running
verify_text(session, "IBM WebSphere Application Server",
    pass_message="WebSphere found in services list")
ocr_click(session, "IBM WebSphere Application Server", offset_x=300)
verify_text(session, "Running",
    pass_message="WebSphere is Running",
    fail_message="WebSphere is NOT running — manual check needed",
    on_fail="warn")
take_screenshot(session, "websphere_status")
key_press(session, "alt+f4")

# Open intranet page
open_app(session, "https://intranet.company.com", wait_after=3.0)
maximize_window(session)
ocr_click_and_type(session, "Username", "admin")
key_press(session, "tab")
ocr_click_and_type(session, "Password", "mypassword")
key_press(session, "enter")
wait(session, 2.0, reason="Wait for page to load")
verify_text(session, "Dashboard",
    pass_message="Login successful",
    fail_message="Login failed",
    on_fail="stop")
take_screenshot(session, "intranet_login")
```