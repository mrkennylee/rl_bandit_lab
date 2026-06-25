"""Phase 6 fix — refuse to start (and so refuse to touch the database) when the
serve port is already taken, so a second `make run` can't tear down the first
instance's Postgres."""

from __future__ import annotations

import socket

import pytest

from rl_bandit_lab.web.netcheck import ensure_port_available, port_in_use


def _listening_socket() -> socket.socket:
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.bind(("127.0.0.1", 0))
    srv.listen()
    return srv


def _free_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def test_port_in_use_true_when_listener() -> None:
    srv = _listening_socket()
    host, port = srv.getsockname()
    try:
        assert port_in_use(host, port) is True
    finally:
        srv.close()


def test_port_in_use_false_when_free() -> None:
    assert port_in_use("127.0.0.1", _free_port()) is False


def test_ensure_port_available_raises_when_taken() -> None:
    srv = _listening_socket()
    host, port = srv.getsockname()
    try:
        with pytest.raises(RuntimeError, match="already in use"):
            ensure_port_available(host, port)
    finally:
        srv.close()


def test_ensure_port_available_passes_when_free() -> None:
    ensure_port_available("127.0.0.1", _free_port())  # must not raise
