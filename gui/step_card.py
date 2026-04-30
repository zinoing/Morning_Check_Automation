"""
step_card.py
Each action step is represented by a StepCard frame.
The card dynamically rebuilds its parameter area when the action type changes.
"""
import tkinter as tk
from tkinter import ttk, filedialog
from pathlib import Path

try:
    from PIL import Image, ImageTk
    PIL_OK = True
except ImportError:
    PIL_OK = False

from gui import styles as S

# ── Action catalogue ──────────────────────────────────────────────────────────
ACTION_LABELS = [
    "Capture",
    "Click",
    "Click + Type",
    "Typing",
    "Key Press",
    "Verify Text",
    "Open App",
    "Win+R",
    "Wait",
    "Run Batch",
    "Maximize",
    "Close Active Window",
    "Focus Window",
]

# action label → internal action key
ACTION_KEY = {
    "Capture":      "capture",
    "Click":        "click",
    "Click + Type": "click_type",
    "Typing":       "typing",
    "Key Press":    "key_press",
    "Verify Text":  "verify",
    "Open App":     "open_app",
    "Win+R":        "win_run",
    "Wait":         "wait",
    "Run Batch":    "run_batch",
    "Maximize":             "maximize",
    "Close Active Window":  "close_window",
    "Focus Window": "focus_window"
}

CONTENT_TYPES = {
    "capture":    ["Image"],
    "click":      ["Text"],
    "click_type": ["Text"],
    "typing":     ["Text"],
    "key_press":  ["Text"],
    "verify":     ["Text"],
    "open_app":   ["Text", "URL"],
    "win_run":    ["Text"],
    "wait":       ["—"],
    "run_batch":  ["File"],
    "maximize":      ["—"],
    "close_window":  ["—"],
    "focus_window":  ["Text"],
}

ON_FAIL_OPTIONS = ["warn", "stop", "skip"]


def _entry(parent, textvariable=None, placeholder="", width=None, **kw):
    """Styled single-line entry."""
    e = tk.Entry(
        parent,
        textvariable=textvariable,
        font=S.F_BASE,
        bg=S.BG_INPUT,
        fg=S.TEXT_PRIMARY,
        relief=tk.FLAT,
        highlightthickness=1,
        highlightbackground=S.BORDER,
        highlightcolor=S.ACCENT,
        insertbackground=S.TEXT_PRIMARY,
        **kw,
    )
    if width:
        e.config(width=width)
    if placeholder and textvariable is None:
        e.insert(0, placeholder)
        e.config(fg=S.TEXT_MUTED)

        def _on_focus_in(ev):
            if e.get() == placeholder:
                e.delete(0, tk.END)
                e.config(fg=S.TEXT_PRIMARY)

        def _on_focus_out(ev):
            if not e.get():
                e.insert(0, placeholder)
                e.config(fg=S.TEXT_MUTED)

        e.bind("<FocusIn>", _on_focus_in)
        e.bind("<FocusOut>", _on_focus_out)
    return e


def _label(parent, text, font=None, fg=None, **kw):
    return tk.Label(
        parent,
        text=text,
        font=font or S.F_SM,
        fg=fg or S.TEXT_SECONDARY,
        bg=S.BG_CARD,
        **kw,
    )


def _combo(parent, values, textvariable, width=18, **kw):
    style_name = "Card.TCombobox"
    c = ttk.Combobox(
        parent,
        values=values,
        textvariable=textvariable,
        state="readonly",
        width=width,
        font=S.F_BASE,
        style=style_name,
        **kw,
    )
    return c


def _check(parent, text, variable, **kw):
    return tk.Checkbutton(
        parent,
        text=text,
        variable=variable,
        font=S.F_SM,
        fg=S.TEXT_SECONDARY,
        bg=S.BG_CARD,
        activebackground=S.BG_CARD,
        selectcolor=S.BG_CARD,
        relief=tk.FLAT,
        bd=0,
        **kw,
    )


def _section_label(parent, text):
    return tk.Label(
        parent,
        text=text,
        font=(S.FONT, 9, "bold"),
        fg=S.TEXT_MUTED,
        bg=S.BG_CARD,
    )


