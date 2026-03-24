# -*- coding: utf-8 -*-
"""
server/app.py - RemoteServerGUI: giao diện server, start/stop, log.
"""
import random
import socket
import subprocess
import threading
import tkinter as tk
import customtkinter as ctk

from server.handlers import handle_client
from server.keylogger import KeyloggerManager

CREATE_NO_WINDOW = 0x08000000


class RemoteServerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Server - Remote Host")
        self.root.geometry("550x580")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close_server)

        self.server_socket = None
        self.is_running = False
        self.keylogger = KeyloggerManager()

        # Track active client connections
        self.active_connections = []
        self.conn_lock = threading.Lock()

        self.local_ip = self.get_local_ip()
        self.selected_port = 9999 # Cố định Port 9999

        # UI
        title_font = ("Arial", 20, "bold")
        normal_font = ("Arial", 13)
        ip_font = ("Consolas", 24, "bold")

        ctk.CTkLabel(root, text="--- SERVER MODE ---", font=title_font).pack(pady=(20, 10))

        info_frame = ctk.CTkFrame(root, corner_radius=15)
        info_frame.pack(fill=ctk.X, padx=30, pady=10)

        ctk.CTkLabel(info_frame, text="Server IP Address:", font=normal_font, text_color="gray").pack(pady=(15, 0))
        self.address_lbl = ctk.CTkLabel(info_frame, text=f"{self.local_ip}", font=ip_font, text_color=("#005FB8", "#60CDFF"))
        self.address_lbl.pack(pady=5)
        ctk.CTkLabel(info_frame, text="(Fixed Port: 9999 - LAN Mode)", font=("Segoe UI Variable Display", 11, "italic"), text_color="gray").pack(pady=(0, 15))

        self.start_btn = ctk.CTkButton(
            root, text="Start Hosting Session", command=self.start_server,
            font=("Arial", 15, "bold"), height=50, corner_radius=10,
            fg_color="#107C10", hover_color="#0B5A0B"
        )
        self.start_btn.pack(fill=ctk.X, padx=30, pady=15)

        ctk.CTkLabel(root, text="Activity Log:", font=("Arial", 14, "bold")).pack(anchor="w", padx=30)
        self.log_area = ctk.CTkTextbox(
            root, font=("Consolas", 12), corner_radius=10,
            fg_color=("#F0F0F0", "#1E1E1E")
        )
        self.log_area.pack(expand=True, fill=ctk.BOTH, padx=30, pady=(5, 20))
        self.log_area.configure(state="disabled")

    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

    def get_random_valid_port(self):
        while True:
            port = random.randint(9900, 9999)
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(('localhost', port)) != 0:
                    return port

    def log(self, message):
        self.log_area.configure(state="normal")
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.yview(tk.END)
        self.log_area.configure(state="disabled")

    def setup_firewall_rule(self, port, action="add"):
        rule_name = f"Remote_Tool_Port_{port}"
        if action == "add":
            cmd = f'New-NetFirewallRule -DisplayName "{rule_name}" -Direction Inbound -LocalPort {port} -Protocol TCP -Action Allow'
            msg_success = f"[*] Firewall opened for Port {port}."
        else:
            cmd = f'Remove-NetFirewallRule -DisplayName "{rule_name}"'
            msg_success = f"[*] Firewall rule removed for Port {port}."
        try:
            result = subprocess.run(
                ["powershell", "-Command", cmd],
                capture_output=True, text=True, errors='replace', creationflags=CREATE_NO_WINDOW
            )
            if result.returncode == 0:
                self.log(msg_success)
            else:
                self.log("[!] Firewall warning: Admin rights needed.")
        except Exception as e:
            self.log(f"[!] Firewall script failed: {e}")

    def start_server(self):
        if not self.is_running:
            self.start_btn.configure(
                text="Stop Listening", fg_color="#D13438",
                hover_color="#4A1A1E", text_color="white"
            )
            self.is_running = True
            self.setup_firewall_rule(self.selected_port, action="add")
            threading.Thread(target=self.run_network_server, daemon=True).start()
            self.log("[*] Server started, waiting for connections...")
        else:
            self.stop_server()

    def stop_server(self):
        self.is_running = False
        with self.conn_lock:
            for conn in self.active_connections:
                try:
                    conn.sendall(b"SERVER_STOPPING")
                    conn.close()
                except:
                    pass
            self.active_connections = []
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
            self.server_socket = None
        self.setup_firewall_rule(self.selected_port, action="remove")
        self.log("[*] Server stopped listening. All clients disconnected.")
        self.start_btn.configure(
            text="Start Hosting Session", fg_color="#107C10",
            hover_color="#0B5A0B", text_color="white"
        )

    def on_close_server(self):
        self.is_running = False
        if hasattr(self, 'selected_port') and self.selected_port:
            self.setup_firewall_rule(self.selected_port, action="remove")
        self.root.destroy()

    def run_network_server(self):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('0.0.0.0', self.selected_port))
            self.server_socket.listen(2)
            self.log(f"[*] Waiting for connection at {self.local_ip}:{self.selected_port}...")

            server_state = {
                'is_running': self.is_running,
                'keylogger': self.keylogger,
            }

            while self.is_running:
                self.server_socket.settimeout(1.0)
                server_state['is_running'] = self.is_running
                try:
                    conn, addr = self.server_socket.accept()
                    conn.settimeout(None)
                    self.log(f"[+] Client connected from: {addr[0]}:{addr[1]}")
                    with self.conn_lock:
                        self.active_connections.append(conn)
                    # Tạo server_state riêng cho từng client (giữ tham chiếu is_running qua lambda)
                    client_state = {
                        'is_running': True,
                        'keylogger': self.keylogger,
                    }
                    # Dùng wrapper để cập nhật is_running theo server
                    def make_client_thread(c, a, cs):
                        def _run():
                            while self.is_running and cs['is_running']:
                                cs['is_running'] = self.is_running
                            # Thực ra handle_client tự kiểm is_running qua server_state
                        handle_client(c, a, {'is_running': True, 'keylogger': self.keylogger}, self.log)
                        with self.conn_lock:
                            if c in self.active_connections:
                                self.active_connections.remove(c)
                    threading.Thread(target=make_client_thread, args=(conn, addr, client_state), daemon=True).start()
                except socket.timeout:
                    continue
        except Exception as e:
            self.log(f"[-] Server Error: {e}")
            self.start_btn.configure(state=tk.NORMAL, text="Start Hosting Session", fg_color="#107C10", text_color="white")
        finally:
            with self.conn_lock:
                for conn in self.active_connections:
                    try:
                        conn.close()
                    except:
                        pass
                self.active_connections = []
