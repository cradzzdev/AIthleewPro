"""
FTP Server — nhận ảnh từ máy ảnh, chuyển sang inbox cho Auto Import.

Hỗ trợ đa máy ảnh kết nối đồng thời (Multi-camera Simultaneous Shooting):
- Tự động cập nhật IP LAN thời gian thực khi chuyển đổi Wi-Fi / Hotspot
- Cho phép nhiều máy ảnh (Sony, Canon, Nikon, Fuji) cùng kết nối và bắn ảnh cùng lúc
- Tự động đánh số tránh trùng file (unique name resolution)
- on_file_received CHỈ nổ khi truyền ĐỦ → atomic move sang 1-inbox/
"""

import datetime
import json
import logging
import os
import socket
import sys
import threading
import time

# Dynamic vendor path resolution
possible_vendor_dirs = [
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "vendor"),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "vendor"),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"),
]

for v_dir in possible_vendor_dirs:
    abs_v = os.path.abspath(v_dir)
    if os.path.exists(abs_v) and abs_v not in sys.path:
        sys.path.insert(0, abs_v)

from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer

PASSIVE_PORTS = range(50000, 50051)
BASE_DIR = os.path.expanduser("~/AIthleewTether")
STAGING_DIR = os.path.join(BASE_DIR, "0-dangnhan")
INBOX_DIR = os.path.join(BASE_DIR, "1-inbox")
STATUS_FILE = os.path.join(BASE_DIR, "tether_status.json")
CONN_FILE = os.path.join(BASE_DIR, "connection.json")
CONSOLE_LOG_FILE = os.path.join(BASE_DIR, "tether_console.log")

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger("tether.ftp")