# ═════════════════════════════════════════════════════════════════════════════
class StepCard(tk.Frame):
    """
    A single step card in the sequence editor.
    Exposes get_config() / load_config() for serialization.
    """

    def __init__(self, parent, index: int, on_delete, on_drag_start, **kw):
        super().__init__(
            parent,
            bg=S.BG_CARD,
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=S.BORDER,
            **kw,
        )
        self.index = index
        self.on_delete = on_delete
        self.on_drag_start = on_drag_start

        # state
        self._action_var = tk.StringVar(value="Capture")
        self._content_type_var = tk.StringVar(value="Image")
        self._status_color = S.BG_CARD   # updated during run

        self._param_widgets = {}   # key → widget for get_config
        self._param_frame: tk.Frame | None = None
        self._thumb_label: tk.Label | None = None
        self._thumb_img = None

        self._build_header()
        self._build_params()

        self._action_var.trace_add("write", self._on_action_change)

    # ── Header row ────────────────────────────────────────────────────────────

    def _build_header(self):
        hdr = tk.Frame(self, bg=S.BG_CARD)
        hdr.pack(fill=tk.X, padx=S.CARD_PAD, pady=(S.CARD_PAD, 6))

        # Drag handle
        self.drag_handle = tk.Label(
            hdr, text="⠿",
            font=(S.FONT, 14), fg=S.TEXT_MUTED, bg=S.BG_CARD,
            cursor="fleur", padx=2,
        )
        self.drag_handle.pack(side=tk.LEFT, padx=(0, 10))
        self.drag_handle.bind("<ButtonPress-1>", lambda e: self.on_drag_start(self, e))

        # Number badge
        self._badge = tk.Label(
            hdr,
            text=f"{self.index:02d}",
            font=(S.FONT, 10, "bold"),
            fg=S.TEXT_WHITE,
            bg=S.BG_SIDEBAR,
            width=3,
            relief=tk.FLAT,
            padx=4,
            pady=2,
        )
        self._badge.pack(side=tk.LEFT, padx=(0, 12))

        # ACTION TYPE
        col1 = tk.Frame(hdr, bg=S.BG_CARD)
        col1.pack(side=tk.LEFT, padx=(0, 16))
        _section_label(col1, "ACTION TYPE").pack(anchor="w")
        _combo(col1, ACTION_LABELS, self._action_var, width=16).pack(anchor="w", pady=(2, 0))

        # CONTENT TYPE
        col2 = tk.Frame(hdr, bg=S.BG_CARD)
        col2.pack(side=tk.LEFT)
        _section_label(col2, "CONTENT TYPE").pack(anchor="w")
        self._content_combo = _combo(col2, ["Image"], self._content_type_var, width=12)
        self._content_combo.pack(anchor="w", pady=(2, 0))

        # Right controls: status dot + delete
        ctrl = tk.Frame(hdr, bg=S.BG_CARD)
        ctrl.pack(side=tk.RIGHT)

        self._status_dot = tk.Label(ctrl, text="●", font=S.F_MD, fg=S.TEXT_MUTED, bg=S.BG_CARD)
        self._status_dot.pack(side=tk.LEFT, padx=(0, 6))

        tk.Button(
            ctrl, text="✕",
            font=S.F_SM, fg=S.TEXT_SECONDARY, bg=S.BG_CARD,
            relief=tk.FLAT, bd=0, cursor="hand2",
            activeforeground=S.RED, activebackground=S.BG_CARD,
            command=lambda: self.on_delete(self),
        ).pack(side=tk.LEFT, padx=1)

        # Divider
        sep = tk.Frame(self, height=1, bg=S.BORDER)
        sep.pack(fill=tk.X, padx=0)

    # ── Param area ────────────────────────────────────────────────────────────

    def _build_params(self):
        if self._param_frame:
            self._param_frame.destroy()

        action = ACTION_KEY.get(self._action_var.get(), "capture")

        # Update content type combo
        ct_options = CONTENT_TYPES.get(action, ["Text"])
        self._content_combo["values"] = ct_options
        if self._content_type_var.get() not in ct_options:
            self._content_type_var.set(ct_options[0])

        self._param_frame = tk.Frame(self, bg=S.BG_CARD, padx=S.CARD_PAD, pady=S.CARD_PAD)
        self._param_frame.pack(fill=tk.X)
        self._param_widgets = {}

        builder = {
            "capture":    self._params_capture,
            "click":      self._params_click,
            "click_type": self._params_click_type,
            "typing":     self._params_typing,
            "key_press":  self._params_key_press,
            "verify":     self._params_verify,
            "open_app":   self._params_open_app,
            "win_run":    self._params_win_run,
            "wait":       self._params_wait,
            "run_batch":  self._params_run_batch,
            "maximize":      self._params_maximize,
            "close_window":  self._params_close_window,
            "focus_window":  self._params_focus_window,
        }.get(action, self._params_maximize)

        builder()

    def _on_action_change(self, *_):
        self._build_params()

    # ── Parameter builders ────────────────────────────────────────────────────

    def _params_capture(self):
        f = self._param_frame

        _section_label(f, "SCREENSHOT NAME").pack(anchor="w")
        v = tk.StringVar()
        _entry(f, textvariable=v).pack(fill=tk.X, pady=(3, 10))
        self._param_widgets["label"] = v

        _section_label(f, "SAVE LOCATION").pack(anchor="w")
        loc_row = tk.Frame(f, bg=S.BG_CARD)
        loc_row.pack(fill=tk.X, pady=(3, 10))
        v2 = tk.StringVar()
        _entry(loc_row, textvariable=v2).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        tk.Button(
            loc_row, text="Browse",
            font=S.F_SM, fg=S.TEXT_SECONDARY, bg=S.BG_CARD,
            relief=tk.GROOVE, bd=1, padx=10, pady=3, cursor="hand2",
            activebackground="#F1F5F9",
            command=lambda: self._pick_save_dir(v2),
        ).pack(side=tk.LEFT)
        self._param_widgets["save_dir"] = v2

    def _pick_save_dir(self, var: tk.StringVar):
        path = filedialog.askdirectory(title="Select save location")
        if path:
            var.set(path)

    def _params_click(self):
        f = self._param_frame
        _section_label(f, "TARGET TEXT / SELECTOR").pack(anchor="w")
        v = tk.StringVar()
        _entry(f, textvariable=v).pack(fill=tk.X, pady=(3, 8))
        self._param_widgets["find_text"] = v

        chk_row = tk.Frame(f, bg=S.BG_CARD)
        chk_row.pack(anchor="w", pady=(0, 2))
        cs = tk.BooleanVar(value=False)
        fm = tk.BooleanVar(value=True)
        _check(chk_row, "Case Sensitive", cs).pack(side=tk.LEFT, padx=(0, 12))
        _check(chk_row, "Fuzzy Match", fm).pack(side=tk.LEFT)
        self._param_widgets["case_sensitive"] = cs
        self._param_widgets["fuzzy_match"] = fm

        desc_row = tk.Frame(f, bg=S.BG_CARD)
        desc_row.pack(anchor="w", pady=(0, 6))
        _label(desc_row, "Case Sensitive: 대소문자 구분   /   Fuzzy Match: 부분 일치 허용", fg=S.TEXT_MUTED, font=S.F_XS).pack(side=tk.LEFT)

        self._extra_row(f, [
            ("Offset X", "offset_x", "0", 6),
            ("Offset Y", "offset_y", "0", 6),
            ("Timeout (s)", "timeout", "10.0", 6),
        ])
        dc = tk.BooleanVar(value=False)
        _check(f, "Double Click", dc).pack(anchor="w", pady=(4, 0))
        self._param_widgets["double_click"] = dc
        self._on_fail_row(f)

    def _params_click_type(self):
        f = self._param_frame
        _section_label(f, "FIND TEXT (label / placeholder)").pack(anchor="w")
        v1 = tk.StringVar()
        _entry(f, textvariable=v1).pack(fill=tk.X, pady=(3, 8))
        self._param_widgets["find_text"] = v1

        _section_label(f, "TYPE TEXT").pack(anchor="w")
        v2 = tk.StringVar()
        _entry(f, textvariable=v2).pack(fill=tk.X, pady=(3, 8))
        self._param_widgets["type_text"] = v2

        chk_row2 = tk.Frame(f, bg=S.BG_CARD)
        chk_row2.pack(anchor="w", pady=(0, 2))
        cs2 = tk.BooleanVar(value=False)
        fm2 = tk.BooleanVar(value=True)
        _check(chk_row2, "Case Sensitive", cs2).pack(side=tk.LEFT, padx=(0, 12))
        _check(chk_row2, "Fuzzy Match", fm2).pack(side=tk.LEFT)
        self._param_widgets["case_sensitive"] = cs2
        self._param_widgets["fuzzy_match"] = fm2

        desc_row2 = tk.Frame(f, bg=S.BG_CARD)
        desc_row2.pack(anchor="w", pady=(0, 6))
        _label(desc_row2, "Case Sensitive: 대소문자 구분   /   Fuzzy Match: 부분 일치 허용", fg=S.TEXT_MUTED, font=S.F_XS).pack(side=tk.LEFT)

        self._extra_row(f, [
            ("Offset X", "offset_x", "0", 6),
            ("Timeout (s)", "timeout", "10.0", 6),
        ])
        cf = tk.BooleanVar(value=True)
        _check(f, "Clear field before typing", cf).pack(anchor="w", pady=(4, 0))
        self._param_widgets["clear_first"] = cf
        self._on_fail_row(f)

    def _params_typing(self):
        f = self._param_frame
        _section_label(f, "VALUE TO INPUT").pack(anchor="w")
        v = tk.StringVar()
        txt = tk.Text(
            f, height=3, font=S.F_BASE,
            bg=S.BG_INPUT, fg=S.TEXT_PRIMARY,
            relief=tk.FLAT, highlightthickness=1,
            highlightbackground=S.BORDER, highlightcolor=S.ACCENT,
            wrap=tk.WORD, insertbackground=S.TEXT_PRIMARY,
        )
        txt.pack(fill=tk.X, pady=(3, 8))
        self._param_widgets["value_widget"] = txt

        row = tk.Frame(f, bg=S.BG_CARD)
        row.pack(anchor="w")
        _section_label(row, "SPEED (MS)").pack(side=tk.LEFT, padx=(0, 6))
        spd = tk.StringVar(value="50")
        tk.Spinbox(
            row, from_=10, to=500, textvariable=spd, width=6,
            font=S.F_SM, relief=tk.FLAT,
            highlightthickness=1, highlightbackground=S.BORDER,
        ).pack(side=tk.LEFT, padx=(0, 16))
        self._param_widgets["speed_ms"] = spd

        pe = tk.BooleanVar(value=True)
        _check(row, "Press Enter after typing", pe).pack(side=tk.LEFT)
        self._param_widgets["press_enter"] = pe

    def _params_key_press(self):
        f = self._param_frame
        _section_label(f, "KEYS  (e.g. enter, ctrl+a, alt+f4)").pack(anchor="w")
        v = tk.StringVar()
        _entry(f, textvariable=v).pack(fill=tk.X, pady=(3, 8))
        self._param_widgets["keys"] = v

        self._extra_row(f, [("Wait after (s)", "wait_after", "0.5", 6)])

    def _params_verify(self):
        f = self._param_frame
        _section_label(f, "TEXT TO VERIFY").pack(anchor="w")
        v = tk.StringVar()
        _entry(f, textvariable=v).pack(fill=tk.X, pady=(3, 8))
        self._param_widgets["find_text"] = v

        _section_label(f, "PASS MESSAGE").pack(anchor="w")
        vp = tk.StringVar()
        _entry(f, textvariable=vp).pack(fill=tk.X, pady=(3, 8))
        self._param_widgets["pass_message"] = vp

        _section_label(f, "FAIL MESSAGE").pack(anchor="w")
        vf = tk.StringVar()
        _entry(f, textvariable=vf).pack(fill=tk.X, pady=(3, 8))
        self._param_widgets["fail_message"] = vf

        self._extra_row(f, [("Timeout (s)", "timeout", "10.0", 6)])
        self._on_fail_row(f)

    def _params_open_app(self):
        f = self._param_frame
        _section_label(f, "TARGET  (path, .msc, or URL)").pack(anchor="w")
        v = tk.StringVar()
        row = tk.Frame(f, bg=S.BG_CARD)
        row.pack(fill=tk.X, pady=(3, 8))
        _entry(row, textvariable=v).pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(
            row, text="Browse", font=S.F_SM, fg=S.TEXT_SECONDARY, bg=S.BG_CARD,
            relief=tk.GROOVE, bd=1, padx=8, cursor="hand2",
            command=lambda: v.set(filedialog.askopenfilename() or v.get()),
        ).pack(side=tk.LEFT, padx=(4, 0))
        self._param_widgets["target"] = v

        self._extra_row(f, [("Wait after (s)", "wait_after", "2.0", 6)])
        self._on_fail_row(f)

    def _params_win_run(self):
        f = self._param_frame
        _section_label(f, "COMMAND  (e.g. services.msc, notepad)").pack(anchor="w")
        v = tk.StringVar()
        _entry(f, textvariable=v).pack(fill=tk.X, pady=(3, 8))
        self._param_widgets["command"] = v
        self._extra_row(f, [("Wait after (s)", "wait_after", "2.0", 6)])

    def _params_wait(self):
        f = self._param_frame
        self._extra_row(f, [("Seconds", "seconds", "1.0", 8)])
        _section_label(f, "REASON (optional)").pack(anchor="w", pady=(8, 0))
        v = tk.StringVar()
        _entry(f, textvariable=v).pack(fill=tk.X, pady=(3, 0))
        self._param_widgets["reason"] = v

    def _params_run_batch(self):
        f = self._param_frame
        _section_label(f, "FILE PATH  (.bat or .ps1)").pack(anchor="w")
        v = tk.StringVar()
        row = tk.Frame(f, bg=S.BG_CARD)
        row.pack(fill=tk.X, pady=(3, 8))
        _entry(row, textvariable=v).pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(
            row, text="Browse", font=S.F_SM, fg=S.TEXT_SECONDARY, bg=S.BG_CARD,
            relief=tk.GROOVE, bd=1, padx=8, cursor="hand2",
            command=lambda: v.set(
                filedialog.askopenfilename(
                    filetypes=[("Batch/PS1", "*.bat *.cmd *.ps1")]
                ) or v.get()
            ),
        ).pack(side=tk.LEFT, padx=(4, 0))
        self._param_widgets["path"] = v
        self._extra_row(f, [("Wait after (s)", "wait_after", "3.0", 6)])
        self._on_fail_row(f)

    def _params_maximize(self):
        _label(self._param_frame, "No parameters required.", fg=S.TEXT_MUTED).pack(anchor="w")

    def _params_close_window(self):
        _label(self._param_frame, "Closes the active window with Alt+F4.", fg=S.TEXT_MUTED).pack(anchor="w")

    def _params_focus_window(self):
        f = self._param_frame
        _section_label(f, "WINDOW TITLE (contains)").pack(anchor="w")
        v = tk.StringVar()
        _entry(f, textvariable=v).pack(fill=tk.X, pady=(3, 8))
        self._param_widgets["title_contains"] = v
        self._extra_row(f, [("Wait after (s)", "wait_after", "0.5", 6)])
        self._on_fail_row(f)

    # ── Shared helpers ────────────────────────────────────────────────────────

    def _extra_row(self, parent, fields):
        """Render a row of small labeled entries: [(label, key, default, width), ...]"""
        row = tk.Frame(parent, bg=S.BG_CARD)
        row.pack(anchor="w", pady=(0, 4))
        for lbl, key, default, w in fields:
            cell = tk.Frame(row, bg=S.BG_CARD)
            cell.pack(side=tk.LEFT, padx=(0, 16))
            _section_label(cell, lbl).pack(anchor="w")
            v = tk.StringVar(value=default)
            _entry(cell, textvariable=v, width=w).pack(anchor="w", pady=(2, 0))
            self._param_widgets[key] = v

    def _on_fail_row(self, parent):
        row = tk.Frame(parent, bg=S.BG_CARD)
        row.pack(anchor="w", pady=(6, 0))
        _section_label(row, "ON FAIL").pack(side=tk.LEFT, padx=(0, 8))
        v = tk.StringVar(value="warn")
        _combo(row, ON_FAIL_OPTIONS, v, width=8).pack(side=tk.LEFT)
        self._param_widgets["on_fail"] = v

    # ── Public API ────────────────────────────────────────────────────────────

    def set_index(self, i: int):
        self.index = i
        self._badge.config(text=f"{i:02d}")

    def set_status(self, status: str):
        color = {
            "PASS": S.GREEN,
            "FAIL": S.RED,
            "WARN": S.AMBER,
            "running": S.ACCENT,
        }.get(status, S.TEXT_MUTED)
        self._status_dot.config(fg=color)

    def get_config(self) -> dict:
        action_label = self._action_var.get()
        action = ACTION_KEY.get(action_label, "capture")
        cfg = {"action": action}

        for key, widget in self._param_widgets.items():
            if key == "value_widget":
                cfg["value"] = widget.get("1.0", tk.END).strip()
            elif isinstance(widget, tk.BooleanVar):
                cfg[key] = widget.get()
            elif isinstance(widget, tk.StringVar):
                cfg[key] = widget.get()

        return cfg

    def load_config(self, cfg: dict):
        # Reverse-lookup action label
        action = cfg.get("action", "capture")
        label = next((k for k, v in ACTION_KEY.items() if v == action), "Capture")
        self._action_var.set(label)
        self._build_params()

        for key, widget in self._param_widgets.items():
            if key == "value_widget":
                widget.delete("1.0", tk.END)
                widget.insert("1.0", cfg.get("value", ""))
            elif isinstance(widget, tk.BooleanVar):
                widget.set(bool(cfg.get(key, False)))
            elif isinstance(widget, tk.StringVar):
                if key in cfg:
                    widget.set(str(cfg[key]))
