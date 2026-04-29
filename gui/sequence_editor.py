"""
sequence_editor.py
The main "Projects" page — scrollable step cards + right-side flow summary panel.
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime

from gui import styles as S
from gui.step_card import StepCard
from gui.runner import SequenceRunner
from gui import project_io as pio


class SequenceEditor(tk.Frame):
    def __init__(self, parent, project_name_var: tk.StringVar, **kw):
        super().__init__(parent, bg=S.BG_MAIN, **kw)
        self._project_name_var = project_name_var
        self._steps: list[StepCard] = []
        self._runner: SequenceRunner | None = None
        self._run_start: datetime | None = None

        # drag state
        self._drag_card: StepCard | None = None
        self._drag_target: StepCard | None = None
        self._drop_indicator: tk.Frame | None = None

        self._build()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build(self):
        # Top title row
        title_bar = tk.Frame(self, bg=S.BG_MAIN)
        title_bar.pack(fill=tk.X, padx=28, pady=(24, 0))

        tk.Label(
            title_bar, text="Sequence Editor",
            font=S.F_2XL, fg=S.TEXT_PRIMARY, bg=S.BG_MAIN,
        ).pack(anchor="w")
        tk.Label(
            title_bar,
            text="Configure automated steps and logic flows for this project.",
            font=S.F_BASE, fg=S.TEXT_SECONDARY, bg=S.BG_MAIN,
        ).pack(anchor="w", pady=(2, 0))

        # Body: left (step list) + right (summary panel)
        body = tk.Frame(self, bg=S.BG_MAIN)
        body.pack(fill=tk.BOTH, expand=True, padx=28, pady=16)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, minsize=S.RIGHT_PANEL_W)
        body.rowconfigure(0, weight=1)

        # ── Left: scrollable step list ────────────────────────────────────────
        left = tk.Frame(body, bg=S.BG_MAIN)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 20))

        canvas = tk.Canvas(left, bg=S.BG_MAIN, highlightthickness=0)
        scrollbar = ttk.Scrollbar(left, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 20))

        self._steps_frame = tk.Frame(canvas, bg=S.BG_MAIN)
        self._canvas_window = canvas.create_window((0, 0), window=self._steps_frame, anchor="nw")

        def _on_frame_resize(e):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_resize(e):
            canvas.itemconfig(self._canvas_window, width=e.width)

        self._steps_frame.bind("<Configure>", _on_frame_resize)
        canvas.bind("<Configure>", _on_canvas_resize)
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(-1 * (e.delta // 120), "units"))

        self._canvas = canvas

        # "Add Action Item" button
        add_btn = tk.Button(
            self._steps_frame,
            text="+ Add Action Item",
            font=S.F_SM, fg=S.TEXT_SECONDARY, bg=S.BG_MAIN,
            relief=tk.FLAT, bd=0, cursor="hand2",
            activeforeground=S.ACCENT, activebackground=S.BG_MAIN,
            command=self._add_step,
        )
        self._add_btn = add_btn  # rendered in _rerender_steps

        # ── Right: summary panel ──────────────────────────────────────────────
        self._right = tk.Frame(body, bg=S.BG_MAIN)
        self._right.grid(row=0, column=1, sticky="ne")

        self._build_summary_panel()
        self._rerender_steps()   # show Add button even with 0 steps

    def _build_summary_panel(self):
        p = self._right

        # FLOW SUMMARY card
        card = tk.Frame(p, bg=S.BG_CARD, relief=tk.FLAT,
                        highlightthickness=1, highlightbackground=S.BORDER)
        card.pack(fill=tk.X, pady=(0, 12))

        tk.Label(card, text="FLOW SUMMARY", font=(S.FONT, 9, "bold"),
                 fg=S.TEXT_MUTED, bg=S.BG_CARD).pack(anchor="w", padx=14, pady=(12, 8))

        self._summary_rows = {}
        for key, label, default in [
            ("total",    "Total Steps",   "00"),
            ("duration", "Est. Run Time", "—"),
            ("rate",     "Success Rate",  "—"),
        ]:
            row = tk.Frame(card, bg=S.BG_CARD)
            row.pack(fill=tk.X, padx=14, pady=3)
            tk.Label(row, text=label, font=S.F_SM,
                     fg=S.TEXT_SECONDARY, bg=S.BG_CARD).pack(side=tk.LEFT)
            lbl = tk.Label(row, text=default, font=(S.FONT, 14, "bold"),
                           fg=S.TEXT_PRIMARY, bg=S.BG_CARD, width=10, anchor="e")
            lbl.pack(side=tk.RIGHT)
            self._summary_rows[key] = lbl

        tk.Frame(card, height=1, bg=S.BORDER).pack(fill=tk.X, padx=0, pady=(8, 0))

        # RECENT ACTIVITY
        tk.Label(card, text="RECENT ACTIVITY", font=(S.FONT, 9, "bold"),
                 fg=S.TEXT_MUTED, bg=S.BG_CARD).pack(anchor="w", padx=14, pady=(10, 4))

        self._activity_frame = tk.Frame(card, bg=S.BG_CARD)
        self._activity_frame.pack(fill=tk.X, padx=14, pady=(0, 12))
        self._activity_items: list[tk.Frame] = []


        self._update_summary()

    # ── Step management ───────────────────────────────────────────────────────

    def _add_step(self, cfg: dict | None = None):
        idx = len(self._steps) + 1
        card = StepCard(
            self._steps_frame,
            index=idx,
            on_delete=self._delete_step,
            on_drag_start=self._drag_start,
        )
        self._steps.append(card)
        if cfg:
            card.load_config(cfg)
        self._rerender_steps()
        self._update_summary()

    def _delete_step(self, card: StepCard):
        if len(self._steps) == 1:
            messagebox.showinfo("MacroFlow", "At least one step is required.")
            return
        self._steps.remove(card)
        self._rerender_steps()
        self._update_summary()

    # ── Drag-and-drop ─────────────────────────────────────────────────────────

    def _drag_start(self, card: StepCard, event):
        self._drag_card = card
        self._drag_insert_idx = None
        # Dim the dragged card
        card.config(highlightbackground=S.ACCENT, highlightthickness=2)
        # Drop indicator line
        self._drop_indicator = tk.Frame(self._steps_frame, height=3, bg=S.ACCENT)
        self.winfo_toplevel().bind("<B1-Motion>", self._drag_motion, add=True)
        self.winfo_toplevel().bind("<ButtonRelease-1>", self._drag_release, add=True)

    def _drag_motion(self, event):
        if not self._drag_card:
            return
        insert_idx = self._get_insert_idx(event.y_root)
        if insert_idx != self._drag_insert_idx:
            self._drag_insert_idx = insert_idx
            self._update_drop_line(insert_idx)

    def _get_insert_idx(self, y_root: int) -> int:
        """Return the index at which the dragged card would be inserted."""
        for i, card in enumerate(self._steps):
            if card is self._drag_card:
                continue
            try:
                card_mid = card.winfo_rooty() + card.winfo_height() // 2
            except Exception:
                continue
            if y_root < card_mid:
                return i
        return len(self._steps)

    def _update_drop_line(self, insert_idx: int):
        """Reposition the blue drop-indicator line between cards."""
        if not self._drop_indicator:
            return
        self._drop_indicator.pack_forget()

        others = [c for c in self._steps if c is not self._drag_card]
        if not others:
            return

        # Clamp to positions among non-dragged cards
        if insert_idx <= 0 or (others and self._steps.index(others[0]) >= insert_idx):
            # Before the first non-drag card
            self._drop_indicator.pack(fill=tk.X, padx=4, pady=0,
                                      before=others[0])
        else:
            # Find the card just before the insertion point
            prev = None
            for card in self._steps:
                if card is self._drag_card:
                    continue
                if self._steps.index(card) < insert_idx:
                    prev = card
            if prev:
                self._drop_indicator.pack(fill=tk.X, padx=4, pady=0,
                                          after=prev)

    def _drag_release(self, event):
        top = self.winfo_toplevel()
        top.unbind("<B1-Motion>")
        top.unbind("<ButtonRelease-1>")

        # Clean up visuals
        if self._drop_indicator:
            self._drop_indicator.destroy()
            self._drop_indicator = None
        if self._drag_card:
            self._drag_card.config(highlightbackground=S.BORDER, highlightthickness=1)

        # Reorder
        if self._drag_card and self._drag_insert_idx is not None:
            card = self._drag_card
            self._steps.remove(card)
            idx = min(self._drag_insert_idx, len(self._steps))
            self._steps.insert(idx, card)
            self._rerender_steps()

        self._drag_card = None
        self._drag_insert_idx = None

    def _find_card(self, widget) -> StepCard | None:
        while widget is not None:
            if isinstance(widget, StepCard):
                return widget
            try:
                widget = widget.master
            except Exception:
                break
        return None

    def _rerender_steps(self):
        """Unpack all cards, repack in order, update indices, then show add button."""
        for w in self._steps_frame.winfo_children():
            w.pack_forget()

        for i, card in enumerate(self._steps, 1):
            card.set_index(i)
            card.pack(fill=tk.X, pady=(0, 10))

        self._add_btn.pack(pady=12)
        self._canvas.update_idletasks()
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    # ── Summary panel helpers ─────────────────────────────────────────────────

    def _update_summary(self):
        total = len(self._steps)
        self._summary_rows["total"].config(text=f"{total:02d}")

    def _add_activity(self, text: str, color: str = S.GREEN):
        # Keep last 4
        if len(self._activity_items) >= 4:
            self._activity_items[0].destroy()
            self._activity_items.pop(0)

        row = tk.Frame(self._activity_frame, bg=S.BG_CARD)
        row.pack(fill=tk.X, pady=1)
        tk.Label(row, text="●", font=S.F_XS, fg=color, bg=S.BG_CARD).pack(side=tk.LEFT)
        tk.Label(row, text=text, font=S.F_SM, fg=S.TEXT_PRIMARY, bg=S.BG_CARD).pack(side=tk.LEFT, padx=4)
        ts = datetime.now().strftime("Today at %H:%M")
        tk.Label(row, text=ts, font=S.F_XS, fg=S.TEXT_MUTED, bg=S.BG_CARD).pack(side=tk.RIGHT)
        self._activity_items.append(row)

    # ── Run / Stop ────────────────────────────────────────────────────────────

    def start_run(self):
        if self._runner and self._runner.is_running():
            return
        steps = [card.get_config() for card in self._steps]
        # reset all dots
        for card in self._steps:
            card.set_status("")

        self._run_start = datetime.now()
        self._summary_rows["duration"].config(text="Running…")
        self._summary_rows["rate"].config(text="—", fg=S.TEXT_PRIMARY)

        self._runner = SequenceRunner(
            steps=steps,
            project_name=self._project_name_var.get(),
            on_step_start=self._on_step_start,
            on_step_done=self._on_step_done,
            on_run_done=self._on_run_done,
            on_error=self._on_run_error,
            tk_after=self.after,
        )
        self._runner.start()

    def stop_run(self):
        if self._runner:
            self._runner.stop()

    def _on_step_start(self, idx: int):
        if 0 <= idx < len(self._steps):
            self._steps[idx].set_status("running")
            self._add_activity(f"Step {idx + 1:02d} executing", S.ACCENT)

    def _on_step_done(self, idx: int, status: str, message: str):
        if 0 <= idx < len(self._steps):
            self._steps[idx].set_status(status)
        color = {"PASS": S.GREEN, "FAIL": S.RED, "WARN": S.AMBER}.get(status, S.TEXT_MUTED)
        self._add_activity(f"Step {idx + 1:02d} {status}: {message[:30]}", color)

    def _on_run_done(self, summary: dict):
        dur = summary.get("duration", 0)
        total = summary.get("total", 1)
        passed = summary.get("pass", 0)
        rate = round(passed / total * 100, 1) if total else 0

        self._summary_rows["duration"].config(text=f"{dur}s")
        rate_color = S.GREEN if rate >= 90 else (S.AMBER if rate >= 60 else S.RED)
        self._summary_rows["rate"].config(text=f"{rate}%", fg=rate_color)
        self._add_activity("Run complete", S.GREEN)

    def _on_run_error(self, msg: str):
        self._add_activity(f"Error: {msg[:40]}", S.RED)
        messagebox.showerror("Run Error", msg)

    # ── Save / Load ───────────────────────────────────────────────────────────

    def save_project(self):
        steps = [card.get_config() for card in self._steps]
        try:
            path = pio.save_project(self._project_name_var.get(), steps)
            self._add_activity(f"Saved → {path.name}", S.TEAL)
            messagebox.showinfo("Saved", f"Project saved to:\n{path}")
        except Exception as e:
            messagebox.showerror("Save Error", str(e))

    def load_project(self):
        path = filedialog.askopenfilename(
            title="Load project",
            initialdir=str(pio.CONFIGS_DIR),
            filetypes=[("YAML files", "*.yaml *.yml")],
        )
        if not path:
            return
        try:
            data = pio.load_project(path)
            self._project_name_var.set(data.get("name", "Untitled"))
            # Clear existing steps
            for card in list(self._steps):
                card.destroy()
            self._steps.clear()
            for step_cfg in data.get("steps", []):
                self._add_step(cfg=step_cfg)
            self._add_activity(f"Loaded project", S.TEAL)
        except Exception as e:
            messagebox.showerror("Load Error", str(e))
