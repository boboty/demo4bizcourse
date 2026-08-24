"""Runtime network helpers shared by classroom-facing executors."""

from __future__ import annotations

import os
import socket
from typing import Optional


def lan_ip() -> str:
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("8.8.8.8", 80))
        return probe.getsockname()[0]
    finally:
        probe.close()


def resolve_demo_base_url(cli_base_url: Optional[str] = None) -> str:
    """Resolve the FastAPI URL without letting each executor guess separately."""
    if cli_base_url:
        return cli_base_url.rstrip("/")

    demo_base_url = os.environ.get("DEMO_BASE_URL")
    if demo_base_url:
        return demo_base_url.rstrip("/")

    mac_lan_ip = os.environ.get("MAC_LAN_IP")
    if mac_lan_ip:
        return "http://{0}:8000".format(mac_lan_ip)

    return "http://{0}:8000".format(lan_ip())
