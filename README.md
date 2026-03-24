# 🖥️ Remote Control Center

**Remote Control Center** là một công cụ quản trị hệ thống và điều khiển máy tính từ xa chuyên biệt cho mạng nội bộ (LAN) sử dụng giao thức TCP/IP. Dự án được xây dựng bằng Python, áp dụng kiến trúc Client-Server đa luồng (Multi-threading) kết hợp với giao diện người dùng hiện đại (Fluent Design) thông qua thư viện CustomTkinter.

Điểm nổi bật của dự án là khả năng **Multi-session** (điều khiển nhiều PC cùng lúc trên các Tab độc lập) và cơ chế **Tường lửa động (Dynamic Firewall)** giúp đảm bảo an toàn thông tin tối đa.

---

## ✨ Tính năng nổi bật

### 🛡️ Bảo mật & Kiến trúc cốt lõi
* **Kiến trúc Multi-session:** Quản lý đồng thời nhiều máy trạm thông qua giao diện Tab động. Các luồng mạng hoạt động hoàn toàn độc lập, không gây nghẽn (TCP Coalescing handled).
* **Stealth & Privilege Escalation (Server):** Tự động ẩn cửa sổ Console và xin quyền Administrator khi khởi chạy để vượt rào cản UIPI của Windows.
* **Tường lửa động (Dynamic Firewall):** Server tự động thực thi PowerShell ẩn để đục lỗ Inbound Rule (Port 9999) khi bật, và tự động xóa sạch Rule này khi tắt phần mềm.
* **Nhịp tim hệ thống (Heartbeat):** Liên tục giám sát kết nối bằng `MSG_PEEK`. Ngắt kết nối chuẩn mực (Graceful Disconnect) khi phát hiện sự cố, chống Crash ứng dụng.

### 🛠️ Các Module Quản trị (Client)
* **📺 Screen Mirroring & Webcam Capture:** Truyền phát hình ảnh thời gian thực, tự động Auto-scale khung hình. Hỗ trợ chụp ảnh (Snapshot) và quay video màn hình/webcam xuất ra file `.avi` (tích hợp OpenCV).
* **📂 File Manager:** Giao diện duyệt file dạng FTP. Hỗ trợ Upload/Download các file dung lượng lớn đảm bảo toàn vẹn dữ liệu, cho phép thực thi (Open) file từ xa.
* **⚙️ Task & Software Manager:** Liệt kê các tiến trình chạy ngầm và phần mềm đã cài đặt. Cho phép tìm kiếm, ép đóng (Force Kill) qua PID hoặc khởi chạy (Start) ứng dụng từ xa.
* **💻 Remote Terminal:** Cửa sổ dòng lệnh giả lập (như CMD), thực thi lệnh hệ thống từ xa một cách mượt mà nhờ kiến trúc đa luồng.
* **⌨️ Keylogger Toàn cục:** Ghi nhận thao tác phím trên toàn hệ điều hành, hỗ trợ xuất nhật ký ra file `.txt` phục vụ kiểm toán.
* **⚡ Power Management:** Điều khiển nguồn (Sleep, Restart, Shutdown) với cơ chế xác nhận 2 lớp an toàn.
* **ℹ️ System Info:** Truy xuất nhanh cấu hình phần cứng (CPU, RAM, Disk).

---

## 🚀 Công nghệ sử dụng
* **Ngôn ngữ:** Python 3.x
* **Giao diện:** `customtkinter`, `tkinter`
* **Mạng & Xử lý:** `socket`, `threading`, `select`, `struct`
* **Xử lý Hình ảnh/Video:** `opencv-python` (cv2), `Pillow` (PIL), `ImageGrab`
* **Hệ thống:** `subprocess`, `ctypes`, `os`, `pynput` (Keylogger)

---

## 📂 Cấu trúc thư mục (Project Structure)

Dự án được phân tách rõ ràng thành hai phân hệ độc lập: `client` (Máy quản trị) và `server` (Máy bị điều khiển).

```text
CAPSTONEPROJECT_REMOTECONTROL/
├── client/                 # Chứa mã nguồn của Máy Quản trị (Điều khiển)
│   ├── features/           # Các module tính năng (Task Manager, File, Screen...)
│   ├── __init__.py
│   ├── app.py              # Giao diện chính (Bảng điều khiển đa Tab)
│   ├── network.py          # Xử lý nhận/gửi gói tin TCP và Heartbeat
│   ├── session.py          # Quản lý phiên làm việc (RemoteSession)
│   └── theme.py            # Cấu hình màu sắc, font chữ (Fluent Design)
├── server/                 # Chứa mã nguồn của Máy Trạm (Bị điều khiển)
│   ├── __init__.py
│   ├── app.py              # Giao diện Host của Server (Start/Stop, Log)
│   ├── handlers.py         # Bộ phân giải và thực thi lệnh từ Client
│   ├── keylogger.py        # Logic giám sát thao tác phím toàn cục
│   └── streaming.py        # Luồng nén và truyền phát Màn hình/Webcam
├── client.py               # File Entry Point để chạy ứng dụng Client
├── server.py               # File Entry Point để chạy ứng dụng Server
└── README.md               # Tài liệu dự án
```

---

## 📦 Hướng dẫn Cài đặt & Sử dụng

### 1. Yêu cầu hệ thống
* Windows 10 hoặc Windows 11.
* Python 3.8 trở lên.

### 2. Cài đặt thư viện
Mở Terminal/CMD và chạy lệnh sau để cài đặt các thư viện cần thiết. Lệnh sử dụng `-m` giúp đảm bảo thư viện cài đúng vào phiên bản Python hiện tại:
```cmd
python -m pip install customtkinter opencv-python pillow pynput
```

### 3. Cách chạy ứng dụng
**Tại máy bị điều khiển (Máy trạm):**
1. Chạy file `server.py` (Mã nguồn sẽ yêu cầu cấp quyền Administrator để tự động mở Tường lửa và chạy Keylogger).
2. Nhấn nút **"Start Hosting Session"**.
3. Gửi địa chỉ IP hiển thị trên màn hình cho Quản trị viên.

**Tại máy Quản trị (Client):**
1. Chạy file `client.py`.
2. Nhập IP của máy trạm vào ô Server IP Address và nhấn **Connect**.
3. Chọn các chức năng trên lưới Menu để bắt đầu điều khiển. Có thể nhấn **"➕ Add PC"** ở góc trên cùng để điều khiển thêm máy khác cùng lúc.

---

## ⚠️ Cảnh báo Pháp lý (Disclaimer)
Dự án này được phát triển **HOÀN TOÀN VÌ MỤC ĐÍCH GIÁO DỤC** và làm đồ án môn học. 
Tác giả không chịu bất kỳ trách nhiệm nào nếu mã nguồn này được sử dụng cho các mục đích vi phạm pháp luật, xâm phạm quyền riêng tư, hoặc cài đặt lên các máy tính không thuộc quyền sở hữu/không được sự cho phép của người dùng. Vui lòng tuân thủ pháp luật về An toàn thông tin mạng khi tham khảo và sử dụng dự án này.
