"""Load snippets from a YAML file."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Tuple

import yaml

from .macro import Action, MacroError, parse

DEFAULT_PATH = Path.home() / ".keyboard-guru.yaml"

_SNIPPET_FIELDS = {"trigger", "expand", "delete_trigger"}
_SETTINGS_FIELDS = {"key_delay"}


class ConfigError(ValueError):
    """The config file is missing, malformed, or has an invalid snippet."""


@dataclass(frozen=True)
class Snippet:
    trigger: str
    expand: str
    actions: Tuple[Action, ...]
    # Erase the typed trigger with backspaces before running the actions.
    delete_trigger: bool = True


@dataclass(frozen=True)
class Config:
    snippets: Tuple[Snippet, ...]
    # Seconds to wait after each keystroke; raise it if an app drops keys.
    key_delay: float = 0.01


def load(path: Path) -> Config:
    try:
        text = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        raise ConfigError(f"{path} not found") from None
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as err:
        raise ConfigError(f"{path} is not valid YAML: {err}") from None
    return from_dict(data)


def from_dict(data: Any) -> Config:
    if not isinstance(data, dict) or not isinstance(data.get("snippets"), list):
        raise ConfigError("the config needs a 'snippets:' list")
    if not data["snippets"]:
        raise ConfigError("'snippets:' is empty")
    _reject_unknown(data, {"snippets", "settings"}, "top level")

    settings = data.get("settings") or {}
    if not isinstance(settings, dict):
        raise ConfigError("'settings:' must be a mapping")
    _reject_unknown(settings, _SETTINGS_FIELDS, "settings")
    key_delay = settings.get("key_delay", Config.key_delay)
    if isinstance(key_delay, bool) or not isinstance(key_delay, (int, float)) or key_delay < 0:
        raise ConfigError("settings.key_delay must be a number of seconds, 0 or more")

    snippets = []
    seen = set()
    for number, item in enumerate(data["snippets"], start=1):
        snippet = _snippet(item, f"snippet #{number}")
        if snippet.trigger in seen:
            raise ConfigError(f"snippet #{number}: trigger {snippet.trigger!r} is defined twice")
        seen.add(snippet.trigger)
        snippets.append(snippet)
    return Config(tuple(snippets), float(key_delay))


def _snippet(item: Any, where: str) -> Snippet:
    if not isinstance(item, dict):
        raise ConfigError(f"{where}: expected 'trigger:' and 'expand:' fields")
    _reject_unknown(item, _SNIPPET_FIELDS, where)

    trigger = item.get("trigger")
    if not isinstance(trigger, str) or not trigger:
        raise ConfigError(f"{where}: 'trigger' must be a non-empty string")
    if "\n" in trigger or "\t" in trigger:
        raise ConfigError(f"{where}: 'trigger' can't contain tabs or newlines")
    where = f"{where} ({trigger})"

    expand = item.get("expand")
    # A list of strings is joined, so long sequences can be split over lines.
    if isinstance(expand, list) and all(isinstance(part, str) for part in expand):
        expand = "".join(expand)
    if not isinstance(expand, str):
        raise ConfigError(f"{where}: 'expand' must be a string or a list of strings")

    delete_trigger = item.get("delete_trigger", True)
    if not isinstance(delete_trigger, bool):
        raise ConfigError(f"{where}: 'delete_trigger' must be true or false")

    try:
        actions = parse(expand)
    except MacroError as err:
        raise ConfigError(f"{where}: {err}") from None
    return Snippet(trigger, expand, tuple(actions), delete_trigger)


def _reject_unknown(data: dict, allowed: set, where: str) -> None:
    unknown = sorted(str(key) for key in data if key not in allowed)
    if unknown:
        raise ConfigError(
            f"{where}: unknown field(s) {', '.join(unknown)} "
            f"(expected {', '.join(sorted(allowed))})"
        )
