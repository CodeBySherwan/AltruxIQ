"""Date/time formatting helpers for terminal display.

Pure stdlib; no project dependencies. Extracted verbatim from ``ui.Menus`` during
the P3 ``console/`` decomposition.
"""
import datetime


def fmt_datetime(dt=None):
    """Human-friendly local timestamp, e.g. 'Tue 23 Jun 2026  19:45:21'."""
    dt = dt or datetime.datetime.now().astimezone()
    return dt.strftime("%a %d %b %Y  %H:%M:%S")


def fmt_date_compact(dt=None):
    """Compact date-time used for project filenames/labels: '2026-06-23 19:45'."""
    dt = dt or datetime.datetime.now().astimezone()
    return dt.strftime("%Y-%m-%d %H:%M")


def fmt_duration(seconds):
    """Format an elapsed duration as 'HH:MM:SS' (or 'Dd HH:MM:SS')."""
    seconds = int(max(0, seconds))
    d, rem = divmod(seconds, 86400)
    h, rem = divmod(rem, 3600)
    m, s = divmod(rem, 60)
    if d:
        return f"{d}d {h:02d}:{m:02d}:{s:02d}"
    return f"{h:02d}:{m:02d}:{s:02d}"
