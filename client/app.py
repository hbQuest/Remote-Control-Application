# -*- coding: utf-8 -*-
"""
app.py - RemoteClientApp: quản lý tab động, mỗi tab là một RemoteSession.
"""
import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox

from client.session import RemoteSession


class RemoteClientApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Remote Control Center")
        self.root.geometry("700x750")

        # Header bar
        header_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        header_frame.pack(fill=ctk.X, padx=20, pady=(15, 5))

        ctk.CTkLabel(header_frame, text="Connections", font=("Arial", 20, "bold")).pack(side=tk.LEFT)

        self.add_pc_btn = ctk.CTkButton(
            header_frame, text="➕ Add PC", command=self.add_new_pc,
            font=("Arial", 13, "bold"), width=100, corner_radius=6
        )
        self.add_pc_btn.pack(side=tk.RIGHT, padx=(10, 0))

        self.close_pc_btn = ctk.CTkButton(
            header_frame,
            text="✖ Close Current PC",
            command=self.close_current_tab,
            font=("Arial", 13, "bold"),
            width=140,
            corner_radius=6,
            fg_color="transparent",
            border_width=1,
            border_color="#D13438",
            text_color="#D13438",
            hover_color=("#FDE7E9", "#4A1A1E"),
        )
        self.close_pc_btn.pack(side=tk.RIGHT)

        # Tab view
        self.tabview = ctk.CTkTabview(self.root, corner_radius=10)
        self.tabview.pack(expand=True, fill=ctk.BOTH, padx=20, pady=(0, 20))

        self.sessions = []
        self.add_new_pc()

    def get_next_pc_number(self):
        """Tìm số PC nhỏ nhất còn trống."""
        used_nums = set()
        for session in self.sessions:
            if session.session_name.startswith("PC "):
                try:
                    used_nums.add(int(session.session_name[3:]))
                except ValueError:
                    pass
        num = 1
        while num in used_nums:
            num += 1
        return num

    def add_new_pc(self):
        session_name = f"PC {self.get_next_pc_number()}"
        self.tabview.add(session_name)
        tab_frame = self.tabview.tab(session_name)
        session = RemoteSession(tab_frame, self, session_name)
        self.sessions.append(session)
        self.tabview.set(session_name)

    def close_current_tab(self):
        current_tab_name = self.tabview.get()
        if not current_tab_name:
            return

        session_to_close = next(
            (s for s in self.sessions if s.session_name == current_tab_name), None
        )
        if session_to_close:
            if session_to_close.client_socket is not None:
                if not messagebox.askyesno(
                    "Confirm Disconnect",
                    f"Session '{current_tab_name}' is currently connected.\n"
                    "Are you sure you want to disconnect and close this tab?",
                    parent=self.root,
                ):
                    return
                session_to_close.disconnect_server()

            current_idx = self.sessions.index(session_to_close)
            next_focus_name = None
            if len(self.sessions) > 1:
                if current_idx > 0:
                    next_focus_name = self.sessions[current_idx - 1].session_name
                else:
                    next_focus_name = self.sessions[1].session_name

            if next_focus_name:
                self.tabview.set(next_focus_name)

            self.sessions.remove(session_to_close)

        try:
            self.tabview.delete(current_tab_name)
        except:
            pass

        if len(self.sessions) == 0:
            self.add_new_pc()
