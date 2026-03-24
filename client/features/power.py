# -*- coding: utf-8 -*-
"""
features/power.py - Mixin Power Management (Sleep / Restart / Shutdown).
"""
import customtkinter as ctk
from tkinter import messagebox


class PowerMixin:

    def open_power_manager(self):
        self.power_window = ctk.CTkToplevel(self.main_window)
        self.power_window.title(
            f"Power Management - {self.session_name}{self.connection_info}"
        )
        self.power_window.geometry("400x320")
        self.bring_to_front(self.power_window)

        ctk.CTkLabel(
            self.power_window,
            text="WARNING: These actions will disconnect the session.",
            text_color=self.accent_red,
            font=("Arial", 13, "bold"),
        ).pack(pady=20)

        btn_opts = {"font": ("Arial", 14, "bold"), "height": 45, "corner_radius": 8}

        ctk.CTkButton(
            self.power_window,
            text=f"💤 Sleep {self.session_name}",
            command=lambda: self.send_power_cmd("SYS_SLEEP", "put the Remote PC to Sleep"),
            fg_color=self.bg_card,
            text_color="#FF9500",
            hover_color=("#FFF4E5", "#4A3500"),
            **btn_opts,
        ).pack(fill=ctk.X, padx=30, pady=8)

        ctk.CTkButton(
            self.power_window,
            text=f"🔄 Restart {self.session_name}",
            command=lambda: self.send_power_cmd("SYS_RESTART", "Restart the Remote PC"),
            fg_color=self.bg_card,
            text_color=self.accent_blue,
            hover_color=("#E5F3FF", "#002147"),
            **btn_opts,
        ).pack(fill=ctk.X, padx=30, pady=8)

        ctk.CTkButton(
            self.power_window,
            text=f"🛑 Shut Down {self.session_name}",
            command=lambda: self.send_power_cmd("SYS_SHUTDOWN", "SHUT DOWN the Remote PC"),
            fg_color=self.bg_card,
            text_color=self.accent_red,
            hover_color=("#FDE7E9", "#4A1A1E"),
            **btn_opts,
        ).pack(fill=ctk.X, padx=30, pady=8)

    def send_power_cmd(self, command, action_name):
        if messagebox.askyesno(
            "Destructive Action",
            f"Are you absolutely sure you want to {action_name}?",
            parent=self.power_window,
        ):
            try:
                with self.net_lock:
                    self.client_socket.sendall(command.encode('utf-8'))
                messagebox.showinfo(
                    "Command Sent",
                    "Power command dispatched. Connection will drop shortly.",
                    parent=self.power_window,
                )
                self.power_window.destroy()
                self.disconnect_server()
            except:
                pass
