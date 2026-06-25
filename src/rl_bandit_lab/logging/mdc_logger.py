"""Per-unit .mdc logs (Rule 6): structured markdown-with-frontmatter, one file
per logical unit run (a bandit run, a gridworld run, a test unit...).

    ---
    unit: bandit_run
    run_id: 42
    started: 2026-06-24T22:30:00
    ---

    step 1 | arm 2 | reward 1 | reason explore | Q=[0,0,1]
"""

from __future__ import annotations

from datetime import datetime

from rl_bandit_lab.config import get_settings


class MdcLogger:
    def __init__(self, unit: str, **frontmatter: object) -> None:
        settings = get_settings()
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        self.path = settings.mdc_log_dir / f"{unit}_{stamp}.mdc"
        self._fh = open(self.path, "w", encoding="utf-8")
        self._fh.write("---\n")
        self._fh.write(f"unit: {unit}\n")
        for key, value in frontmatter.items():
            self._fh.write(f"{key}: {value}\n")
        self._fh.write(f"started: {datetime.now().isoformat(timespec='seconds')}\n")
        self._fh.write("---\n\n")
        self._fh.flush()

    def line(self, message: str) -> None:
        self._fh.write(message.rstrip("\n") + "\n")
        self._fh.flush()

    def close(self) -> None:
        if not self._fh.closed:
            self._fh.write(
                f"\n_ended: {datetime.now().isoformat(timespec='seconds')}_\n"
            )
            self._fh.close()

    def __enter__(self) -> "MdcLogger":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
