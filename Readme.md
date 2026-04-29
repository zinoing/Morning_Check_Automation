# Morning Check Automation
## Phase 1 — OCR Core Setup & Test

---

### Project Structure (Phase 1)

```
morning_check/
├── ocr_core/
│   ├── screen_capture.py   ← capture + preprocess screenshots
│   ├── ocr_engine.py       ← Tesseract: find text, verify, get all positions
│   └── logger.py           ← structured logging + run session tracking
├── tests/
│   └── test_ocr_core.py    ← run this to validate Phase 1
├── output/
│   ├── screenshots/        ← auto-created
│   ├── reports/            ← auto-created (Phase 4)
│   └── logs/               ← auto-created
├── configs/                ← server YAML files (Phase 3)
└── requirements.txt
```

---

### Step 1 — Install Tesseract (Windows)

1. Download from: https://github.com/UB-Mannheim/tesseract/wiki
2. Install to default path: `C:\Users\CHOJIN\AppData\Local\Programs\Tesseract-OCR`
C:\Users\CHOJIN\AppData\Local\Programs\Tesseract-OCR
3. If your server UI includes Korean text, during install tick:
   **Additional language data → Korean**

---

### Step 2 — Install Python dependencies

```bash
pip install -r requirements.txt
```

---

### Step 3 — Validate Phase 1

```bash
cd tests
python test_ocr_core.py
```

Expected output:
```
============================================================
  Morning Check — Phase 1 OCR Core Test Suite
============================================================

[Test 1] Screen capture
  ✅ PASS  capture_screen()       Captured 1920x1080 px
  ✅ PASS  save_screenshot()      ...

[Test 7] DPI / coordinate accuracy check
  ✅ PASS  Bounding box overlay saved
           Open output/screenshots/test_dpi_bounding_boxes_*.png
           and verify green boxes align with text
...
============================================================
  Results: 8/8 tests passed
  ✅ Phase 1 OCR Core is ready — proceed to Phase 2
============================================================
```

**Important:** Open the bounding box screenshot from Test 7 and visually
confirm the green boxes sit on top of the correct text. If they are
offset, adjust `scale` in the relevant function calls.

---

### Troubleshooting

| Problem | Fix |
|---|---|
| `TesseractNotFoundError` | Check Tesseract install path in `ocr_engine.py` |
| Words found but boxes misaligned | Try `scale=1.5` instead of `2.0` |
| Low word count on screen | Lower `min_confidence` to `30.0` |
| Korean characters not detected | Install kor language pack, set `TESS_LANG = "eng+kor"` in `ocr_engine.py` |
| `mss` import error | `pip install mss` |

---

### Phase Roadmap

| Phase | Status | Description |
|---|---|---|
| **Phase 1** | ✅ In Progress | OCR Core (capture, preprocess, find text) |
| Phase 2 | ⬜ Pending | Action Engine (click, type, open app) |
| Phase 3 | ⬜ Pending | Config System (YAML per server) |
| Phase 4 | ⬜ Pending | Report Builder (Excel output) |
| Phase 5 | ⬜ Pending | PyInstaller packaging |