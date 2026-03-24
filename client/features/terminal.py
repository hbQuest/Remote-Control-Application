# -*- coding: utf-8 -*-
"""
features/terminal.py - Mixin cửa sổ Remote Terminal.
"""
import struct
import threading
import tkinter as tk
import customtkinter as ctk


class TerminalMixin:

    def open_terminal_window(self):
        self.term_window = ctk.CTkToplevel(self.main_window)
        self.term_window.title(f"Remote Terminal - {self.session_name}{self.connection_info}")
        self.term_window.geometry("800x600")
        self.bring_to_front(self.term_window)

        input_frame = ctk.CTkFrame(self.term_window, corner_radius=0)
        input_frame.pack(fill=ctk.X, side=tk.TOP)

        ctk.CTkLabel(input_frame, text="Command:", font=("Arial", 12, "bold")).pack(
            side=tk.LEFT, padx=(15, 5), pady=15
        )

        self.term_entry = ctk.CTkEntry(input_frame, font=("Consolas", 14), corner_radius=6)
        self.term_entry.pack(side=tk.LEFT, fill=ctk.X, expand=True, padx=5)
        self.term_entry.bind("<Return>", self.send_terminal_cmd)

        ctk.CTkButton(
            input_frame, text="Execute", command=self.send_terminal_cmd,
            fg_color=self.accent_blue, font=("Arial", 12, "bold"), width=100, corner_radius=6
        ).pack(side=tk.RIGHT, padx=15)

        self.term_output = ctk.CTkTextbox(
            self.term_window, font=("Consolas", 13), corner_radius=0,
            fg_color=("black", "#121212"), text_color="#00FF00"
        )
        self.term_output.pack(expand=True, fill=ctk.BOTH)
        self.term_output.insert(
            tk.END, f"Terminal session established with {self.session_name}. Ready for input...\n"
        )
        self.term_output.configure(state=tk.DISABLED)

    def send_terminal_cmd(self, event=None):
        cmd = self.term_entry.get().strip()
        if not cmd:
            return
        self.term_entry.delete(0, tk.END)

        self.term_output.configure(state=tk.NORMAL)
        self.term_output.insert(tk.END, f"\n> {cmd}\n")
        self.term_output.insert(tk.END, "Executing...\n")
        self.term_output.yview(tk.END)
        self.term_output.configure(state=tk.DISABLED)

        threading.Thread(target=self.do_send_terminal_cmd, args=(cmd,), daemon=True).start()

    def do_send_terminal_cmd(self, cmd):
        with self.net_lock:
            try:
                self.client_socket.sendall(f"CMD_EXEC:{cmd}".encode('utf-8'))
                raw_msglen = self.recvall(4)
                if not raw_msglen:
                    return
                msglen = struct.unpack('>I', raw_msglen)[0]
                result_output = self.recvall(msglen).decode('utf-8', errors='replace')
                self.main_window.after(0, lambda: self.update_terminal_output(result_output))
            except Exception as e:
                err_msg = str(e)
                self.main_window.after(
                    0, lambda m=err_msg: self.update_terminal_output(f"[NETWORK ERROR]: {m}")
                )

    def update_terminal_output(self, text):
        if hasattr(self, 'term_window') and self.term_window.winfo_exists():
            self.term_output.configure(state=tk.NORMAL)
            self.term_output.delete("end-14c", tk.END)
            self.term_output.insert(tk.END, f"{text}\n")
            self.term_output.yview(tk.END)
            self.term_output.configure(state=tk.DISABLED)
