"""Validated prompt primitives: ``ask_float``/``ask_int``/``ask_text``/
``ask_choice``/``ask_yes_no``.

Generic, domain-agnostic input helpers sharing one visual language. Retry on
bad input; optional cancel tokens. Extracted verbatim from ``ui.inputs``
during the P3 ``console/`` decomposition.
"""
import time
from termcolor import colored

from ui.console.widgets import print_error

# =============================================================================
#  PROFESSIONAL INPUT TOOLKIT
# -----------------------------------------------------------------------------
#  Validated, retry-on-error prompt primitives sharing one visual language:
#  a bold cyan label, an inline constraint/units hint, the standard caret, and
#  friendly red error messages. Numeric prompts re-ask on invalid input instead
#  of crashing; optional prompts accept a cancel keyword so the user can back
#  out of any data-entry step cleanly.
# =============================================================================
PROMPT_CARET = "\u2794"
_CANCEL_TOKENS = {"c", "cancel", "q", "quit", "b", "back", "esc"}


def _dim(text):
    return colored(text, 'white', attrs=['dark'])


def _format_prompt(label, unit=None, hint=None, default=None, allow_cancel=False):
    head = "  " + label.strip()
    if unit:
        head += f"  [{unit}]"
    sub = []
    if hint:
        sub.append(hint)
    if default is not None:
        sub.append(f"default: {default}")
    if allow_cancel:
        sub.append("'c' to cancel")
    line = colored(head, 'cyan', attrs=['bold'])
    if sub:
        line += _dim("   (" + "  \u00b7  ".join(sub) + ")")
    line += colored(f"\n  {PROMPT_CARET} ", 'cyan', attrs=['bold'])
    return line


def _range_hint(minimum, maximum, exclusive_min, exclusive_max, symbol="x"):
    if minimum is None and maximum is None:
        return None
    lo = ""
    if minimum is not None:
        lo = f"{minimum} {'<' if exclusive_min else '\u2264'} "
    hi = ""
    if maximum is not None:
        hi = f" {'<' if exclusive_max else '\u2264'} {maximum}"
    return f"{lo}{symbol}{hi}"


def ask_float(label, unit=None, minimum=None, maximum=None,
              exclusive_min=False, exclusive_max=False,
              default=None, allow_cancel=False):
    """Prompt for a float, validating range and retrying on bad input.
    Returns the float, or None if the user cancels (when allowed)."""
    hint = _range_hint(minimum, maximum, exclusive_min, exclusive_max)
    while True:
        raw = input(_format_prompt(label, unit, hint, default, allow_cancel)).strip()
        if not raw and default is not None:
            return float(default)
        if allow_cancel and raw.lower() in _CANCEL_TOKENS:
            return None
        try:
            val = float(raw)
        except ValueError:
            print_error("  Please enter a valid number (e.g. 12.5).")
            time.sleep(1.0); continue
        if minimum is not None and (val < minimum or (exclusive_min and val == minimum)):
            rel = "greater than" if exclusive_min else "at least"
            print_error(f"  Value must be {rel} {minimum}{(' ' + unit) if unit else ''}.")
            time.sleep(1.0); continue
        if maximum is not None and (val > maximum or (exclusive_max and val == maximum)):
            rel = "less than" if exclusive_max else "at most"
            print_error(f"  Value must be {rel} {maximum}{(' ' + unit) if unit else ''}.")
            time.sleep(1.0); continue
        return val


def ask_int(label, minimum=None, maximum=None, default=None, allow_cancel=False):
    """Prompt for an integer, validating range and retrying on bad input."""
    hint = _range_hint(minimum, maximum, False, False, symbol="n")
    while True:
        raw = input(_format_prompt(label, None, hint, default, allow_cancel)).strip()
        if not raw and default is not None:
            return int(default)
        if allow_cancel and raw.lower() in _CANCEL_TOKENS:
            return None
        try:
            val = int(raw)
        except ValueError:
            print_error("  Please enter a whole number (e.g. 2001).")
            time.sleep(1.0); continue
        if minimum is not None and val < minimum:
            print_error(f"  Value must be at least {minimum}."); time.sleep(1.0); continue
        if maximum is not None and val > maximum:
            print_error(f"  Value must be at most {maximum}."); time.sleep(1.0); continue
        return val


def ask_text(label, required=True, default=None, allow_cancel=False, max_len=None):
    """Prompt for a line of text with optional required / length validation."""
    while True:
        raw = input(_format_prompt(label, None, None, default, allow_cancel)).strip()
        if allow_cancel and raw.lower() in _CANCEL_TOKENS:
            return None
        if not raw:
            if default is not None:
                return default
            if not required:
                return ""
            print_error("  This field cannot be empty."); time.sleep(1.0); continue
        if max_len and len(raw) > max_len:
            print_error(f"  Please keep it under {max_len} characters."); time.sleep(1.0); continue
        return raw


def ask_choice(label, valid, allow_cancel=False):
    """Prompt until the user enters one of ``valid`` tokens. Returns the token."""
    valid = [str(v) for v in valid]
    hint = "options: " + " / ".join(valid)
    while True:
        raw = input(_format_prompt(label, None, hint, None, allow_cancel)).strip()
        if allow_cancel and raw.lower() in _CANCEL_TOKENS:
            return None
        if raw in valid:
            return raw
        print_error(f"  Invalid choice. Pick one of: {', '.join(valid)}."); time.sleep(1.0)


def ask_yes_no(question, default=None):
    """Prompt for a yes/no answer. Returns True/False (default on empty input)."""
    suffix = "(Y/N)" if default is None else ("(Y/n)" if default else "(y/N)")
    while True:
        raw = input(colored(f"  {question} {suffix} {PROMPT_CARET} ",
                            'cyan', attrs=['bold'])).strip().lower()
        if not raw and default is not None:
            return default
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        print_error("  Please answer Y or N."); time.sleep(0.8)
