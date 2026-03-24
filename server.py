# -*- coding: utf-8 -*-
"""
server.py - Entry point cho ứng dụng Remote Control Server.
Toàn bộ logic đã được tách vào package server/.
"""
import ctypes
import sys

# Tự động ẩn cửa sổ Terminal (Console) đen khi chạy trên Windows
try:
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
except:
    pass

# Tự động xin quyền Administrator
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if not is_admin():
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
    sys.exit()

import customtkinter as ctk
from server.app import RemoteServerGUI

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

def apply_resolution_scaling(root):
    # Tính toán hệ số scale dựa trên độ phân giải logic của màn hình
    # Lấy màn hình 2K (2560x1440) làm chuẩn thiết kế
    screen_width = root.winfo_screenwidth()
    scale_factor = screen_width / 2560.0
    
    if scale_factor < 0.7:
        scale_factor = 0.7
    elif scale_factor > 2.0:
        scale_factor = 2.0
        
    ctk.set_widget_scaling(scale_factor)
    ctk.set_window_scaling(scale_factor)

if __name__ == "__main__":
    root = ctk.CTk()
    apply_resolution_scaling(root)
    app = RemoteServerGUI(root)
    root.mainloop()