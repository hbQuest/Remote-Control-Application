# -*- coding: utf-8 -*-
"""
features/software.py - Mixin Installed Software Manager.
Widget pooling được giữ nguyên để tối ưu hiệu năng.
"""
import io
import csv
import struct
import threading
import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox


class SoftwareMixin:

    def open_software_manager(self):
        self.disable_main_buttons()
        self.software_window = ctk.CTkToplevel(self.main_window)
        self.software_window.title(
            f"Installed Software - {self.session_name}{self.connection_info}"
        )
        self.software_window.geometry("700x750")
        self.software_window.protocol("WM_DELETE_WINDOW", self.on_close_software_window)
        self.bring_to_front(self.software_window)

        top_frame = ctk.CTkFrame(self.software_window, fg_color="transparent")
        top_frame.pack(fill=ctk.X, padx=25, pady=15)
        ctk.CTkLabel(
            top_frame,
            text=f"Installed Software on {self.session_name}",
            font=("Arial", 18, "bold"),
        ).pack(side=tk.LEFT)
        ctk.CTkButton(
            top_frame, text="Close", command=self.on_close_software_window,
            fg_color="transparent", text_color=self.accent_red,
            hover_color=("#FDE7E9", "#4A1A1E"), width=80,
        ).pack(side=tk.RIGHT, padx=5)
        ctk.CTkButton(
            top_frame, text="Refresh", command=self.refresh_software_list,
            fg_color=self.bg_card, text_color=self.accent_blue, width=80,
        ).pack(side=tk.RIGHT, padx=10)

        search_frame = ctk.CTkFrame(self.software_window, fg_color="transparent")
        search_frame.pack(fill=ctk.X, padx=20, pady=(0, 10))
        search_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(search_frame, text="🔍 Search:", font=("Arial", 13)).grid(
            row=0, column=0, padx=(5, 5), sticky="w"
        )
        self.sw_search_entry = ctk.CTkEntry(
            search_frame, placeholder_text="Filter by name..."
        )
        self.sw_search_entry.grid(row=0, column=1, sticky="ew")
        self.sw_search_entry.bind("<KeyRelease>", self.filter_software_list)

        header = ctk.CTkFrame(self.software_window, corner_radius=6, fg_color=self.bg_card)
        header.pack(fill=ctk.X, padx=20)
        header.grid_columnconfigure(0, weight=1)
        header.grid_columnconfigure(1, weight=0, minsize=100)

        h_font = ("Arial", 13, "bold")
        ctk.CTkLabel(header, text="Application Name", anchor="w", text_color=self.text_muted, font=h_font).grid(row=0, column=0, padx=10, pady=5, sticky="w")
        ctk.CTkLabel(header, text="Action", anchor="center", text_color=self.text_muted, font=h_font).grid(row=0, column=1, padx=10, pady=5, sticky="ew")

        self.sw_scrollable_frame = ctk.CTkScrollableFrame(
            self.software_window, corner_radius=10, fg_color=self.bg_card
        )
        self.sw_scrollable_frame.pack(expand=True, fill=ctk.BOTH, padx=20, pady=(10, 20))

        self.refresh_software_list()

    def on_close_software_window(self):
        self._sw_row_pool = []
        self._sw_data_cache = []
        self.software_window.destroy()
        self.enable_main_buttons()

    def refresh_software_list(self):
        if hasattr(self, 'sw_search_entry') and self.sw_search_entry.winfo_exists():
            self.sw_search_entry.delete(0, tk.END)
            self._sw_search_term_cache = ""
        threading.Thread(target=self.fetch_software_data, daemon=True).start()

    def fetch_software_data(self):
        with self.net_lock:
            try:
                self.client_socket.sendall("LIST_INSTALLED_APPS".encode('utf-8'))
                raw_msglen = self.recvall(4)
                if not raw_msglen:
                    return
                msglen = struct.unpack('>I', raw_msglen)[0]
                software_data = self.recvall(msglen).decode('utf-8', errors='replace')
                self.current_software_data = software_data
                self.main_window.after(
                    0, lambda: self.render_software_list(self.current_software_data)
                )
            except:
                pass

    def filter_software_list(self, event=None):
        if (
            hasattr(self, 'sw_search_entry')
            and self.sw_search_entry.winfo_exists()
            and hasattr(self, 'current_software_data')
        ):
            search_term = self.sw_search_entry.get().lower()
            self._sw_search_term_cache = search_term
            self.render_software_list(self.current_software_data, search_term)

    def _get_or_create_sw_row(self, index):
        if index < len(self._sw_row_pool):
            return self._sw_row_pool[index]
        if len(self._sw_row_pool) < self._max_pool_size:
            row_frame = ctk.CTkFrame(self.sw_scrollable_frame, fg_color="transparent", height=40)
            row_frame.pack(fill=ctk.X, pady=2)
            row_frame.pack_propagate(False)
            row_frame.grid_rowconfigure(0, weight=1)
            row_frame.grid_columnconfigure(0, weight=1)
            row_frame.grid_columnconfigure(1, weight=0, minsize=100)
            name_lbl = ctk.CTkLabel(row_frame, text="", font=("Arial", 12, "bold"))
            name_lbl.grid(row=0, column=0, padx=10, sticky="w")
            action_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
            action_frame.grid(row=0, column=1, sticky="e", padx=5)
            btn = ctk.CTkButton(
                action_frame, text="Start", fg_color="transparent",
                text_color=self.accent_green, border_width=1,
                width=80, height=2, command=lambda: None
            )
            btn.grid(row=0, column=0, pady=5)
            empty_lbl = ctk.CTkLabel(action_frame, text="", width=80)
            empty_lbl.grid(row=0, column=0)
            row_frame._widgets = {'name': name_lbl, 'btn': btn, 'empty': empty_lbl}
            row_frame._current_icon = None
            row_frame._has_button = False
            self._sw_row_pool.append(row_frame)
            return row_frame
        return None

    def _update_sw_button(self, row_frame, display_icon):
        def make_callback(icon):
            return lambda: self.request_start_app_from_sw_list(icon)
        row_frame._widgets['btn'].configure(command=make_callback(display_icon))

    def request_start_app_from_sw_list(self, display_icon_path):
        if not display_icon_path:
            return
        executable_path = display_icon_path.split(',')[0].strip('"')
        if not executable_path:
            messagebox.showwarning(
                "Cannot Start",
                "Could not determine the executable path for this application.",
                parent=self.software_window,
            )
            return
        threading.Thread(
            target=self.send_command,
            args=(f"START_PROCESS:{executable_path}", self.software_window),
            daemon=True,
        ).start()

    def render_software_list(self, software_data, search_term=""):
        clean_data = software_data.strip()
        if not clean_data:
            if not hasattr(self, '_sw_empty_label'):
                self._sw_empty_label = ctk.CTkLabel(
                    self.sw_scrollable_frame,
                    text="No software found or failed to query.",
                    text_color=self.text_muted,
                )
                self._sw_empty_label.pack(pady=20)
            return

        if hasattr(self, '_sw_empty_label'):
            self._sw_empty_label.destroy()
            delattr(self, '_sw_empty_label')

        new_sw_data = []
        reader = csv.reader(io.StringIO(clean_data))
        try:
            next(reader)
        except StopIteration:
            return

        for row in reader:
            if len(row) >= 5:
                name, display_icon = row[0], row[4]
                if search_term and not (search_term in name.lower()):
                    continue
                can_start = display_icon and ".exe" in display_icon.lower()
                new_sw_data.append((name, display_icon, can_start))

        data_changed = new_sw_data != self._sw_data_cache
        if data_changed:
            self._sw_data_cache = new_sw_data

        visible_count = 0
        for i, (name, display_icon, can_start) in enumerate(new_sw_data):
            row_frame = self._get_or_create_sw_row(i)
            if row_frame is None:
                break
            icon_changed = row_frame._current_icon != display_icon
            if icon_changed or data_changed:
                row_frame._widgets['name'].configure(text=self._truncate(name, 60))
                if can_start:
                    if not row_frame._has_button:
                        row_frame._widgets['empty'].grid_forget()
                        row_frame._widgets['btn'].grid(row=0, column=0, pady=5)
                        row_frame._has_button = True
                    self._update_sw_button(row_frame, display_icon)
                else:
                    if row_frame._has_button:
                        row_frame._widgets['btn'].grid_forget()
                        row_frame._widgets['empty'].grid(row=0, column=0)
                        row_frame._has_button = False
                row_frame._current_icon = display_icon
            if not row_frame.winfo_viewable():
                row_frame.pack(fill=ctk.X, pady=2)
            visible_count += 1

        for i in range(visible_count, len(self._sw_row_pool)):
            row_frame = self._sw_row_pool[i]
            if row_frame.winfo_viewable():
                row_frame.pack_forget()
