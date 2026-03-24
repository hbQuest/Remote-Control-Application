# -*- coding: utf-8 -*-
"""
features/screen.py - Mixin Screen Mirroring: nhận stream video màn hình, record, screenshot.
"""
import io
import os
import struct
import select
import time
import threading
import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox, filedialog
from PIL import Image, ImageTk, ImageOps
import cv2
import numpy as np
import shutil


class ScreenMirrorMixin:

    def open_stream_window(self):
        self.disable_main_buttons()
        self.stream_window = ctk.CTkToplevel(self.main_window)
        self.stream_window.title(
            f"Screen Mirroring - {self.session_name}{self.connection_info}"
        )
        self.stream_window.geometry("960x650")
        self.stream_window.protocol("WM_DELETE_WINDOW", self.on_close_stream_window)
        self.bring_to_front(self.stream_window)

        self.is_paused = False
        self.is_recording_stream = False
        self.stream_video_writer = None

        tool_frame = ctk.CTkFrame(
            self.stream_window, corner_radius=0, fg_color=("#1D1D1F", "#1D1D1F")
        )
        tool_frame.pack(fill=ctk.X, side=tk.TOP)

        self.pause_btn = ctk.CTkButton(
            tool_frame, text="⏸ Freeze Frame", command=self.toggle_pause_stream,
            fg_color="transparent", text_color="#FFCC00", hover_color="#332B00",
            border_width=1, border_color="#FFCC00",
        )
        self.pause_btn.pack(side=tk.LEFT, padx=15, pady=10)

        self.stream_record_btn = ctk.CTkButton(
            tool_frame, text="⏺ Record Screen", command=self.toggle_record_stream,
            fg_color="transparent", text_color="#FF453A", hover_color="#4A1A1E",
            border_width=1, border_color="#FF453A",
        )
        self.stream_record_btn.pack(side=tk.LEFT, padx=5, pady=10)

        self.stream_status_lbl = ctk.CTkLabel(
            tool_frame, text="", text_color="#FF453A", font=("Arial", 13, "bold")
        )
        self.stream_status_lbl.pack(side=tk.LEFT, padx=10, pady=10)

        ctk.CTkButton(
            tool_frame, text="Close", command=self.on_close_stream_window,
            fg_color="transparent", text_color="#FF453A", hover_color="#4A1A1E", width=80,
        ).pack(side=tk.RIGHT, padx=15, pady=10)

        self.save_btn = ctk.CTkButton(
            tool_frame, text="📸 Save Screenshot", command=self.save_screenshot,
            fg_color="transparent", text_color="#0A84FF", hover_color="#002147",
            border_width=1, border_color="#0A84FF",
        )
        self.save_btn.pack(side=tk.RIGHT, padx=5, pady=10)

        self.video_label = ctk.CTkLabel(
            self.stream_window,
            text=f"Establishing connection to {self.session_name} display...",
            text_color="#86868B",
            font=("Arial", 14),
        )
        self.video_label.pack(expand=True, fill=ctk.BOTH)

        self.is_viewing_stream = True
        with self.net_lock:
            try:
                self.client_socket.sendall("START_STREAM".encode('utf-8'))
            except:
                pass
        threading.Thread(target=self.receive_video_stream, daemon=True).start()

    def update_stream_record_timer(self):
        if (
            self.is_recording_stream
            and hasattr(self, 'stream_status_lbl')
            and self.stream_status_lbl.winfo_exists()
        ):
            elapsed = int(time.time() - self.stream_record_start_time)
            mins, secs = divmod(elapsed, 60)
            hours, mins = divmod(mins, 60)
            self.stream_status_lbl.configure(
                text=f"Đang quay... {hours:02d}:{mins:02d}:{secs:02d}"
            )
            self.main_window.after(1000, self.update_stream_record_timer)

    def toggle_record_stream(self):
        if not self.is_recording_stream:
            if self.current_frame:
                self.is_recording_stream = True
                self.stream_record_start_time = time.time()
                self.stream_record_btn.configure(
                    text="⏹ Stop Recording", text_color="#0A84FF",
                    border_color="#0A84FF", hover_color="#002147",
                )
                self.update_stream_record_timer()
            else:
                messagebox.showwarning(
                    "Wait", "Waiting for video stream to start...", parent=self.stream_window
                )
        else:
            self.is_recording_stream = False
            if self.stream_video_writer:
                self.stream_video_writer.release()
                self.stream_video_writer = None
            self.stream_record_btn.configure(
                text="⏺ Record Screen", text_color="#FF453A",
                border_color="#FF453A", hover_color="#4A1A1E",
            )
            self.stream_status_lbl.configure(text="")

            if os.path.exists(self.stream_temp_video_path):
                filepath = filedialog.asksaveasfilename(
                    defaultextension=".avi", filetypes=[("AVI Video", "*.avi")],
                    title="Save Recorded Screen As", parent=self.stream_window,
                )
                if filepath:
                    try:
                        shutil.move(self.stream_temp_video_path, filepath)
                        messagebox.showinfo(
                            "Saved",
                            f"Screen recording saved successfully:\n{filepath}",
                            parent=self.stream_window,
                        )
                    except Exception as e:
                        messagebox.showerror(
                            "Error", f"Could not save video: {e}", parent=self.stream_window
                        )
                else:
                    os.remove(self.stream_temp_video_path)

    def toggle_pause_stream(self):
        if not self.is_paused:
            self.is_paused = True
            self.pause_btn.configure(
                text="▶ Resume", text_color="#34C759",
                border_color="#34C759", hover_color="#0D2A14",
            )
        else:
            self.is_paused = False
            self.pause_btn.configure(
                text="⏸ Freeze Frame", text_color="#FFCC00",
                border_color="#FFCC00", hover_color="#332B00",
            )

    def update_video_label(self, tk_image, target_label):
        if target_label.winfo_exists():
            target_label.configure(image=tk_image, text="")
            target_label.image = tk_image

    def receive_video_stream(self):
        while self.is_viewing_stream:
            try:
                ready, _, _ = select.select([self.client_socket], [], [], 0.5)
                if not ready:
                    continue
                with self.net_lock:
                    if not self.is_viewing_stream:
                        break
                    raw_msglen = self.recvall(4)
                    if not raw_msglen:
                        break
                    msglen = struct.unpack('>I', raw_msglen)[0]
                    image_data = self.recvall(msglen)
                    if not image_data:
                        break

                if not self.is_paused:
                    img = Image.open(io.BytesIO(image_data))
                    self.current_frame = img.copy()

                    if self.is_recording_stream:
                        if self.stream_video_writer is None:
                            width, height = img.size
                            fourcc = cv2.VideoWriter_fourcc(*'XVID')
                            self.stream_video_writer = cv2.VideoWriter(
                                self.stream_temp_video_path, fourcc, 10.0, (width, height)
                            )
                        cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                        self.stream_video_writer.write(cv_img)

                    lbl_w = self.video_label.winfo_width()
                    lbl_h = self.video_label.winfo_height()
                    if lbl_w > 10 and lbl_h > 10:
                        display_img = ImageOps.contain(img, (lbl_w, lbl_h), Image.Resampling.LANCZOS)
                    else:
                        display_img = img

                    tk_image = ImageTk.PhotoImage(display_img)
                    self.main_window.after(
                        0, lambda img=tk_image: self.update_video_label(img, self.video_label)
                    )
            except:
                break

    def on_close_stream_window(self):
        self.is_viewing_stream = False
        self.is_paused = False

        if getattr(self, 'stream_video_writer', None):
            self.stream_video_writer.release()
            self.stream_video_writer = None
        if hasattr(self, 'stream_temp_video_path') and os.path.exists(self.stream_temp_video_path):
            try:
                os.remove(self.stream_temp_video_path)
            except:
                pass

        if self.client_socket:
            with self.net_lock:
                try:
                    self.client_socket.sendall("STOP_STREAM".encode('utf-8'))
                    time.sleep(0.3)
                    self.client_socket.setblocking(0)
                    try:
                        while self.client_socket.recv(8192):
                            pass
                    except BlockingIOError:
                        pass
                    self.client_socket.setblocking(1)
                except:
                    pass
        self.stream_window.destroy()
        self.enable_main_buttons()

    def save_screenshot(self):
        if self.current_frame:
            filepath = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG Image", "*.png"), ("JPEG Image", "*.jpg")],
                title="Save Screenshot As",
            )
            if filepath:
                self.current_frame.save(filepath)
                messagebox.showinfo(
                    "Success", f"Screenshot saved to:\n{filepath}", parent=self.stream_window
                )
