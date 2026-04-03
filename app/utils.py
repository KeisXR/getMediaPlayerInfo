"""
Shared utility functions for the GUI layer.
"""
from __future__ import annotations


def fmt_ms(ms: int) -> str:
    """Format milliseconds to a human-readable ``m:ss`` string.

    Examples::

        fmt_ms(90000)   → '1:30'
        fmt_ms(3661000) → '61:01'
    """
    total_s = ms // 1000
    m, s = divmod(total_s, 60)
    return f"{m}:{s:02d}"


def fmt_duration(ms: int) -> str:
    """Format milliseconds to a compact human-readable string.

    Returns ``Xh Ym``, ``Xm Ys``, or ``Xs`` depending on magnitude.

    Examples::

        fmt_duration(5_400_000)  → '1h 30m'
        fmt_duration(90_000)     → '1m 30s'
        fmt_duration(5_000)      → '5s'
    """
    total_s = ms // 1000
    h, rem = divmod(total_s, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h {m}m"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"
