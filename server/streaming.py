# -*- coding: utf-8 -*-
"""
server/streaming.py - Logic stream màn hình và webcam gửi tới client.
"""
import io
import struct
import time

from PIL import ImageGrab

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False


def stream_screen(conn, is_streaming_ref):
    """
    Gửi liên tục ảnh chụp màn hình sang client.
    is_streaming_ref: list[bool] để stop từ bên ngoài.
    """
    while is_streaming_ref[0]:
        try:
            screenshot = ImageGrab.grab()
            screenshot.thumbnail((1920, 1080))
            img_bytes = io.BytesIO()
            screenshot.save(img_bytes, format='JPEG', quality=65)
            img_data = img_bytes.getvalue()
            conn.sendall(struct.pack('>I', len(img_data)))
            conn.sendall(img_data)
            time.sleep(0.1)
        except:
            is_streaming_ref[0] = False
            break


def stream_webcam(conn, is_streaming_ref, log_fn=None):
    """
    Gửi liên tục frame webcam sang client.
    is_streaming_ref: list[bool] để stop từ bên ngoài.
    """
    if not HAS_CV2:
        is_streaming_ref[0] = False
        return

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        if log_fn:
            log_fn("[-] Cannot open webcam. Hardware might be missing.")
        is_streaming_ref[0] = False
        return

    while is_streaming_ref[0]:
        try:
            ret, frame = cap.read()
            if not ret:
                break
            frame = cv2.resize(frame, (960, 720))
            _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
            img_data = buffer.tobytes()
            conn.sendall(struct.pack('>I', len(img_data)))
            conn.sendall(img_data)
            time.sleep(0.05)
        except:
            is_streaming_ref[0] = False
            break

    cap.release()
