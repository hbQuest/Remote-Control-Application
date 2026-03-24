# -*- coding: utf-8 -*-
"""
features/webcam.py - Mixin Webcam Capture: nhận stream webcam, snapshot, record video.
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


class WebcamMixin:

    def open_webcam_window(self):
        self.disable_main_buttons()
        self.webcam_window = ctk.CTkToplevel(self.main_window)
        self.webcam_window.title(
            f"Webcam Capture - {self.session_name}{self.connection_info}"
        )
        self.webcam_window.geometry("750x600")
        self.webcam_window.protocol("WM_DELETE_WINDOW", self.on_close_webcam_window)
        self.bring_to_front(self.webcam_window)

        self.is_recording_webcam = False
        self.video_writer = None
        self.record_start_time = 0

        tool_frame = ctk.CTkFrame(
            self.webcam_window, corner_radius=0, fg_color=("#1D1D1F", "#1D1D1F")
        )
        tool_frame.pack(fill=ctk.X, side=tk.TOP)

        self.record_btn = ctk.CTkButton(
            tool_frame, text="⏺ Record Video", command=self.toggle_record_webcam,
            fg_color="transparent", text_color="#FF453A", hover_color="#4A1A1E",
            border_width=1, border_color="#FF453A",
        )
        self.record_btn.pack(side=tk.LEFT, padx=15, pady=10)

        self.cam_status_lbl = ctk.CTkLabel(
            tool_frame, text="", text_color="#FF453A", font=("Arial", 13, "bold")
        )
        self.cam_status_lbl.pack(side=tk.LEFT, padx=10, pady=10)

        ctk.CTkButton(
            tool_frame, text="Close", command=self.on_close_webcam_window,
            fg_color="transparent", text_color="#FF453A", hover_color="#4A1A1E", width=80,
        ).pack(side=tk.RIGHT, padx=15, pady=10)

        self.snapshot_btn = ctk.CTkButton(
            tool_frame, text="📸 Snapshot", command=self.save_webcam_snapshot,
            fg_color="transparent", text_color="#0A84FF", hover_color="#002147",
            border_width=1, border_color="#0A84FF",
        )
        self.snapshot_btn.pack(side=tk.RIGHT, padx=5, pady=10)

        self.cam_label = ctk.CTkLabel(
            self.webcam_window,
            text=f"Accessing Webcam on {self.session_name}...",
            text_color="#86868B",
            font=("Arial", 14),
        )
        self.cam_label.pack(expand=True, fill=ctk.BOTH)

        self.is_webcam_streaming = True
        with self.net_lock:
            try:
                self.client_socket.sendall("START_WEBCAM".encode('utf-8'))
            except:
                pass
        threading.Thread(target=self.receive_webcam_stream, daemon=True).start()

    def update_record_timer(self):
        if (
            self.is_recording_webcam
            and hasattr(self, 'cam_status_lbl')
            and self.cam_status_lbl.winfo_exists()
        ):
            elapsed = int(time.time() - self.record_start_time)
            mins, secs = divmod(elapsed, 60)
            hours, mins = divmod(mins, 60)
            self.cam_status_lbl.configure(
                text=f"Đang quay... {hours:02d}:{mins:02d}:{secs:02d}"
            )
            self.main_window.after(1000, self.update_record_timer)

    def toggle_record_webcam(self):
        if not self.is_recording_webcam:
            if self.current_webcam_frame:
                self.is_recording_webcam = True
                self.record_start_time = time.time()
                self.record_btn.configure(
                    text="⏹ Stop Recording", text_color="#0A84FF",
                    border_color="#0A84FF", hover_color="#002147",
                )
                self.update_record_timer()
            else:
                messagebox.showwarning(
                    "Wait", "Waiting for video stream to start...", parent=self.webcam_window
                )
        else:
            self.is_recording_webcam = False
            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None
            self.record_btn.configure(
                text="⏺ Record Video", text_color="#FF453A",
                border_color="#FF453A", hover_color="#4A1A1E",
            )
            self.cam_status_lbl.configure(text="")

            if os.path.exists(self.temp_video_path):
                filepath = filedialog.asksaveasfilename(
                    defaultextension=".avi", filetypes=[("AVI Video", "*.avi")],
                    title="Save Recorded Video As", parent=self.webcam_window,
                )
                if filepath:
                    try:
                        shutil.move(self.temp_video_path, filepath)
                        messagebox.showinfo(
                            "Saved", f"Video saved successfully:\n{filepath}",
                            parent=self.webcam_window,
                        )
                    except Exception as e:
                        messagebox.showerror(
                            "Error", f"Could not save video: {e}", parent=self.webcam_window
                        )
                else:
                    os.remove(self.temp_video_path)

    def receive_webcam_stream(self):
        while self.is_webcam_streaming:
            try:
                ready, _, _ = select.select([self.client_socket], [], [], 0.5)
                if not ready:
                    continue
                with self.net_lock:
                    if not self.is_webcam_streaming:
                        break
                    raw_msglen = self.recvall(4)
                    if not raw_msglen:
                        break
                    msglen = struct.unpack('>I', raw_msglen)[0]
                    image_data = self.recvall(msglen)
                    if not image_data:
                        break

                img = Image.open(io.BytesIO(image_data))
                self.current_webcam_frame = img.copy()

                if self.is_recording_webcam:
                    if self.video_writer is None:
                        width, height = img.size
                        fourcc = cv2.VideoWriter_fourcc(*'XVID')
                        self.video_writer = cv2.VideoWriter(
                            self.temp_video_path, fourcc, 20.0, (width, height)
                        )
                    cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                    self.video_writer.write(cv_img)

                lbl_w = self.cam_label.winfo_width()
                lbl_h = self.cam_label.winfo_height()
                if lbl_w > 10 and lbl_h > 10:
                    display_img = ImageOps.contain(img, (lbl_w, lbl_h), Image.Resampling.LANCZOS)
                else:
                    display_img = img

                tk_image = ImageTk.PhotoImage(display_img)
                self.main_window.after(
                    0, lambda img=tk_image: self.update_video_label(img, self.cam_label)
                )
            except:
                break

    def save_webcam_snapshot(self):
        if self.current_webcam_frame:
            filepath = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG Image", "*.png"), ("JPEG Image", "*.jpg")],
                title="Save Snapshot As",
            )
            if filepath:
                self.current_webcam_frame.save(filepath)
                messagebox.showinfo(
                    "Success", f"Snapshot saved to:\n{filepath}", parent=self.webcam_window
                )

    def on_close_webcam_window(self):
        self.is_webcam_streaming = False
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None
        if hasattr(self, 'temp_video_path') and os.path.exists(self.temp_video_path):
            try:
                os.remove(self.temp_video_path)
            except:
                pass

        with self.net_lock:
            try:
                self.client_socket.sendall("STOP_WEBCAM".encode('utf-8'))
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
        self.webcam_window.destroy()
        self.enable_main_buttons()
