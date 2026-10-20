"""Parse expansion strings such as ``"Jane{TAB}Doe{ENTER}"`` into actions.

Plain text is typed as-is. Anything in braces is a key or a command:

    {TAB}  {ENTER}  {BACKSPACE}  {ESC}  {LEFT} ...   press a key
    {TAB 3}                                           press it 3 times
    {CMD+A}  {SHIFT+TAB}  {CTRL+ALT+DELETE}           press a key combination
    {DELAY 0.5}                                       wait half a second
    {{  }}                                            a literal { or }
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Tuple, Union


class MacroError(ValueError):
    """An expansion string could not be parsed."""


@dataclass(frozen=True)
class TypeText:
    text: str

    def __str__(self) -> str:
        return f"type {self.text!r}"


@dataclass(frozen=True)
class PressKeys:
    # Canonical key names, modifiers first: ("cmd", "a"), ("tab",).
    keys: Tuple[str, ...]
    times: int = 1

    def __str__(self) -> str:
        repeat = f" x{self.times}" if self.times > 1 else ""
        return f"press {'+'.join(self.keys)}{repeat}"


@dataclass(frozen=True)
class Delay:
    seconds: float

    def __str__(self) -> str:
        return f"wait {self.seconds:g}s"


Action = Union[TypeText, PressKeys, Delay]

# Names accepted inside braces, mapped to pynput ``Key`` member names.
KEYS = {
    "tab": "tab",
    "enter": "enter",
    "return": "enter",
    "backspace": "backspace",  # the key labelled "delete" on a Mac
    "bs": "backspace",
    "delete": "delete",  # forward delete
    "del": "delete",
    "esc": "esc",
    "escape": "esc",
    "space": "space",
    "up": "up",
    "down": "down",
    "left": "left",
    "right": "right",
    "home": "home",
    "end": "end",
    "pageup": "page_up",
    "pgup": "page_up",
    "pagedown": "page_down",
    "pgdn": "page_down",
    **{f"f{n}": f"f{n}" for n in range(1, 13)},
}

MODIFIERS = {
    "cmd": "cmd",
    "command": "cmd",
    "win": "cmd",
    "super": "cmd",
    "ctrl": "ctrl",
    "control": "ctrl",
    "alt": "alt",
    "option": "alt",
    "opt": "alt",
    "shift": "shift",
}

_DELAY_WORDS = {"delay", "wait", "pause"}

# A doubled brace, a {token}, or a stray brace (which is an error).
_TOKEN = re.compile(r"\{\{|\}\}|\{([^{}]*)\}|[{}]")


def parse(source: str) -> List[Action]:
    """Turn an expansion string into a list of actions."""
    actions: List[Action] = []
    text = ""
    pos = 0
    for match in _TOKEN.finditer(source):
        text += source[pos : match.start()]
        pos = match.end()
        token = match.group()
        if token == "{{":
            text += "{"
        elif token == "}}":
            text += "}"
        elif match.group(1) is not None:
            if text:
                actions.append(TypeText(text))
                text = ""
            actions.append(_parse_token(match.group(1)))
        else:
            raise MacroError(
                f"unmatched {token!r} at position {match.start()} "
                "(write {{ or }} for a literal brace)"
            )
    text += source[pos:]
    if text:
        actions.append(TypeText(text))
    return actions


def _parse_token(body: str) -> Action:
    words = body.split()
    if not words or len(words) > 2:
        raise MacroError(f"can't understand {{{body}}}")
    name = words[0].lower()
    arg = words[1] if len(words) == 2 else None

    if name in _DELAY_WORDS:
        try:
            seconds = float(arg) if arg is not None else -1
        except ValueError:
            seconds = -1
        if seconds < 0:
            raise MacroError(f"{{{body}}} needs a number of seconds, e.g. {{DELAY 0.5}}")
        return Delay(seconds)

    times = 1
    if arg is not None:
        if not arg.isdigit() or int(arg) < 1:
            raise MacroError(f"repeat count in {{{body}}} must be a whole number of 1 or more")
        times = int(arg)

    # Split on "+" except a trailing one, so {CMD++} means Cmd and the "+" key.
    *mods, key = re.split(r"\+(?!$)", name)
    keys = []
    for mod in mods:
        if mod not in MODIFIERS:
            raise MacroError(f"unknown modifier {mod!r} in {{{body}}}")
        keys.append(MODIFIERS[mod])
    if key in KEYS:
        keys.append(KEYS[key])
    elif key in MODIFIERS:
        keys.append(MODIFIERS[key])
    elif len(key) == 1:
        keys.append(key)
    else:
        raise MacroError(f"unknown key {key!r} in {{{body}}}")
    return PressKeys(tuple(keys), times)
