"""
app.py
Main application window: sidebar + topbar + page routing + bottom bar.
"""
import tkinter as tk
from tkinter import ttk, simpledialog

from gui import styles as S
from gui.sequence_editor import SequenceEditor


# ═════════════════════════════════════════════════════════════════════════════
class MacroFlowApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("MacroFlow — Automation Engine")
        self.root.geometry("1160x780")
        self.root.minsize(900, 640)
        self.root.configure(bg=S.BG_SIDEBAR)

        self._project_name = tk.StringVar(value="")
        self._project_created = False
        self._current_page = ""
        self._editor: SequenceEditor | None = None

        self._configure_ttk()
        self._apply_saved_settings()
        self._build()
        self._show_page("projects")

    # ── Saved settings ────────────────────────────────────────────────────────

    def _apply_saved_settings(self):
        from gui import project_io as pio
        try:
            settings = pio.load_settings()
            import pytesseract
            pytesseract.pytesseract.tesseract_cmd = settings["tesseract_path"]
        except Exception:
            pass

    # ── ttk theme ─────────────────────────────────────────────────────────────

    def _configure_ttk(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")

        style.configure(
            "Card.TCombobox",
            fieldbackground=S.BG_INPUT,
            background=S.BG_INPUT,
            foreground=S.TEXT_PRIMARY,
            bordercolor=S.BORDER,
            arrowcolor=S.TEXT_SECONDARY,
            relief="flat",
        )
        style.map("Card.TCombobox",
                  fieldbackground=[("readonly", S.BG_INPUT)],
                  selectbackground=[("readonly", S.BG_INPUT)],
                  selectforeground=[("readonly", S.TEXT_PRIMARY)])

        style.configure(
            "Sidebar.TButton",
            background=S.BG_SIDEBAR,
            foreground=S.TEXT_SIDEBAR,
            font=S.F_BASE,
            borderwidth=0,
            relief="flat",
            padding=(12, 10),
        )
        style.map("Sidebar.TButton",
                  background=[("active", S.BG_SIDEBAR_H)],
                  foreground=[("active", S.TEXT_WHITE)])

        style.configure("Vertical.TScrollbar",
                        background=S.BORDER,
                        troughcolor=S.BG_MAIN,
                        arrowcolor=S.TEXT_MUTED,
                        bordercolor=S.BG_MAIN,
                        relief="flat")

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build(self):
        # Outer paned: sidebar | right-side
        self._sidebar = self._build_sidebar()
        self._main = tk.Frame(self.root, bg=S.BG_MAIN)
        self._main.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._topbar = self._build_topbar(self._main)
        self._content = tk.Frame(self._main, bg=S.BG_MAIN)
        self._content.pack(fill=tk.BOTH, expand=True)
        self._bottombar = self._build_bottombar(self._main)

    # ── Sidebar ───────────────────────────────────────────────────────────────

    def _build_sidebar(self) -> tk.Frame:
        sb = tk.Frame(self.root, bg=S.BG_SIDEBAR, width=S.SIDEBAR_W)
        sb.pack(side=tk.LEFT, fill=tk.Y)
        sb.pack_propagate(False)

        # Brand
        brand = tk.Frame(sb, bg=S.BG_SIDEBAR)
        brand.pack(fill=tk.X, padx=16, pady=(20, 24))

        logo_bg = tk.Frame(brand, bg="#1E40AF", width=32, height=32)
        logo_bg.pack(side=tk.LEFT)
        logo_bg.pack_propagate(False)
        tk.Label(logo_bg, text="M", font=(S.FONT, 14, "bold"),
                 fg=S.TEXT_WHITE, bg="#1E40AF").place(relx=0.5, rely=0.5, anchor="center")

        info = tk.Frame(brand, bg=S.BG_SIDEBAR)
        info.pack(side=tk.LEFT, padx=(10, 0))
        tk.Label(info, text="MacroFlow", font=S.F_BRAND,
                 fg=S.TEXT_WHITE, bg=S.BG_SIDEBAR).pack(anchor="w")
        tk.Label(info, text="Automation Engine", font=S.F_XS,
                 fg=S.TEXT_MUTED, bg=S.BG_SIDEBAR).pack(anchor="w")

        # Divider
        tk.Frame(sb, height=1, bg=S.BG_SIDEBAR_H).pack(fill=tk.X)

        # Nav items
        self._nav_buttons: dict[str, tk.Frame] = {}
        nav_items = [
            ("projects",  " Projects"),
            ("settings",  " Settings"),
        ]
        for page, label in nav_items:
            self._nav_buttons[page] = self._nav_item(sb, page, label)

        return sb

    def _nav_item(self, parent, page: str, label: str) -> tk.Frame:
        row = tk.Frame(parent, bg=S.BG_SIDEBAR, cursor="hand2")
        row.pack(fill=tk.X)
        lbl = tk.Label(row, text=label, font=S.F_BASE,
                       fg=S.TEXT_SIDEBAR, bg=S.BG_SIDEBAR,
                       anchor="w", padx=16, pady=10)
        lbl.pack(fill=tk.X)

        def on_enter(_):
            if page != self._current_page:
                lbl.config(bg=S.BG_SIDEBAR_H, fg=S.TEXT_WHITE)
                row.config(bg=S.BG_SIDEBAR_H)

        def on_leave(_):
            if page != self._current_page:
                lbl.config(bg=S.BG_SIDEBAR, fg=S.TEXT_SIDEBAR)
                row.config(bg=S.BG_SIDEBAR)

        row.bind("<Enter>", on_enter)
        lbl.bind("<Enter>", on_enter)
        row.bind("<Leave>", on_leave)
        lbl.bind("<Leave>", on_leave)
        row.bind("<Button-1>", lambda e: self._show_page(page))
        lbl.bind("<Button-1>", lambda e: self._show_page(page))
        return row

    def _set_nav_active(self, page: str):
        for p, row in self._nav_buttons.items():
            lbl = row.winfo_children()[0]
            if p == page:
                lbl.config(bg=S.BG_SIDEBAR_H, fg=S.TEXT_WHITE)
                row.config(bg=S.BG_SIDEBAR_H)
            else:
                lbl.config(bg=S.BG_SIDEBAR, fg=S.TEXT_SIDEBAR)
                row.config(bg=S.BG_SIDEBAR)

    # ── Top bar ───────────────────────────────────────────────────────────────

    def _build_topbar(self, parent) -> tk.Frame:
        bar = tk.Frame(parent, bg=S.BG_TOPBAR, height=S.TOPBAR_H,
                       relief=tk.FLAT, highlightthickness=1,
                       highlightbackground=S.BORDER)
        bar.pack(fill=tk.X)
        bar.pack_propagate(False)

        # Left: back button + project name
        left = tk.Frame(bar, bg=S.BG_TOPBAR)
        left.pack(side=tk.LEFT, padx=(12, 0), pady=0, fill=tk.Y)

        self._btn_back = tk.Button(
            left, text="← Projects",
            font=S.F_SM, fg=S.TEXT_SECONDARY, bg=S.BG_TOPBAR,
            relief=tk.FLAT, bd=0, padx=8, pady=4, cursor="hand2",
            activeforeground=S.TEXT_PRIMARY, activebackground=S.BG_TOPBAR,
            command=lambda: self._show_page("projects"),
        )
        self._btn_back.pack(side=tk.LEFT, padx=(0, 4))

        tk.Label(left, text="·", font=S.F_SM,
                 fg=S.TEXT_MUTED, bg=S.BG_TOPBAR).pack(side=tk.LEFT, padx=(0, 8))

        tk.Label(left, text="Project:", font=S.F_SM,
                 fg=S.TEXT_MUTED, bg=S.BG_TOPBAR).pack(side=tk.LEFT)

        self._project_name_lbl = tk.Label(
            left, textvariable=self._project_name,
            font=(S.FONT, 12, "bold"), fg=S.TEXT_PRIMARY, bg=S.BG_TOPBAR,
            cursor="hand2",
        )
        self._project_name_lbl.pack(side=tk.LEFT, padx=(6, 0))
        self._project_name_lbl.bind("<Button-1>", self._rename_project)

        # Right: Stop / Run
        right = tk.Frame(bar, bg=S.BG_TOPBAR)
        right.pack(side=tk.RIGHT, padx=20, fill=tk.Y)

        self._btn_stop = tk.Button(
            right, text="Stop",
            font=S.F_BASE, fg=S.TEXT_PRIMARY, bg=S.BTN_STOP_BG,
            relief=tk.GROOVE, bd=1, padx=16, pady=4, cursor="hand2",
            activebackground="#F1F5F9",
            command=self._on_stop,
        )
        self._btn_stop.pack(side=tk.LEFT, padx=(0, 8))

        self._btn_run = tk.Button(
            right, text="▶  Run",
            font=(S.FONT, 11, "bold"), fg=S.TEXT_WHITE, bg=S.BTN_RUN_BG,
            relief=tk.FLAT, padx=18, pady=5, cursor="hand2",
            activebackground="#334155", activeforeground=S.TEXT_WHITE,
            command=self._on_run,
        )
        self._btn_run.pack(side=tk.LEFT)

        return bar

    # ── Bottom bar ────────────────────────────────────────────────────────────

    def _build_bottombar(self, parent) -> tk.Frame:
        bar = tk.Frame(parent, bg=S.BG_TOPBAR, height=S.BOTTOMBAR_H,
                       relief=tk.FLAT, highlightthickness=1,
                       highlightbackground=S.BORDER)
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        bar.pack_propagate(False)

        right = tk.Frame(bar, bg=S.BG_TOPBAR)
        right.pack(side=tk.RIGHT, padx=20, fill=tk.Y)

        tk.Button(
            right, text="Save & Publish",
            font=(S.FONT, 11, "bold"), fg=S.TEXT_WHITE, bg=S.BTN_PUBLISH_BG,
            relief=tk.FLAT, padx=16, pady=5, cursor="hand2",
            activebackground="#334155", activeforeground=S.TEXT_WHITE,
            command=self._on_save,
        ).pack(side=tk.LEFT)

        return bar

    # ── Page routing ──────────────────────────────────────────────────────────

    def _show_page(self, page: str):
        self._current_page = page
        self._set_nav_active(page)
        for w in self._content.winfo_children():
            w.destroy()
        self._editor = None

        if page == "projects":
            self._page_projects()
        elif page == "history":
            self._page_history()
        elif page == "settings":
            self._page_settings()

    def _page_projects(self):
        """Scrollable project list with inline '+' card creation."""
        self._project_created = False
        self._topbar.pack_forget()
        self._bottombar.pack_forget()

        from gui import project_io as pio
        import os, datetime as dt

        outer = tk.Frame(self._content, bg=S.BG_MAIN)
        outer.pack(fill=tk.BOTH, expand=True, padx=28, pady=24)

        # ── Header ────────────────────────────────────────────────────────────
        hdr = tk.Frame(outer, bg=S.BG_MAIN)
        hdr.pack(fill=tk.X, pady=(0, 16))
        tk.Label(hdr, text="Projects", font=S.F_2XL,
                 fg=S.TEXT_PRIMARY, bg=S.BG_MAIN).pack(side=tk.LEFT)

        # ── Scrollable list ───────────────────────────────────────────────────
        canvas = tk.Canvas(outer, bg=S.BG_MAIN, highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        list_frame = tk.Frame(canvas, bg=S.BG_MAIN)
        win_id = canvas.create_window((0, 0), window=list_frame, anchor="nw")

        def _on_resize(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
        def _on_canvas_resize(e):
            canvas.itemconfig(win_id, width=e.width)
        list_frame.bind("<Configure>", _on_resize)
        canvas.bind("<Configure>", _on_canvas_resize)
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(-1*(e.delta//120), "units"))

        # ── Saved project cards ───────────────────────────────────────────────
        def _render_saved():
            for w in list_frame.winfo_children():
                w.destroy()

            for p in pio.list_projects():
                card = tk.Frame(list_frame, bg=S.BG_CARD, relief=tk.FLAT,
                                highlightthickness=1, highlightbackground=S.BORDER)
                card.pack(fill=tk.X, pady=(0, 8))

                left = tk.Frame(card, bg=S.BG_CARD)
                left.pack(side=tk.LEFT, padx=16, pady=12)
                tk.Label(left, text=p.stem, font=(S.FONT, 12, "bold"),
                         fg=S.TEXT_PRIMARY, bg=S.BG_CARD).pack(anchor="w")
                mtime = dt.datetime.fromtimestamp(
                    os.path.getmtime(p)).strftime("%Y-%m-%d  %H:%M")
                tk.Label(left, text=mtime, font=S.F_SM,
                         fg=S.TEXT_MUTED, bg=S.BG_CARD).pack(anchor="w")

                btn_row = tk.Frame(card, bg=S.BG_CARD)
                btn_row.pack(side=tk.RIGHT, padx=14, pady=12)
                tk.Button(
                    btn_row, text="Open",
                    font=(S.FONT, 10, "bold"), fg=S.TEXT_WHITE, bg=S.BTN_RUN_BG,
                    relief=tk.FLAT, padx=14, pady=5, cursor="hand2",
                    activebackground="#334155", activeforeground=S.TEXT_WHITE,
                    command=lambda path=p: self._open_project(path),
                ).pack(side=tk.LEFT, padx=(0, 6))
                tk.Button(
                    btn_row, text="✕",
                    font=S.F_SM, fg=S.TEXT_MUTED, bg=S.BG_CARD,
                    relief=tk.FLAT, bd=0, cursor="hand2",
                    activeforeground=S.RED, activebackground=S.BG_CARD,
                    command=lambda path=p: _delete_project(path),
                ).pack(side=tk.LEFT)

            _add_new_btn()

        def _delete_project(path):
            from tkinter import messagebox
            if messagebox.askyesno("Delete", f"Delete project '{path.stem}'?"):
                try:
                    path.unlink()
                except Exception:
                    pass
                _render_saved()

        # ── "+ New Project" add button ────────────────────────────────────────
        self._proj_add_btn_frame = None

        def _add_new_btn():
            if self._proj_add_btn_frame and self._proj_add_btn_frame.winfo_exists():
                self._proj_add_btn_frame.destroy()
            f = tk.Frame(list_frame, bg=S.BG_MAIN)
            f.pack(pady=8)
            self._proj_add_btn_frame = f
            tk.Button(
                f, text="+ New Project",
                font=S.F_SM, fg=S.TEXT_SECONDARY, bg=S.BG_MAIN,
                relief=tk.FLAT, bd=0, cursor="hand2",
                activeforeground=S.ACCENT, activebackground=S.BG_MAIN,
                command=lambda: _show_create_card(f),
            ).pack()

        def _show_create_card(btn_frame):
            btn_frame.destroy()

            # Inline creation card
            card = tk.Frame(list_frame, bg=S.BG_CARD, relief=tk.FLAT,
                            highlightthickness=1, highlightbackground=S.ACCENT)
            card.pack(fill=tk.X, pady=(0, 8))

            inner = tk.Frame(card, bg=S.BG_CARD)
            inner.pack(fill=tk.X, padx=16, pady=14)

            tk.Label(inner, text="PROJECT NAME", font=(S.FONT, 9, "bold"),
                     fg=S.TEXT_MUTED, bg=S.BG_CARD).pack(anchor="w", pady=(0, 4))

            input_row = tk.Frame(inner, bg=S.BG_CARD)
            input_row.pack(fill=tk.X)

            name_var = tk.StringVar()
            name_entry = tk.Entry(
                input_row, textvariable=name_var,
                font=(S.FONT, 12), bg=S.BG_INPUT, fg=S.TEXT_PRIMARY,
                relief=tk.FLAT, highlightthickness=1,
                highlightbackground=S.BORDER, highlightcolor=S.ACCENT,
                insertbackground=S.TEXT_PRIMARY,
            )
            name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5)
            name_entry.focus_set()

            err_lbl = tk.Label(inner, text="", font=S.F_XS,
                               fg=S.RED, bg=S.BG_CARD)
            err_lbl.pack(anchor="w", pady=(3, 0))

            def _confirm():
                name = name_var.get().strip()
                if not name:
                    err_lbl.config(text="Please enter a project name.")
                    return
                self._project_name.set(name)
                self._open_editor()

            def _cancel():
                card.destroy()
                _add_new_btn()

            name_entry.bind("<Return>", lambda e: _confirm())
            name_entry.bind("<Escape>", lambda e: _cancel())

            btn_row = tk.Frame(input_row, bg=S.BG_CARD)
            btn_row.pack(side=tk.LEFT, padx=(10, 0))

            tk.Button(
                btn_row, text="Create",
                font=(S.FONT, 10, "bold"), fg=S.TEXT_WHITE, bg=S.BTN_RUN_BG,
                relief=tk.FLAT, padx=14, pady=5, cursor="hand2",
                activebackground="#334155", activeforeground=S.TEXT_WHITE,
                command=_confirm,
            ).pack(side=tk.LEFT, padx=(0, 6))
            tk.Button(
                btn_row, text="✕",
                font=S.F_SM, fg=S.TEXT_MUTED, bg=S.BG_CARD,
                relief=tk.FLAT, bd=0, cursor="hand2",
                activeforeground=S.RED, activebackground=S.BG_CARD,
                command=_cancel,
            ).pack(side=tk.LEFT)

            canvas.update_idletasks()
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.yview_moveto(1.0)

        _render_saved()

    def _page_new_project(self):
        pass

    def _page_history(self):
        from gui import project_io as pio
        f = tk.Frame(self._content, bg=S.BG_MAIN)
        f.pack(fill=tk.BOTH, expand=True, padx=28, pady=24)

        tk.Label(f, text="History", font=S.F_2XL,
                 fg=S.TEXT_PRIMARY, bg=S.BG_MAIN).pack(anchor="w")
        tk.Label(f, text="Past project runs and saved sequences.",
                 font=S.F_BASE, fg=S.TEXT_SECONDARY, bg=S.BG_MAIN).pack(anchor="w", pady=(2, 16))

        projects = pio.list_projects()
        if not projects:
            tk.Label(f, text="No saved projects found.\nSave a project from the Sequence Editor.",
                     font=S.F_BASE, fg=S.TEXT_MUTED, bg=S.BG_MAIN, justify=tk.LEFT).pack(anchor="w")
            return

        for p in projects:
            row = tk.Frame(f, bg=S.BG_CARD, relief=tk.FLAT,
                           highlightthickness=1, highlightbackground=S.BORDER)
            row.pack(fill=tk.X, pady=(0, 8))
            tk.Label(row, text=p.stem, font=(S.FONT, 12, "bold"),
                     fg=S.TEXT_PRIMARY, bg=S.BG_CARD, padx=14, pady=8).pack(side=tk.LEFT)
            import os, datetime as dt
            mtime = dt.datetime.fromtimestamp(os.path.getmtime(p)).strftime("%Y-%m-%d %H:%M")
            tk.Label(row, text=mtime, font=S.F_SM,
                     fg=S.TEXT_MUTED, bg=S.BG_CARD).pack(side=tk.LEFT)
            tk.Button(
                row, text="Load", font=S.F_SM, fg=S.TEXT_WHITE, bg=S.BTN_RUN_BG,
                relief=tk.FLAT, padx=12, pady=4, cursor="hand2",
                command=lambda path=p: self._load_and_open(path),
            ).pack(side=tk.RIGHT, padx=14, pady=8)

    def _page_settings(self):
        f = tk.Frame(self._content, bg=S.BG_MAIN)
        f.pack(fill=tk.BOTH, expand=True, padx=28, pady=24)

        tk.Label(f, text="Settings", font=S.F_2XL,
                 fg=S.TEXT_PRIMARY, bg=S.BG_MAIN).pack(anchor="w")
        tk.Label(f, text="Configure paths and runtime behaviour.",
                 font=S.F_BASE, fg=S.TEXT_SECONDARY, bg=S.BG_MAIN).pack(anchor="w", pady=(2, 20))

        # Tesseract path
        card = tk.Frame(f, bg=S.BG_CARD, relief=tk.FLAT,
                        highlightthickness=1, highlightbackground=S.BORDER)
        card.pack(fill=tk.X, pady=(0, 12))

        tk.Label(card, text="Tesseract Path", font=(S.FONT, 11, "bold"),
                 fg=S.TEXT_PRIMARY, bg=S.BG_CARD, padx=14, pady=10).pack(anchor="w")

        # Load saved path
        from gui import project_io as pio
        settings = pio.load_settings()
        current = settings.get("tesseract_path", "")

        tess_var = tk.StringVar(value=current)
        row = tk.Frame(card, bg=S.BG_CARD)
        row.pack(fill=tk.X, padx=14, pady=(0, 8))
        tk.Entry(row, textvariable=tess_var, font=S.F_BASE,
                 bg=S.BG_INPUT, fg=S.TEXT_PRIMARY, relief=tk.FLAT,
                 highlightthickness=1, highlightbackground=S.BORDER,
                 insertbackground=S.TEXT_PRIMARY).pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5)
        tk.Button(
            row, text="Browse", font=S.F_SM, fg=S.TEXT_SECONDARY, bg=S.BG_CARD,
            relief=tk.GROOVE, bd=1, padx=10, pady=4, cursor="hand2",
            command=lambda: tess_var.set(
                tk.filedialog.askopenfilename(
                    title="Select tesseract.exe",
                    filetypes=[("Executable", "*.exe")]) or tess_var.get()),
        ).pack(side=tk.LEFT, padx=(8, 0))

        status_lbl = tk.Label(card, text="", font=S.F_SM, bg=S.BG_CARD)
        status_lbl.pack(anchor="w", padx=14)

        def _save_tess():
            path = tess_var.get().strip()
            if not path:
                status_lbl.config(text="Path cannot be empty.", fg=S.RED)
                return
            try:
                import pytesseract
                pytesseract.pytesseract.tesseract_cmd = path
                pio.save_settings({"tesseract_path": path})
                status_lbl.config(text="✓  Saved and applied.", fg=S.GREEN)
            except Exception as e:
                status_lbl.config(text=f"Error: {e}", fg=S.RED)

        tk.Button(card, text="Save", font=S.F_SM, fg=S.TEXT_WHITE, bg=S.BTN_RUN_BG,
                  relief=tk.FLAT, padx=14, pady=4, cursor="hand2",
                  command=_save_tess).pack(anchor="e", padx=14, pady=(4, 12))

        # Info
        info = tk.Frame(f, bg=S.BG_CARD, relief=tk.FLAT,
                        highlightthickness=1, highlightbackground=S.BORDER)
        info.pack(fill=tk.X)
        lines = [
            "PyInstaller packaging:   pyinstaller morning_check.spec",
            "Default configs dir:     configs/",
            "Screenshots:             output/screenshots/",
            "Logs:                    output/logs/",
        ]
        tk.Label(info, text="Quick Reference", font=(S.FONT, 11, "bold"),
                 fg=S.TEXT_PRIMARY, bg=S.BG_CARD, padx=14, pady=10).pack(anchor="w")
        for line in lines:
            tk.Label(info, text=line, font=(S.FONT, 10),
                     fg=S.TEXT_SECONDARY, bg=S.BG_CARD, padx=14).pack(anchor="w")
        tk.Frame(info, height=12, bg=S.BG_CARD).pack()

    # ── Actions ───────────────────────────────────────────────────────────────

    def _on_run(self):
        if self._editor:
            self._btn_run.config(state=tk.DISABLED)
            self._btn_stop.config(state=tk.NORMAL)
            self._editor.start_run()
            # re-enable run button after run (poll)
            self._poll_run_done()

    def _poll_run_done(self):
        if self._editor and self._editor._runner and self._editor._runner.is_running():
            self.root.after(500, self._poll_run_done)
        else:
            self._btn_run.config(state=tk.NORMAL)
            self._btn_stop.config(state=tk.NORMAL)

    def _on_stop(self):
        if self._editor:
            self._editor.stop_run()
        self._btn_run.config(state=tk.NORMAL)

    def _on_save(self):
        if self._editor:
            self._editor.save_project()

    def _on_preview(self):
        if not self._editor:
            return
        steps = [c.get_config() for c in self._editor._steps]
        lines = [f"Step {i+1:02d}: {s['action'].upper()} — {list(s.values())[1] if len(s) > 1 else ''}"
                 for i, s in enumerate(steps)]
        tk.messagebox.showinfo(
            f"Preview — {self._project_name.get()}",
            "\n".join(lines) or "No steps defined.",
        )

    def _rename_project(self, _=None):
        new = simpledialog.askstring(
            "Rename Project",
            "Enter project name:",
            initialvalue=self._project_name.get(),
            parent=self.root,
        )
        if new and new.strip():
            self._project_name.set(new.strip())

    def _open_editor(self, steps: list[dict] | None = None):
        """Show topbar/bottombar and launch the sequence editor."""
        self._project_created = True
        self._topbar.pack(fill=tk.X, before=self._content)
        self._bottombar.pack(fill=tk.X, side=tk.BOTTOM)
        for w in self._content.winfo_children():
            w.destroy()
        self._editor = SequenceEditor(
            self._content,
            project_name_var=self._project_name,
        )
        self._editor.pack(fill=tk.BOTH, expand=True)
        if steps:
            for cfg in steps:
                self._editor._add_step(cfg=cfg)

    def _open_project(self, path):
        """Load a saved YAML project and open the editor."""
        from gui import project_io as pio
        try:
            data = pio.load_project(path)
            self._project_name.set(data.get("name", "Untitled"))
            for w in self._content.winfo_children():
                w.destroy()
            self._open_editor(steps=data.get("steps", []))
        except Exception as e:
            tk.messagebox.showerror("Load Error", str(e))

    # ── Entry point ───────────────────────────────────────────────────────────

    def run(self):
        self.root.mainloop()
