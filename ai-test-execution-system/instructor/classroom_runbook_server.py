#!/usr/bin/env python3
"""Local-only classroom Runbook server using only the Python standard library."""

from __future__ import annotations

import ipaddress
import json
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Iterable, Optional


HOST = "127.0.0.1"
PORT = 8765
DEMO_PORT = 8000
INSTRUCTOR_DIR = Path(__file__).resolve().parent
RUNBOOK_PATH = INSTRUCTOR_DIR / "classroom-runbook.html"


def run_command(args: list[str]) -> str:
    try:
        result = subprocess.run(
            args, check=True, capture_output=True, text=True, timeout=2
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout


def is_virtual_interface(interface: str) -> bool:
    name = interface.strip().lower()
    prefixes = (
        "utun", "tun", "tap", "tailscale", "docker", "bridge", "vmenet",
        "vmnet", "awdl", "llw", "lo",
    )
    return not name or name.startswith(prefixes)


def is_safe_lan_ipv4(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value.strip())
    except ValueError:
        return False
    if address.version != 4:
        return False
    if address.is_loopback or address.is_unspecified or address.is_link_local:
        return False
    if address.is_multicast or address.is_reserved:
        return False
    if address in ipaddress.ip_network("198.18.0.0/15"):
        return False
    return True


def interface_ipv4(interface: str) -> Optional[str]:
    if is_virtual_interface(interface):
        return None
    value = run_command(["/usr/sbin/ipconfig", "getifaddr", interface]).strip()
    return value if is_safe_lan_ipv4(value) else None


def default_route_interface() -> Optional[str]:
    output = run_command(["/sbin/route", "-n", "get", "default"])
    for line in output.splitlines():
        key, separator, value = line.partition(":")
        if separator and key.strip() == "interface":
            interface = value.strip()
            if not is_virtual_interface(interface):
                return interface
    return None


def hardware_interfaces() -> Iterable[str]:
    """Return locally reported physical interfaces, in OS order."""
    output = run_command(["/usr/sbin/networksetup", "-listallhardwareports"])
    for line in output.splitlines():
        key, separator, value = line.partition(":")
        if separator and key.strip() == "Device":
            interface = value.strip()
            if not is_virtual_interface(interface):
                yield interface


def discover_lan_ip() -> Optional[str]:
    """Prefer the default-route interface; safely inspect physical fallbacks."""
    preferred = default_route_interface()
    if preferred:
        address = interface_ipv4(preferred)
        if address:
            return address

    seen: set[str] = set()
    for interface in hardware_interfaces():
        if interface in seen:
            continue
        seen.add(interface)
        address = interface_ipv4(interface)
        if address:
            return address
    return None


def runtime_payload() -> dict[str, object]:
    lan_ip = discover_lan_ip()
    if lan_ip is None:
        return {
            "status": "unavailable",
            "lan_ip": None,
            "demo_base_url": None,
            "runbook_url": f"http://{HOST}:{PORT}/",
            "message": "无法自动确定课堂 LAN IP，请检查当前网络。",
        }
    return {
        "status": "available",
        "lan_ip": lan_ip,
        "demo_base_url": f"http://{lan_ip}:{DEMO_PORT}",
        "runbook_url": f"http://{HOST}:{PORT}/",
        "message": None,
    }


class ClassroomRunbookHandler(BaseHTTPRequestHandler):
    server_version = "ClassroomRunbook/1.0"

    def send_bytes(self, body: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        if self.path in ("/", "/classroom-runbook.html"):
            try:
                body = RUNBOOK_PATH.read_bytes()
            except OSError:
                self.send_bytes(b"Runbook HTML is unavailable.\n", "text/plain; charset=utf-8", 500)
                return
            self.send_bytes(body, "text/html; charset=utf-8")
            return

        if self.path == "/api/runtime":
            body = json.dumps(runtime_payload(), ensure_ascii=False).encode("utf-8")
            self.send_bytes(body, "application/json; charset=utf-8")
            return

        self.send_bytes(b"Not found\n", "text/plain; charset=utf-8", 404)

    def log_message(self, format: str, *args: object) -> None:
        print(f"[classroom-runbook] {self.address_string()} - {format % args}")


class LocalOnlyHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True


def main() -> None:
    if not RUNBOOK_PATH.is_file():
        raise SystemExit(f"Missing Runbook HTML: {RUNBOOK_PATH}")
    server = LocalOnlyHTTPServer((HOST, PORT), ClassroomRunbookHandler)
    print(f"Classroom Runbook: http://{HOST}:{PORT}/")
    print("Local-only server; FastAPI Demo and Appium are not started by this process.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nClassroom Runbook stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
