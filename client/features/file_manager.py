# -*- coding: utf-8 -*-
"""
features/file_manager.py - Mixin File Manager: duyệt thư mục, download, upload, open file.
"""
import os
import struct
import time
import threading
import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox, filedialog


class FileManagerMixin:

    def open_file_explorer(self):
        self.disable_main_buttons()
        self.file_window = ctk.CTkToplevel(self.main_window)
        self.file_window.title(f"File Manager - {self.session_name}{self.connection_info}")
        self.file_window.geometry("900x700")
        self.file_window.protocol("WM_DELETE_WINDOW", self.on_close_file_window)
        self.bring_to_front(self.file_window)
        self.last_valid_path = "C:\\"

        path_frame = ctk.CTkFrame(self.file_window, corner_radius=10)
        path_frame.pack(fill=ctk.X, padx=20, pady=15)

        ctk.CTkButton(
            path_frame, text="⬆ Up", command=self.go_up_dir,
            fg_color="transparent", border_width=1, width=60, text_color=("black", "white")
        ).pack(side=tk.LEFT, padx=(15, 5), pady=15)

        self.path_entry = ctk.CTkEntry(path_frame, font=("Consolas", 13), corner_radius=6)
        self.path_entry.pack(side=tk.LEFT, fill=ctk.X, expand=True, padx=5)
        self.path_entry.insert(0, "C:\\")
        self.path_entry.bind("<Return>", lambda e: self.refresh_file_list())

        ctk.CTkButton(
            path_frame, text="Go", command=self.refresh_file_list,
            fg_color=self.accent_blue, width=60
        ).pack(side=tk.LEFT, padx=5)
        ctk.CTkButton(
            path_frame, text="Close", command=self.on_close_file_window,
            fg_color="transparent", hover_color=("#FDE7E9", "#4A1A1E"),
            text_color=self.accent_red, width=60
        ).pack(side=tk.RIGHT, padx=15)

        header = ctk.CTkFrame(self.file_window, corner_radius=6, fg_color=self.bg_card)
        header.pack(fill=ctk.X, padx=20)
        header.grid_columnconfigure(0, weight=0)
        header.grid_columnconfigure(1, weight=5)
        header.grid_columnconfigure(2, weight=2)
        header.grid_columnconfigure(3, weight=0, minsize=120)

        font_header = ("Arial", 12, "bold")
        ctk.CTkLabel(header, text="Type", anchor="w", text_color=self.text_muted, font=font_header).grid(row=0, column=0, padx=10, pady=5, sticky="w")
        ctk.CTkLabel(header, text="Name", anchor="w", text_color=self.text_muted, font=font_header).grid(row=0, column=1, padx=10, pady=5, sticky="w")
        ctk.CTkLabel(header, text="Size", anchor="w", text_color=self.text_muted, font=font_header).grid(row=0, column=2, padx=10, pady=5, sticky="w")
        ctk.CTkLabel(header, text="Action", anchor="center", text_color=self.text_muted, font=font_header).grid(row=0, column=3, padx=10, pady=5, sticky="ew")

        self.f_scrollable_frame = ctk.CTkScrollableFrame(
            self.file_window, corner_radius=10, fg_color=self.bg_card
        )
        self.f_scrollable_frame.pack(expand=True, fill=ctk.BOTH, padx=20, pady=(10, 15))

        upload_frame = ctk.CTkFrame(self.file_window, fg_color="transparent")
        upload_frame.pack(fill=ctk.X, padx=20, pady=(0, 15))
        ctk.CTkButton(
            upload_frame,
            text=f"📤 Upload File to {self.session_name}",
            command=self.upload_file,
            fg_color=self.bg_card,
            text_color=self.accent_blue,
            font=("Arial", 13, "bold"),
            corner_radius=8,
            height=40,
        ).pack(side=tk.LEFT)

        self.refresh_file_list()

    def on_close_file_window(self):
        self.file_window.destroy()
        self.enable_main_buttons()

    def get_full_path(self, base, item):
        base = base.strip()
        if not base.endswith("\\") and not base.endswith("/"):
            base += "\\"
        return base + item

    def go_up_dir(self):
        current = self.path_entry.get().strip()
        if current:
            parent = os.path.dirname(current.rstrip("\\/"))
            if not parent or parent == current.rstrip("\\/"):
                parent = current
            if not parent.endswith("\\") and len(parent) == 2 and parent[1] == ':':
                parent += "\\"
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, parent)
            self.refresh_file_list()

    def format_size(self, size_bytes):
        if size_bytes == 0:
            return ""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes/1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes/(1024*1024):.1f} MB"
        else:
            return f"{size_bytes/(1024*1024*1024):.2f} GB"

    def refresh_file_list(self):
        for w in self.f_scrollable_frame.winfo_children():
            w.destroy()
        ctk.CTkLabel(
            self.f_scrollable_frame, text="Loading directory contents...",
            text_color=self.text_muted
        ).pack(pady=20)
        path = self.path_entry.get().strip()
        threading.Thread(target=self.fetch_file_data, args=(path,), daemon=True).start()

    def fetch_file_data(self, path):
        with self.net_lock:
            try:
                self.client_socket.sendall(f"FILE_LIST:{path}".encode('utf-8'))
                raw_msglen = self.recvall(4)
                if not raw_msglen:
                    return
                msglen = struct.unpack('>I', raw_msglen)[0]
                data = self.recvall(msglen).decode('utf-8', errors='replace')
                self.main_window.after(0, self.render_file_list, data, path)
            except:
                pass

    def select_file_item(self, item_name, event=None):
        full_path = self.get_full_path(self.last_valid_path, item_name)
        self.path_entry.delete(0, tk.END)
        self.path_entry.insert(0, full_path)

    def enter_folder(self, folder_name, event=None):
        new_path = self.get_full_path(self.last_valid_path, folder_name)
        self.path_entry.delete(0, tk.END)
        self.path_entry.insert(0, new_path)
        self.refresh_file_list()

    def render_file_list(self, data, current_path):
        for w in self.f_scrollable_frame.winfo_children():
            w.destroy()

        if data.startswith("ERROR|"):
            _, err, _ = data.split("|", 2)
            ctk.CTkLabel(
                self.f_scrollable_frame,
                text=f"Access Denied: {err}",
                text_color=self.accent_red,
            ).pack(pady=20)
            return

        self.last_valid_path = current_path
        lines = data.split("\n")
        dirs, files = [], []
        for line in lines:
            if not line:
                continue
            parts = line.split("|", 2)
            if len(parts) == 3:
                if parts[0] == "DIR":
                    dirs.append(parts)
                else:
                    files.append(parts)

        font_item = ("Arial", 13)
        font_bold = ("Arial", 13, "bold")

        for t, name, _ in dirs:
            row = ctk.CTkFrame(self.f_scrollable_frame, fg_color="transparent")
            row.pack(fill=ctk.X, pady=1)
            row.grid_columnconfigure(0, weight=0)
            row.grid_columnconfigure(1, weight=5)
            row.grid_columnconfigure(2, weight=2)
            row.grid_columnconfigure(3, weight=0, minsize=120)

            icon_lbl = ctk.CTkLabel(row, text="📁", font=font_item, cursor="hand2")
            icon_lbl.grid(row=0, column=0, padx=10, sticky="w")
            name_lbl = ctk.CTkLabel(row, text=self._truncate(name, 50), anchor="w", font=font_bold, cursor="hand2")
            name_lbl.grid(row=0, column=1, padx=10, sticky="w")

            icon_lbl.bind("<Double-Button-1>", lambda e, n=name: self.enter_folder(n))
            name_lbl.bind("<Double-Button-1>", lambda e, n=name: self.enter_folder(n))
            icon_lbl.bind("<Button-1>", lambda e, n=name: self.select_file_item(n))
            name_lbl.bind("<Button-1>", lambda e, n=name: self.select_file_item(n))

            ctk.CTkLabel(row, text="", anchor="w").grid(row=0, column=2, padx=10, sticky="w")

            action_frame = ctk.CTkFrame(row, fg_color="transparent")
            action_frame.grid(row=0, column=3, sticky="ew")
            ctk.CTkButton(
                action_frame, text="Open", fg_color="transparent",
                text_color=self.accent_blue, font=font_bold, width=80,
                command=lambda n=name: self.enter_folder(n)
            ).pack()

        for t, name, size in files:
            row = ctk.CTkFrame(self.f_scrollable_frame, fg_color="transparent")
            row.pack(fill=ctk.X, pady=1)
            row.grid_columnconfigure(0, weight=0)
            row.grid_columnconfigure(1, weight=5)
            row.grid_columnconfigure(2, weight=2)
            row.grid_columnconfigure(3, weight=0, minsize=120)

            icon_lbl = ctk.CTkLabel(row, text="📄", font=font_item, cursor="hand2")
            icon_lbl.grid(row=0, column=0, padx=10, sticky="w")
            name_lbl = ctk.CTkLabel(row, text=self._truncate(name, 50), anchor="w", font=font_item, cursor="hand2")
            name_lbl.grid(row=0, column=1, padx=10, sticky="w")

            icon_lbl.bind("<Double-Button-1>", lambda e, n=name: self.open_file_on_server(n))
            name_lbl.bind("<Double-Button-1>", lambda e, n=name: self.open_file_on_server(n))
            icon_lbl.bind("<Button-1>", lambda e, n=name: self.select_file_item(n))
            name_lbl.bind("<Button-1>", lambda e, n=name: self.select_file_item(n))

            ctk.CTkLabel(
                row, text=self.format_size(int(size)), anchor="w",
                text_color=self.text_muted, font=font_item
            ).grid(row=0, column=2, padx=10, sticky="w")

            action_frame = ctk.CTkFrame(row, fg_color="transparent")
            action_frame.grid(row=0, column=3, sticky="ew")
            ctk.CTkButton(
                action_frame, text="Download", fg_color="transparent", border_width=1,
                width=80, text_color=("black", "white"), font=font_item,
                command=lambda n=name: self.download_file(n)
            ).pack()

    def open_file_on_server(self, filename, event=None):
        full_path = self.get_full_path(self.last_valid_path, filename)
        if messagebox.askyesno(
            "Open File",
            f"Execute/Open this file on {self.session_name}?\n\n{full_path}",
            parent=self.file_window,
        ):
            threading.Thread(
                target=self.do_open_file_on_server, args=(full_path,), daemon=True
            ).start()

    def do_open_file_on_server(self, full_path):
        with self.net_lock:
            try:
                self.client_socket.sendall(f"START_PROCESS:{full_path}".encode('utf-8'))
                raw_msglen = self.recvall(4)
                if not raw_msglen:
                    return
                msglen = struct.unpack('>I', raw_msglen)[0]
                response = self.recvall(msglen).decode('utf-8', errors='replace')
                self.main_window.after(
                    0,
                    lambda: messagebox.showinfo("Execution Result", response, parent=self.file_window),
                )
            except:
                pass

    def download_file(self, filename):
        save_path = filedialog.asksaveasfilename(initialfile=filename, title="Save Downloaded File")
        if not save_path:
            return
        server_path = self.get_full_path(self.last_valid_path, filename)
        threading.Thread(target=self.do_download, args=(server_path, save_path), daemon=True).start()

    def do_download(self, server_path, save_path):
        with self.net_lock:
            try:
                self.client_socket.sendall(f"FILE_DOWNLOAD:{server_path}".encode('utf-8'))
                raw_msglen = self.recvall(4)
                if not raw_msglen:
                    return
                msglen = struct.unpack('>I', raw_msglen)[0]
                status = self.recvall(msglen)

                if status == b"SUCCESS":
                    raw_filelen = self.recvall(4)
                    filelen = struct.unpack('>I', raw_filelen)[0]
                    file_data = self.recvall(filelen)
                    with open(save_path, 'wb') as f:
                        f.write(file_data)
                    self.main_window.after(
                        0,
                        lambda: messagebox.showinfo(
                            "Download Complete", f"Saved successfully:\n{save_path}",
                            parent=self.file_window,
                        ),
                    )
                else:
                    err_txt = status.decode('utf-8', errors='replace')
                    self.main_window.after(
                        0,
                        lambda m=err_txt: messagebox.showerror("Server Error", m, parent=self.file_window),
                    )
            except Exception as e:
                err_msg = str(e)
                self.main_window.after(
                    0,
                    lambda m=err_msg: messagebox.showerror("Network Error", m, parent=self.file_window),
                )

    def upload_file(self):
        local_path = filedialog.askopenfilename(title="Select File to Upload")
        if not local_path:
            return
        filename = os.path.basename(local_path)
        server_path = self.get_full_path(self.last_valid_path, filename)
        threading.Thread(target=self.do_upload, args=(local_path, server_path), daemon=True).start()

    def do_upload(self, local_path, server_path):
        try:
            with open(local_path, 'rb') as f:
                file_data = f.read()
            with self.net_lock:
                self.client_socket.sendall(f"FILE_UPLOAD:{server_path}".encode('utf-8'))
                time.sleep(0.2)
                self.client_socket.sendall(struct.pack('>I', len(file_data)))
                self.client_socket.sendall(file_data)

                raw_msglen = self.recvall(4)
                if raw_msglen:
                    msglen = struct.unpack('>I', raw_msglen)[0]
                    resp = self.recvall(msglen).decode('utf-8', errors='replace')
                    self.main_window.after(
                        0,
                        lambda m=resp: messagebox.showinfo("Upload Result", m, parent=self.file_window),
                    )
            self.main_window.after(0, self.refresh_file_list)
        except Exception as e:
            err_msg = str(e)
            self.main_window.after(
                0,
                lambda m=err_msg: messagebox.showerror("Upload Error", m, parent=self.file_window),
            )
