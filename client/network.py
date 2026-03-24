# -*- coding: utf-8 -*-
"""
network.py - Mixin xử lý mạng: recvall, heartbeat, phát hiện ngắt kết nối.
Được RemoteSession thừa kế.
"""
import socket
import time
import threading
from tkinter import messagebox
import select


class NetworkMixin:
    """Cung cấp các phương thức mạng cốt lõi cho RemoteSession."""

    def recvall(self, n):
        """Nhận đúng n bytes từ socket."""
        data = bytearray()
        while len(data) < n:
            packet = self.client_socket.recv(n - len(data))
            if not packet:
                return None
            if b"SERVER_STOPPING" in packet:
                self.main_window.after(0, self._show_server_stopped_and_disconnect)
                return None
            data.extend(packet)
        return data

    def _show_server_stopped_and_disconnect(self):
        """Hiển thị cảnh báo và ngắt kết nối khi server dừng."""
        if not self._server_stopping:
            self._server_stopping = True
            messagebox.showwarning(
                "Server Stopped",
                "Server has stopped listening. Connection closed."
            )
            self.disconnect_server()

    def _heartbeat_loop(self):
        """Thread nền kiểm tra xem server có còn kết nối không."""
        while self._is_heartbeat_running and self.client_socket:
            try:
                # Dùng select với timeout 1s để kiểm tra trạng thái socket
                ready_to_read, _, _ = select.select([self.client_socket], [], [], 1.0)
                if ready_to_read:
                    # Dùng MSG_PEEK để không lấy mất dữ liệu của thread khác
                    data = self.client_socket.recv(1024, socket.MSG_PEEK)
                    if data and b"SERVER_STOPPING" in data:
                        # Lấy thông điệp ra khỏi buffer
                        self.client_socket.recv(len(data))
                        self.main_window.after(0, self._show_server_stopped_and_disconnect)
                        break
                    elif not data:
                        # Server đã ngắt kết nối
                        self.main_window.after(0, self._show_server_stopped_and_disconnect)
                        break
                else:
                    # Timeout của select, chờ vòng lặp tiếp theo
                    time.sleep(2)
            except (OSError, socket.error):
                if self._is_heartbeat_running and not self._server_stopping:
                    self.main_window.after(0, self._show_server_stopped_and_disconnect)
                break
            except Exception:
                break
