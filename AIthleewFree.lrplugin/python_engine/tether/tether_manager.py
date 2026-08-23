#!/usr/bin/env python3
"""Quản lý FTP server — được gọi bởi Lua hoặc CLI."""

import argparse
import json
import os
import signal
import sys
import threading

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from tether.ftp_server import start_ftp_server, BASE_DIR
from tether.camera_profiles import list_cameras

PID_FILE = os.path.join(BASE_DIR, "tether.pid")
CONFIG_FILE = os.path.join(BASE_DIR, "tether_config.json")

DEFAULT_CONFIG = {
    "tether": {
        "port": 2121,
        "username": "a7",
        "password": "12345678",
        "base_dir": BASE_DIR,
        "camera_profile": "sony_a7iv",
    }
}


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_CONFIG


def save_config(config):
    os.makedirs(BASE_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def is_pid_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def cmd_start(port=None, username=None, password=None, camera=None, output=None):
    config = load_config()
    if port:
        config.setdefault("tether", {})["port"] = int(port)
    if username:
        config.setdefault("tether", {})["username"] = str(username)
    if password:
        config.setdefault("tether", {})["password"] = str(password)
    if camera:
        config.setdefault("tether", {})["camera_profile"] = str(camera)
    if output:
        config.setdefault("tether", {})["base_dir"] = os.path.dirname(os.path.abspath(output)) if output.endswith("1-inbox") else os.path.abspath(output)

    save_config(config)
    os.makedirs(BASE_DIR, exist_ok=True)

    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                old_pid = int(f.read().strip())
            if is_pid_running(old_pid):
                return {"status": "already_running", "pid": old_pid}
        except Exception:
            pass

    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))
        f.flush()
        try:
            os.fsync(f.fileno())
        except Exception:
            pass

    stop_event = threading.Event()
    
    def _sig_handler(*_):
        stop_event.set()

    signal.signal(signal.SIGTERM, _sig_handler)
    signal.signal(signal.SIGINT, _sig_handler)

    try:
        start_ftp_server(config, stop_event)
    finally:
        if os.path.exists(PID_FILE):
            try:
                os.remove(PID_FILE)
            except Exception:
                pass

    return {"status": "stopped"}


def cmd_stop():
    if not os.path.exists(PID_FILE):
        return {"status": "not_running"}
    try:
        with open(PID_FILE, "r") as f:
            pid = int(f.read().strip())
        
        if is_pid_running(pid):
            os.kill(pid, signal.SIGTERM)
            return {"status": "stopping", "pid": pid}
        else:
            os.remove(PID_FILE)
            return {"status": "cleaned_stale_pid", "pid": pid}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def cmd_status():
    running = False
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                pid = int(f.read().strip())
            running = is_pid_running(pid)
            if not running:
                os.remove(PID_FILE)
        except Exception:
            running = False

    status_file = os.path.join(BASE_DIR, "tether_status.json")
    conn_file = os.path.join(BASE_DIR, "connection.json")
    result = {"running": running, "base_dir": BASE_DIR}
    
    if os.path.exists(status_file):
        try:
            with open(status_file, "r", encoding="utf-8") as f:
                result["stats"] = json.load(f)
        except Exception:
            pass
            
    if os.path.exists(conn_file):
        try:
            with open(conn_file, "r", encoding="utf-8") as f:
                result["connection"] = json.load(f)
        except Exception:
            pass
            
    return result


def cmd_cameras():
    cameras = list_cameras()
    return {"cameras": [{"id": cid, "name": name} for cid, name in cameras]}


def main():
    parser = argparse.ArgumentParser(description="AIthleewPro Tether Manager")
    parser.add_argument("command", choices=["start", "stop", "status", "cameras"])
    parser.add_argument("--port", type=int, default=None, help="FTP Port")
    parser.add_argument("--username", type=str, default=None, help="FTP Username")
    parser.add_argument("--password", type=str, default=None, help="FTP Password")
    parser.add_argument("--camera", type=str, default=None, help="Camera profile")
    parser.add_argument("--output", type=str, default="")
    args = parser.parse_args()

    if args.command == "start":
        result = cmd_start(port=args.port, username=args.username, password=args.password, camera=args.camera)
    elif args.command == "stop":
        result = cmd_stop()
    elif args.command == "status":
        result = cmd_status()
    elif args.command == "cameras":
        result = cmd_cameras()
    else:
        result = {"status": "error", "error": "Unknown command"}
    
    output = json.dumps(result, indent=2, ensure_ascii=False)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
    else:
        print(output)

    return 0 if result.get("status") != "error" else 1


if __name__ == "__main__":
    sys.exit(main())

