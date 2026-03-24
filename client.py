# -*- coding: utf-8 -*-
"""
client.py - Entry point cho ứng dụng Remote Control Client.
Toàn bộ logic đã được tách vào package client/.
"""
import customtkinter as ctk

from client.app import RemoteClientApp

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

def apply_resolution_scaling(root):
    # Tính toán hệ số scale dựa trên độ phân giải logic (đã tính DPI của Windows)
    # Lấy màn hình 2K (2560x1440) làm chuẩn thiết kế
    screen_width = root.winfo_screenwidth()
    
    scale_factor = screen_width / 2560.0
    
    # Giới hạn scale để không bị quá nhỏ hoặc quá to
    if scale_factor < 0.7:
        scale_factor = 0.7
    elif scale_factor > 2.0:
        scale_factor = 2.0
        
    ctk.set_widget_scaling(scale_factor)
    ctk.set_window_scaling(scale_factor)

if __name__ == "__main__":
    root = ctk.CTk()
    apply_resolution_scaling(root)
    app = RemoteClientApp(root)
    root.mainloop()
