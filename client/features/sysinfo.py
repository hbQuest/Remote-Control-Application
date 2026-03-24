# -*- coding: utf-8 -*-
"""
features/sysinfo.py - Mixin hiển thị thông tin hệ thống máy chủ từ xa.
"""
import struct
import threading
from tkinter import messagebox


class SysInfoMixin:

    def request_sysinfo(self):
        self.sysinfo_btn.configure(state="disabled")
        threading.Thread(target=self.do_request_sysinfo, daemon=True).start()

    def do_request_sysinfo(self):
        with self.net_lock:
            try:
                self.client_socket.sendall(b"GET_SYSINFO")
                raw_msglen = self.recvall(4)
                if raw_msglen:
                    msglen = struct.unpack('>I', raw_msglen)[0]
                    sysinfo_data = self.recvall(msglen).decode('utf-8', errors='replace')
                    self.main_window.after(
                        0,
                        lambda: messagebox.showinfo(
                            f"System Information - {self.session_name}", sysinfo_data
                        )
                    )
            except Exception as e:
                err_msg = str(e)
                self.main_window.after(
                    0,
                    lambda m=err_msg: messagebox.showerror(
                        "Network Error", f"Failed to retrieve system info: {m}"
                    )
                )
        self.main_window.after(0, lambda: self.sysinfo_btn.configure(state="normal"))
