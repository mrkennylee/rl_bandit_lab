"""Timestamped system-wide log: logs/system/system_<YYYYMMDD_HHMMSS>.log."""

from __future__ import annotations

import logging

from rl_bandit_lab.config import get_settings

_FMT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"


def get_system_logger() -> logging.Logger:
    logger = logging.getLogger("rl_bandit_lab")
    if logger.handlers:  # already configured this process
        return logger

    settings = get_settings()
    logger.setLevel(logging.INFO)
    logger.propagate = False

    path = settings.system_log_dir / f"system_{settings.run_timestamp}.log"
    formatter = logging.Formatter(_FMT)

    file_handler = logging.FileHandler(path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    logger.info("system logger initialised -> %s", path)
    return logger