def append_console_log(message: str):
    """Ghi từng hoạt động rõ ràng vào file console cho UI hiển thị."""
    now_str = datetime.datetime.now().strftime("%H:%M:%S")
    formatted = f"[{now_str}] {message}"
    logger.info(message)
    try:
        os.makedirs(BASE_DIR, exist_ok=True)
        with open(CONSOLE_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")
    except Exception:
        pass


class TetherHandler(FTPHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stats = {"files_received": 0, "last_file": None, "bytes_total": 0}

    def on_connect(self):
        if self.remote_ip and not self.remote_ip.startswith("127."):
            append_console_log(f"🔗 Máy ảnh kết nối từ IP: {self.remote_ip}")

    def on_login(self, username):
        if self.remote_ip and not self.remote_ip.startswith("127."):
            append_console_log(f"👤 Xác thực thành công từ {self.remote_ip} (User: '{username}')")

    def on_file_received(self, file_path):
        filename = os.path.basename(file_path)
        try:
            size = os.path.getsize(file_path)
        except Exception:
            size = -1

        dest_name = self._unique_name(filename, size)
        dest_path = os.path.join(INBOX_DIR, dest_name)

        try:
            os.makedirs(INBOX_DIR, exist_ok=True)
            os.replace(file_path, dest_path)
            self._increment_stats(dest_name, size)
            size_mb = size / 1048576 if size > 0 else 0
            append_console_log(f"✅ Đã nhận từ {self.remote_ip}: {dest_name} ({size_mb:.1f} MB) → 1-inbox/")
            
            # Dọn dẹp thư mục con trống trong 0-dangnhan nếu máy ảnh tạo thư mục DCIM/...
            try:
                parent_dir = os.path.dirname(file_path)
                if parent_dir != STAGING_DIR and os.path.commonpath([parent_dir, STAGING_DIR]) == STAGING_DIR:
                    os.removedirs(parent_dir)
            except Exception:
                pass
        except Exception as e:
            append_console_log(f"❌ Lỗi chuyển file từ {self.remote_ip} ({filename}): {e}")

    def on_incomplete_file_received(self, file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass
        if self.remote_ip and not self.remote_ip.startswith("127."):
            append_console_log(f"⚠️ File dở dang từ {self.remote_ip}: {os.path.basename(file_path)} → Đã tự động dọn dẹp")

    def on_disconnect(self):
        if self.remote_ip and not self.remote_ip.startswith("127."):
            append_console_log(f"🔌 Máy ảnh ngắt kết nối: {self.remote_ip}")

    def _unique_name(self, filename, size):
        dest = os.path.join(INBOX_DIR, filename)
        if not os.path.exists(dest):
            return filename
        if os.path.exists(dest) and os.path.getsize(dest) == size:
            return filename
        base, ext = os.path.splitext(filename)
        counter = 2
        while True:
            new_name = f"{base}-{counter}{ext}"
            if not os.path.exists(os.path.join(INBOX_DIR, new_name)):
                return new_name
            counter += 1

    def _increment_stats(self, filename, size):
        current_stats = {"files_received": 0, "last_file": None, "bytes_total": 0}
        if os.path.exists(STATUS_FILE):
            try:
                with open(STATUS_FILE, "r") as f:
                    current_stats = json.load(f)
            except Exception:
                pass
        
        current_stats["files_received"] = current_stats.get("files_received", 0) + 1
        current_stats["last_file"] = filename
        current_stats["bytes_total"] = current_stats.get("bytes_total", 0) + max(0, size)
        
        try:
            with open(STATUS_FILE, "w") as f:
                json.dump(current_stats, f, indent=2)
        except Exception:
            pass


def get_lan_ip():
    """Lấy IP LAN thực tế theo mạng Wi-Fi/Hotspot đang kết nối."""
    # 1. Thử qua macOS ipconfig
    try:
        import subprocess
        for iface in ["en0", "en1", "en2", "pdp_ip0", "bridge0"]:
            try:
                res = subprocess.check_output(["ipconfig", "getifaddr", iface], stderr=subprocess.DEVNULL).decode().strip()
                if res and not res.startswith("127."):
                    return res
            except Exception:
                pass
    except Exception:
        pass

    # 2. Thử qua socket routing
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith("127."):
            return ip
    except Exception:
        pass

    # 3. Thử qua ifconfig
    try:
        import subprocess
        out = subprocess.check_output(["ifconfig"]).decode("utf-8")
        for line in out.splitlines():
            if "inet " in line:
                parts = line.strip().split()
                if len(parts) >= 2:
                    cand = parts[1]
                    if not cand.startswith("127.") and not cand.startswith("169.254."):
                        return cand
    except Exception:
        pass

    return "127.0.0.1"


def start_ftp_server(config: dict, stop_event: threading.Event):
    ftp_config = config.get("tether", {})
    port = ftp_config.get("port", 2121)
    user = ftp_config.get("username", "a7")
    password = ftp_config.get("password", "12345678")
    base_dir = ftp_config.get("base_dir", BASE_DIR)

    staging = os.path.join(base_dir, "0-dangnhan")
    inbox = os.path.join(base_dir, "1-inbox")
    os.makedirs(staging, exist_ok=True)
    os.makedirs(inbox, exist_ok=True)

    auth = DummyAuthorizer()
    auth.add_user(user, password, staging, perm="elradfmw")

    ip = get_lan_ip()
    handler = TetherHandler
    handler.authorizer = auth
    handler.passive_ports = PASSIVE_PORTS
    handler.timeout = 300
    handler.use_sendfile = False
    handler.banner = "AIthleewPro Multi-Camera Tether Ready"
    if ip and not ip.startswith("127."):
        handler.masquerade_address = ip

    try:
        server = FTPServer(("0.0.0.0", port), handler)
    except Exception as e:
        err_msg = f"Không mở được cổng {port}: {e}"
        append_console_log(f"❌ {err_msg}")
        raise

    server.max_cons = 32
    server.max_cons_per_ip = 16
    append_console_log(f"🚀 FTP Server khởi động tại {ip}:{port} (Lắng nghe mọi card mạng 0.0.0.0)")
    append_console_log(f"📁 Thư mục nhận: {inbox}")

    def _write_conn_info(current_ip, status="running"):
        try:
            with open(CONN_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "ip": current_ip,
                    "port": port,
                    "username": user,
                    "password": password,
                    "status": status,
                    "pid": os.getpid(),
                    "updated_at": int(time.time()),
                }, f, indent=2)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Error writing connection info: {e}")

    _write_conn_info(ip, status="running")

    if not os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE, "w", encoding="utf-8") as f:
                json.dump({"files_received": 0, "last_file": "Chưa có ảnh", "bytes_total": 0}, f, indent=2)
        except Exception:
            pass

    def _heartbeat_and_network_monitor():
        last_ip = ip
        while not stop_event.is_set():
            time.sleep(2.0)
            current_ip = get_lan_ip()
            if current_ip != last_ip and current_ip != "127.0.0.1" and not current_ip.startswith("169.254"):
                append_console_log(f"🌐 Mạng thay đổi → IP LAN mới: {current_ip}:{port}")
                handler.masquerade_address = current_ip
                last_ip = current_ip
            _write_conn_info(last_ip, status="running")

    threading.Thread(target=_heartbeat_and_network_monitor, daemon=True).start()

    def _wait_stop():
        stop_event.wait()
        try:
            _write_conn_info(ip, status="stopped")
            server.close_all()
            append_console_log("⏹ Đã dừng FTP Server.")
        except Exception:
            pass

    threading.Thread(target=_wait_stop, daemon=True).start()
    try:
        server.serve_forever(timeout=1, handle_exit=False)
    except Exception as e:
        if not stop_event.is_set():
            append_console_log(f"⚠️ FTP server dừng: {e}")
    finally:
        _write_conn_info(ip, status="stopped")
