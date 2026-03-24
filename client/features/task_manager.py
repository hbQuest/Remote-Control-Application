# -*- coding: utf-8 -*-
"""
features/task_manager.py – Task Manager với ttk.Treeview.

Màu sắc đồng bộ hoàn toàn với bảng màu Fluent Design của ứng dụng:
  • bg_card   : (#FFFFFF / #2B2B2B)
  • accent_r  : (#D13438 / #FF99A4)
  • accent_b  : (#005FB8 / #60CDFF)
  • text_muted: (#5c5c5c / #a0a0a0)

Scrollbar custom bằng Canvas – mảnh, bo tròn, màu accent, đẹp hơn ttk mặc định.
"""
import io
import csv
import struct
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk


# ══════════════════════════════════════════════════════════════════════════════
#  Scrollbar custom (Canvas-based, thin & rounded)
# ══════════════════════════════════════════════════════════════════════════════

class SmoothScrollbar(tk.Canvas):
    """
    Scrollbar mỏng, bo tròn, màu accent.
    Dùng thay cho ttk.Scrollbar để đồng bộ theme.
    """
    TRACK_COLOR_DARK  = "#1e1e2e"
    TRACK_COLOR_LIGHT = "#f0f0f0"
    THUMB_NORMAL      = "#555570"
    THUMB_HOVER       = "#7070a0"
    THUMB_DARK_N      = "#555570"
    THUMB_DARK_H      = "#8888b0"
    THUMB_LIGHT_N     = "#b0b0c8"
    THUMB_LIGHT_H     = "#7070a8"

    W = 8   # chiều rộng scrollbar

    def __init__(self, master, is_dark=True, **kw):
        track = self.TRACK_COLOR_DARK if is_dark else self.TRACK_COLOR_LIGHT
        super().__init__(master, width=self.W, bg=track,
                         highlightthickness=0, bd=0, **kw)
        self._is_dark   = is_dark
        self._thumb_n   = self.THUMB_DARK_N if is_dark else self.THUMB_LIGHT_N
        self._thumb_h   = self.THUMB_DARK_H if is_dark else self.THUMB_LIGHT_H
        self._command   = None
        self._thumb_id  = None
        self._dragging  = False
        self._drag_start_y = 0
        self._drag_start_frac = 0
        self._first = 0.0
        self._last  = 1.0

        self.bind("<Configure>",     self._redraw)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<B1-Motion>",     self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Enter>",         lambda e: self._set_hover(True))
        self.bind("<Leave>",         lambda e: self._set_hover(False))
        self._hovered = False

    def configure_command(self, cmd):
        self._command = cmd

    def set(self, first, last):
        self._first = float(first)
        self._last  = float(last)
        self._redraw()

    def _redraw(self, event=None):
        self.delete("all")
        h = self.winfo_height()
        w = self.W
        if h == 0:
            return
        y0 = int(self._first * h)
        y1 = int(self._last  * h)
        y1 = max(y1, y0 + 20)   # min thumb size
        r  = w // 2 - 1
        color = self._thumb_h if self._hovered or self._dragging else self._thumb_n
        # Rounded rect via arc + line trick
        x0, x1 = 1, w - 1
        self._draw_rounded_rect(x0, y0 + 2, x1, y1 - 2, r, color)

    def _draw_rounded_rect(self, x0, y0, x1, y1, r, fill):
        r = min(r, (x1 - x0) // 2, max(1, (y1 - y0) // 2))
        self.create_arc(x0, y0, x0+2*r, y0+2*r, start=90,  extent=90,  fill=fill, outline=fill)
        self.create_arc(x1-2*r, y0, x1, y0+2*r, start=0,   extent=90,  fill=fill, outline=fill)
        self.create_arc(x0, y1-2*r, x0+2*r, y1, start=180, extent=90,  fill=fill, outline=fill)
        self.create_arc(x1-2*r, y1-2*r, x1, y1, start=270, extent=90,  fill=fill, outline=fill)
        self.create_rectangle(x0+r, y0, x1-r, y1, fill=fill, outline=fill)
        self.create_rectangle(x0, y0+r, x1, y1-r, fill=fill, outline=fill)

    def _set_hover(self, state):
        self._hovered = state
        self._redraw()

    def _on_press(self, event):
        self._dragging = True
        self._drag_start_y    = event.y
        self._drag_start_frac = self._first
        self._set_hover(True)

    def _on_drag(self, event):
        if not self._dragging or self._command is None:
            return
        h = self.winfo_height()
        if h == 0:
            return
        delta = (event.y - self._drag_start_y) / h
        new_first = max(0.0, min(1.0 - (self._last - self._first),
                                 self._drag_start_frac + delta))
        self._command("moveto", new_first)

    def _on_release(self, event):
        self._dragging = False
        self._redraw()


# ══════════════════════════════════════════════════════════════════════════════
#  TaskManagerMixin
# ══════════════════════════════════════════════════════════════════════════════

class TaskManagerMixin:

    # ──────────────────────────────────────────────────────────────────────────
    #  Mở cửa sổ
    # ──────────────────────────────────────────────────────────────────────────

    def open_task_manager(self):
        self.disable_main_buttons()

        self._tm_search_after = None
        self._tm_all_apps     = []
        self._tm_all_procs    = []
        self.current_app_data     = ""
        self.current_process_data = ""

        win = ctk.CTkToplevel(self.main_window)
        win.title(f"Task Manager – {self.session_name}{self.connection_info}")
        win.geometry("900x830")
        win.resizable(True, True)
        win.protocol("WM_DELETE_WINDOW", self.on_close_task_manager_window)
        win.transient(self.main_window)
        win.after(10, win.lift) 
        win.after(10, win.focus_force)
        # win.attributes("-topmost", True)

        self.task_manager_window = win
        # self.bring_to_front(win)

        self._build_tm_ui(win)
        self.refresh_task_manager_list()

    # ──────────────────────────────────────────────────────────────────────────
    #  Build UI
    # ──────────────────────────────────────────────────────────────────────────

    def _build_tm_ui(self, win):
        is_dark = ctk.get_appearance_mode().lower() == "dark"

        # ── Bảng màu đồng bộ với theme Fluent Design của app ────────────────
        # Lấy giá trị màu thực (không phải tuple CTk) theo mode hiện tại
        def _c(pair):
            return pair[1] if is_dark else pair[0]

        if is_dark:
            C = dict(
                win_bg    = "#242424",          # CTk dark window default
                card_bg   = _c(self.bg_card),   # #2B2B2B
                row_a     = "#2B2B2B",
                row_b     = "#242424",
                row_hover = "#363636",
                row_sel   = "#3a3a4a",
                head_bg   = "#1e1e1e",
                border    = "#3a3a3a",
                fg        = "#e0e0e0",
                fg_muted  = _c(self.text_muted),  # #a0a0a0
                fg_kill   = _c(self.accent_red),  # #FF99A4
                fg_blue   = _c(self.accent_blue), # #60CDFF
                sb_track  = "#1e1e1e",
                sb_thumb  = "#505050",
                sb_hover  = "#707070",
            )
        else:
            C = dict(
                win_bg    = "#ebebeb",          # CTk light window default
                card_bg   = _c(self.bg_card),   # #FFFFFF
                row_a     = "#FFFFFF",
                row_b     = "#f5f5f5",
                row_hover = "#e8f0fb",
                row_sel   = "#dbe8f8",
                head_bg   = "#f0f0f0",
                border    = "#d0d0d0",
                fg        = "#1a1a1a",
                fg_muted  = _c(self.text_muted),  # #5c5c5c
                fg_kill   = _c(self.accent_red),  # #D13438
                fg_blue   = _c(self.accent_blue), # #005FB8
                sb_track  = "#f0f0f0",
                sb_thumb  = "#c0c0c8",
                sb_hover  = "#9090b0",
            )
        self._C = C
        self._tm_is_dark = is_dark

        # ── Top bar ──────────────────────────────────────────────────────────
        top = ctk.CTkFrame(win, fg_color="transparent")
        top.pack(fill=tk.X, padx=24, pady=(18, 8))

        ctk.CTkLabel(
            top,
            text=f"⚙  Task Manager  —  {self.session_name}",
            font=("Arial", 17, "bold"),
        ).pack(side=tk.LEFT)

        ctk.CTkButton(
            top, text="✕  Close",
            command=self.on_close_task_manager_window,
            fg_color="transparent", text_color=self.accent_red,
            hover_color=("#fde7e9", "#3a1520"),
            font=("Arial", 14), width=90, height=30, corner_radius=7,
        ).pack(side=tk.RIGHT, padx=(6, 0))

        ctk.CTkButton(
            top, text="↻  Refresh",
            command=self.refresh_task_manager_list,
            fg_color=self.bg_card, text_color=self.accent_blue,
            font=("Arial", 14), width=100, height=30, corner_radius=7,
        ).pack(side=tk.RIGHT, padx=6)

        # ── Search bar ───────────────────────────────────────────────────────
        sf = ctk.CTkFrame(win, fg_color=self.bg_card, corner_radius=8)
        sf.pack(fill=tk.X, padx=24, pady=(0, 10))
        sf.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            sf, text="🔍", font=("Arial", 14), text_color=self.text_muted
        ).grid(row=0, column=0, padx=(14, 6), pady=9)

        self.tm_search_entry = ctk.CTkEntry(
            sf,
            placeholder_text="Type to filter processes…",
            font=("Arial", 14),
            fg_color="transparent",
            border_width=0,
        )
        self.tm_search_entry.grid(row=0, column=1, sticky="ew", pady=9, padx=(0, 14))
        self.tm_search_entry.bind("<KeyRelease>", self._tm_search_debounce)

        # ── Main content ─────────────────────────────────────────────────────
        content = ctk.CTkFrame(win, fg_color="transparent")
        content.pack(expand=True, fill=tk.BOTH, padx=24, pady=(0, 8))
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(1, weight=0)
        content.grid_rowconfigure(4, weight=1)

        # Apps section
        self.apps_label = ctk.CTkLabel(
            content, text="Apps (loading…)",
            font=("Arial", 14, "bold"), anchor="w",
            text_color=self.text_muted,
        )
        self.apps_label.grid(row=0, column=0, sticky="ew", padx=2, pady=(4, 3))

        self.apps_tv_outer = self._make_treeview(content, C, is_dark, height=7)
        self.apps_tv_outer.grid(row=1, column=0, sticky="nsew", pady=(0, 12))

        # Processes section
        self.procs_label = ctk.CTkLabel(
            content, text="Background processes (loading…)",
            font=("Arial", 14, "bold"), anchor="w",
            text_color=self.text_muted,
        )
        self.procs_label.grid(row=3, column=0, sticky="ew", padx=2, pady=(0, 3))

        self.procs_tv_outer = self._make_treeview(content, C, is_dark, height=6)
        self.procs_tv_outer.grid(row=4, column=0, sticky="nsew")

        # Expose treeview widgets
        self.apps_tv  = self.apps_tv_outer._tv
        self.procs_tv = self.procs_tv_outer._tv

        # ── Control bar ──────────────────────────────────────────────────────
        ctrl = ctk.CTkFrame(win, fg_color=self.bg_card, corner_radius=8)
        ctrl.pack(fill=tk.X, padx=24, pady=(10, 16))
        ctrl.grid_columnconfigure(1, weight=1)
        ctrl.grid_columnconfigure(4, weight=1)

        ctk.CTkLabel(ctrl, text="Start App:", font=("Arial", 14)).grid(
            row=0, column=0, padx=(16, 6), pady=11, sticky="w"
        )
        self.tm_start_entry = ctk.CTkEntry(
            ctrl, font=("Consolas", 12), corner_radius=6,
            placeholder_text="notepad.exe"
        )
        self.tm_start_entry.grid(row=0, column=1, padx=4, pady=11, sticky="ew")
        self.tm_start_entry.bind("<Return>", self.request_start_process_tm)

        ctk.CTkButton(
            ctrl, text="▶  Start",
            command=self.request_start_process_tm,
            fg_color="transparent", text_color=self.accent_blue,
            border_width=1, border_color=self.accent_blue,
            font=("Arial", 14), width=90, height=30, corner_radius=7,
        ).grid(row=0, column=2, padx=(4, 16), pady=11)

        sep = tk.Frame(ctrl, bg=C["border"], width=1)
        sep.grid(row=0, column=3, sticky="ns", pady=8)

        ctk.CTkLabel(ctrl, text="Kill PID:", font=("Arial", 14)).grid(
            row=0, column=4, padx=(16, 6), pady=11, sticky="w"
        )
        self.tm_kill_entry = ctk.CTkEntry(
            ctrl, font=("Consolas", 14), corner_radius=6,
            placeholder_text="1234"
        )
        self.tm_kill_entry.grid(row=0, column=5, padx=4, pady=11, sticky="ew")
        self.tm_kill_entry.bind("<Return>", self.request_kill_process_input_tm)

        ctk.CTkButton(
            ctrl, text="⛔  Kill",
            command=self.request_kill_process_input_tm,
            fg_color="transparent", text_color=self.accent_red,
            border_width=1, border_color=self.accent_red,
            hover_color=("#fde7e9", "#3a1520"),
            font=("Arial", 14), width=90, height=30, corner_radius=7,
        ).grid(row=0, column=6, padx=(4, 16), pady=11)

        ctrl.grid_columnconfigure(1, weight=1)
        ctrl.grid_columnconfigure(5, weight=1)

    # ──────────────────────────────────────────────────────────────────────────
    #  Treeview factory + custom scrollbar
    # ──────────────────────────────────────────────────────────────────────────

    def _make_treeview(self, parent, C, is_dark, height=10):
        """
        Tạo Treeview 3 cột (Name | PID | Kill) bọc trong outer Frame.
        Scrollbar custom mảnh, bo tròn, màu đồng bộ với app.
        """
        # ── ttk Style ────────────────────────────────────────────────────────
        uid = str(id(parent)) + str(height)
        sid = f"TM{uid}.Treeview"
        s = ttk.Style()
        s.theme_use("clam")

        s.configure(sid,
            background      = C["row_a"],
            foreground      = C["fg"],
            fieldbackground = C["row_a"],
            rowheight       = 34,
            font            = ("Arial", 11),
            borderwidth     = 0,
        )
        s.configure(f"{sid}.Heading",
            background  = C["head_bg"],
            foreground  = C["fg_muted"],
            font        = ("Arial", 11, "bold"),
            relief      = "flat",
            padding     = (10, 7),
        )
        s.map(sid,
            background=[("selected", C["row_sel"])],
            foreground=[("selected", C["fg"])])
        s.map(f"{sid}.Heading",
            background=[("active", C["head_bg"])])

        # ── Outer frame (card với border) ────────────────────────────────────
        outer = tk.Frame(
            parent,
            bg=C["border"],
            highlightthickness=0,
        )

        inner = tk.Frame(outer, bg=C["row_a"], bd=0)
        inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        inner.grid_rowconfigure(0, weight=1)
        inner.grid_columnconfigure(0, weight=1)

        # ── Treeview ─────────────────────────────────────────────────────────
        tv = ttk.Treeview(
            inner,
            columns=("pid", "action"),
            show="headings tree",
            selectmode="browse",
            style=sid,
            height=height,
        )
        tv.heading("#0",     text="  Application Name", anchor="w")
        tv.heading("pid",    text="PID",                anchor="center")
        tv.heading("action", text="Action",             anchor="center")

        tv.column("#0",     anchor="w",      stretch=True,  minwidth=240)
        tv.column("pid",    anchor="center", stretch=False, width=78)
        tv.column("action", anchor="center", stretch=False, width=90)

        # ── Custom scrollbar ─────────────────────────────────────────────────
        vsb = SmoothScrollbar(inner, is_dark=is_dark)
        vsb.configure_command(tv.yview)
        tv.configure(yscrollcommand=lambda f, l: (vsb.set(f, l)))

        tv.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns", padx=(2, 3), pady=3)

        # ── Tags ─────────────────────────────────────────────────────────────
        tv.tag_configure("even",  background=C["row_a"], foreground=C["fg"])
        tv.tag_configure("odd",   background=C["row_b"], foreground=C["fg"])
        tv.tag_configure("hover", background=C["row_hover"], foreground=C["fg"])

        tv._C          = C
        tv._hover_iid  = None

        # ── Bindings ─────────────────────────────────────────────────────────
        tv.bind("<Button-1>", lambda e, t=tv: self._tm_on_click(e, t))
        tv.bind("<Motion>",   lambda e, t=tv: self._tm_on_motion(e, t))
        tv.bind("<Leave>",    lambda e, t=tv: self._tm_on_leave(t))
        tv.bind("<Button-3>", lambda e, t=tv: self._tm_context_menu(e, t))

        outer._tv = tv
        return outer

    # ──────────────────────────────────────────────────────────────────────────
    #  Interaction handlers
    # ──────────────────────────────────────────────────────────────────────────

    def _tm_on_click(self, event, tv):
        region = tv.identify_region(event.x, event.y)
        col    = tv.identify_column(event.x)
        iid    = tv.identify_row(event.y)
        if region == "cell" and col == "#2" and iid:
            pid = tv.item(iid, "values")[0]
            self.request_kill_process_by_pid(pid, self.task_manager_window)

    def _tm_on_motion(self, event, tv):
        iid = tv.identify_row(event.y)
        col = tv.identify_column(event.x)
        prev = tv._hover_iid

        if prev and prev != iid:
            if tv.exists(prev):
                children = list(tv.get_children())
                idx = children.index(prev) if prev in children else 0
                tv.item(prev, tags=("even" if idx % 2 == 0 else "odd",))
            tv._hover_iid = None

        if iid:
            tv._hover_iid = iid
            tv.item(iid, tags=("hover",))

        tv.configure(cursor="hand2" if (iid and col == "#2") else "")

    def _tm_on_leave(self, tv):
        prev = tv._hover_iid
        if prev and tv.exists(prev):
            children = list(tv.get_children())
            idx = children.index(prev) if prev in children else 0
            tv.item(prev, tags=("even" if idx % 2 == 0 else "odd",))
        tv._hover_iid = None
        tv.configure(cursor="")

    def _tm_context_menu(self, event, tv):
        iid = tv.identify_row(event.y)
        if not iid:
            return
        tv.selection_set(iid)
        pid  = tv.item(iid, "values")[0]
        name = tv.item(iid, "text").strip()
        menu = tk.Menu(tv, tearoff=0)
        menu.add_command(
            label=f'Kill  "{name}"  (PID {pid})',
            command=lambda: self.request_kill_process_by_pid(pid, self.task_manager_window),
        )
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    # ──────────────────────────────────────────────────────────────────────────
    #  Close
    # ──────────────────────────────────────────────────────────────────────────

    def on_close_task_manager_window(self):
        if self._tm_search_after:
            self.main_window.after_cancel(self._tm_search_after)
            self._tm_search_after = None
        self.task_manager_window.destroy()
        self.enable_main_buttons()

    # ──────────────────────────────────────────────────────────────────────────
    #  Fetch & Parse (background thread)
    # ──────────────────────────────────────────────────────────────────────────

    def refresh_task_manager_list(self):
        self.apps_label.configure(text="Apps (loading…)")
        self.procs_label.configure(text="Background processes (loading…)")
        if hasattr(self, "tm_search_entry") and self.tm_search_entry.winfo_exists():
            self.tm_search_entry.delete(0, tk.END)
        threading.Thread(target=self._fetch_and_parse, daemon=True).start()

    def _fetch_and_parse(self):
        with self.net_lock:
            try:
                self.client_socket.sendall("LIST_APP".encode("utf-8"))
                raw = self.recvall(4)
                if not raw:
                    self.main_window.after(0, lambda: self.apps_label.configure(
                        text="Apps (connection lost)"))
                    return
                app_data = self.recvall(struct.unpack(">I", raw)[0]).decode("utf-8", errors="replace")

                self.client_socket.sendall("LIST_PROCESS".encode("utf-8"))
                raw = self.recvall(4)
                if not raw:
                    self.main_window.after(0, lambda: self.procs_label.configure(
                        text="Processes (connection lost)"))
                    return
                proc_data = self.recvall(struct.unpack(">I", raw)[0]).decode("utf-8", errors="replace")

            except Exception as ex:
                msg = str(ex)[:40]
                self.main_window.after(0, lambda m=msg: self.apps_label.configure(
                    text=f"Apps (error: {m})"))
                return

        app_rows, proc_rows = self._parse_data(app_data, proc_data)
        self.main_window.after(0, lambda: self._populate(app_rows, proc_rows))

    def _parse_data(self, app_data, proc_data):
        app_pids, app_rows = set(), []
        lines = app_data.strip().split("\n")
        if lines and lines[0].startswith("#TYPE"):
            lines = lines[1:]
        reader = csv.reader(io.StringIO("\n".join(lines)))
        try:
            next(reader)
        except StopIteration:
            pass
        for row in reader:
            if len(row) >= 3:
                name, pid = row[0].strip(), row[1].strip()
                app_pids.add(pid)
                app_rows.append((name, pid))

        _skip = {"system idle process", "system", "registry", "smss.exe"}
        proc_rows = []
        for row in csv.reader(io.StringIO(proc_data)):
            if len(row) >= 5:
                name, pid = row[0].strip(), row[1].strip()
                if pid not in app_pids and name.lower() not in _skip:
                    proc_rows.append((name, pid))

        self._tm_all_apps  = app_rows
        self._tm_all_procs = proc_rows
        return app_rows, proc_rows

    # ──────────────────────────────────────────────────────────────────────────
    #  Populate / Fill Treeview
    # ──────────────────────────────────────────────────────────────────────────

    def _populate(self, app_rows, proc_rows, search=""):
        self._fill_tv(self.apps_tv,  app_rows,  search)
        self._fill_tv(self.procs_tv, proc_rows, search)
        self.apps_label.configure(
            text=f"Apps  ({len(self.apps_tv.get_children())})")
        self.procs_label.configure(
            text=f"Background processes  ({len(self.procs_tv.get_children())})")

    def _fill_tv(self, tv, rows, search=""):
        tv.delete(*tv.get_children())
        st = search.lower() if search else ""
        for i, (name, pid) in enumerate(rows):
            if st and st not in name.lower():
                continue
            tag = "even" if i % 2 == 0 else "odd"
            tv.insert("", "end",
                       text=f"  {self._truncate(name, 65)}",
                       values=(pid, "Kill"),
                       tags=(tag,))

    # ──────────────────────────────────────────────────────────────────────────
    #  Search (debounce 100 ms)
    # ──────────────────────────────────────────────────────────────────────────

    def _tm_search_debounce(self, event=None):
        if self._tm_search_after:
            self.main_window.after_cancel(self._tm_search_after)
        self._tm_search_after = self.main_window.after(100, self._tm_apply_filter)

    def _tm_apply_filter(self):
        self._tm_search_after = None
        if not hasattr(self, "tm_search_entry") or not self.tm_search_entry.winfo_exists():
            return
        st = self.tm_search_entry.get().lower()
        self._fill_tv(self.apps_tv,  self._tm_all_apps,  st)
        self._fill_tv(self.procs_tv, self._tm_all_procs, st)
        self.apps_label.configure(
            text=f"Apps  ({len(self.apps_tv.get_children())})")
        self.procs_label.configure(
            text=f"Background processes  ({len(self.procs_tv.get_children())})")

    # ──────────────────────────────────────────────────────────────────────────
    #  Network commands
    # ──────────────────────────────────────────────────────────────────────────

    def send_command(self, command, parent_win=None):
        with self.net_lock:
            try:
                self.client_socket.sendall(command.encode("utf-8"))
                raw = self.recvall(4)
                if not raw:
                    return
                response = self.recvall(struct.unpack(">I", raw)[0]).decode("utf-8", errors="replace")
                if parent_win:
                    self.main_window.after(
                        0,
                        lambda m=response: messagebox.showinfo(
                            "Action Result", m, parent=parent_win),
                    )
            except Exception:
                pass
        if parent_win == getattr(self, "task_manager_window", None):
            self.main_window.after(0, self.refresh_task_manager_list)

    def request_kill_process_by_pid(self, pid, parent_window):
        if messagebox.askyesno(
            "Confirm Kill",
            f"Force kill process với PID {pid}?",
            parent=parent_window,
        ):
            threading.Thread(
                target=self.send_command,
                args=(f"KILL_PROCESS:{pid}", parent_window),
                daemon=True,
            ).start()

    def request_kill_process_input_tm(self, event=None):
        target_pid = self.tm_kill_entry.get().strip()
        if not target_pid:
            return
        if not target_pid.isdigit():
            messagebox.showwarning("Invalid PID",
                                   "Vui lòng nhập PID hợp lệ (số nguyên).",
                                   parent=self.task_manager_window)
            return
        self.tm_kill_entry.delete(0, tk.END)
        threading.Thread(
            target=self.send_command,
            args=(f"KILL_PROCESS:{target_pid}", self.task_manager_window),
            daemon=True,
        ).start()

    def request_start_process_tm(self, event=None):
        target = self.tm_start_entry.get().strip()
        if not target:
            return
        self.tm_start_entry.delete(0, tk.END)
        if not target.lower().endswith(".exe"):
            target += ".exe"
        threading.Thread(
            target=self.send_command,
            args=(f"START_PROCESS:{target}", self.task_manager_window),
            daemon=True,
        ).start()
