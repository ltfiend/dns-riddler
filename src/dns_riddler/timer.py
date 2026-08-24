"""Timed line input from stdin.

Uses select() on stdin in canonical (line) mode: stdin only becomes readable
when the user presses Enter, so we get a full timed line read with normal
echo and line editing — no termios raw-mode handling needed.
"""

from __future__ import annotations

import sys
import time

try:
    import select

    _HAS_SELECT = hasattr(select, "select")
except ImportError:  # pragma: no cover
    _HAS_SELECT = False


def _can_time() -> bool:
    # select() on Windows only works on sockets, not console handles.
    return _HAS_SELECT and sys.platform != "win32" and sys.stdin.isatty()


def timed_input(prompt: str, timeout: float | None) -> str | None:
    """Read one line from stdin. Returns None on timeout.

    With timeout=None (or when timing is unsupported on this platform),
    behaves like plain input().
    """
    if timeout is None or not _can_time():
        try:
            return input(prompt)
        except EOFError:
            return ""

    sys.stdout.write(prompt)
    sys.stdout.flush()
    deadline = time.monotonic() + timeout
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            sys.stdout.write("\n")
            sys.stdout.flush()
            return None
        # Short ticks so a future version could redraw a countdown.
        ready, _, _ = select.select([sys.stdin], [], [], min(1.0, remaining))
        if ready:
            line = sys.stdin.readline()
            if line == "":  # EOF
                return ""
            return line.rstrip("\n")


def flush_stdin() -> None:
    """Discard any pending typed-but-unread input (e.g. after a timeout)."""
    if not _can_time():
        return
    while True:
        ready, _, _ = select.select([sys.stdin], [], [], 0)
        if not ready:
            return
        if sys.stdin.readline() == "":
            return
