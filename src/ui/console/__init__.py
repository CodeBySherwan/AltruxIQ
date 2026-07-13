"""Generic, domain-agnostic terminal UI kit for AltruxIQ.

One convenient import surface for the prompt primitives, the rendering widgets
and the date/time formatters. No beam/load/material knowledge lives here —
this package is what a future non-beam calculator reuses unchanged.

Extracted from ``ui.Menus`` and ``ui.inputs`` during the P3 ``console/``
decomposition (moves, not rewrites).
"""
from ui.console.formatting import (
    fmt_datetime,
    fmt_date_compact,
    fmt_duration,
)
from ui.console.widgets import (
    SESSION_START,
    UI_W,
    session_uptime,
    _live_clock_supported,
    input_with_live_clock,
    _strip_len,
    ui_banner,
    ui_open,
    ui_close,
    ui_blank,
    ui_text,
    ui_head,
    ui_field,
    ui_bullet,
    ui_bar,
    ui_check_row,
    ui_verdict_badge,
    ui_footer,
    ui_menu_stage,
    clear_screen,
    print_title,
    print_option,
    print_error,
    print_success,
)
from ui.console.prompts import (
    PROMPT_CARET,
    _CANCEL_TOKENS,
    _dim,
    _format_prompt,
    _range_hint,
    ask_float,
    ask_int,
    ask_text,
    ask_choice,
    ask_yes_no,
)

__all__ = [
    # formatting
    "fmt_datetime",
    "fmt_date_compact",
    "fmt_duration",
    # widgets
    "SESSION_START",
    "UI_W",
    "session_uptime",
    "input_with_live_clock",
    "ui_banner",
    "ui_open",
    "ui_close",
    "ui_blank",
    "ui_text",
    "ui_head",
    "ui_field",
    "ui_bullet",
    "ui_bar",
    "ui_check_row",
    "ui_verdict_badge",
    "ui_footer",
    "ui_menu_stage",
    "clear_screen",
    "print_title",
    "print_option",
    "print_error",
    "print_success",
    # prompts
    "PROMPT_CARET",
    "ask_float",
    "ask_int",
    "ask_text",
    "ask_choice",
    "ask_yes_no",
]
