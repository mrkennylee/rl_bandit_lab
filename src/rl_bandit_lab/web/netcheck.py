"""Port-availability check used at startup so a second launch on a busy port
fails fast — before it would otherwise bootstrap (and on shutdown tear down) the
database that the already-running instance is using."""

from __future__ import annotations

import socket


def port_in_use(host: str, port: int, timeout: float = 0.5) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        return sock.connect_ex((host, port)) == 0


def ensure_port_available(host: str, port: int) -> None:
    if port_in_use(host, port):
        raise RuntimeError(
            f"port {host}:{port} is already in use — the app is probably already "
            f"running. Stop it first (make stop) or pick another port "
            f"(make run PORT=...)."
        )
