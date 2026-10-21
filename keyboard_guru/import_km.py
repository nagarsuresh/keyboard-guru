"""Convert supported Keyboard Maestro macros without executing their actions."""

from __future__ import annotations

import argparse
import json
import os
import plistlib
import re
from pathlib import Path

import yaml

from .config import from_dict

# macOS virtual key codes used by exported keystroke actions.
KEY_CODES = {36: "ENTER", 48: "TAB", 49: "SPACE", 51: "BACKSPACE",
             53: "ESC", 117: "DELETE", 123: "LEFT", 124: "RIGHT",
             125: "DOWN", 126: "UP"}


class Unsupported(ValueError):
    pass


def typed_text(source: str) -> str:
    """Translate KM typing escapes into key actions, preserving escaped slashes.

    Do not use unicode_escape: snippets can contain Unicode and literal shell
    backslashes, which must not be decoded as Python string literals.
    """
    escapes = {"b": "\b", "t": "\t", "r": "\r", "n": "\n", "e": "\x1b",
               "a": "\a", "f": "\f", "\\": "\\"}
    controls = {"\b": "{BACKSPACE}", "\t": "{TAB}", "\r": "{ENTER}",
                "\n": "{ENTER}", "\x1b": "{ESC}"}
    parts = []
    position = 0
    while position < len(source):
        char = source[position]
        if char == "\\" and position + 1 < len(source) and source[position + 1] in escapes:
            position += 1
            char = escapes[source[position]]
        if char in "\a\f":
            raise Unsupported("bell or form-feed typing escape")
        parts.append(controls.get(char, char.replace("{", "{{").replace("}", "}}")))
        position += 1
    return "".join(parts)


def actions_to_text(actions: list) -> str:
    parts = []
    for action in actions:
        if action.get("IsActive", True) is False:
            continue
        kind = action.get("MacroActionType")
        if action.get("TargetingType", "Front") != "Front":
            raise Unsupported("action targets a specific application")
        if kind == "InsertText":
            if action.get("Action") != "ByTyping":
                raise Unsupported("text insertion mode is not ByTyping")
            text = action.get("Text", "")
            if re.search(r"%[^%\n]+%", text):
                raise Unsupported("dynamic Keyboard Maestro text tokens")
            parts.append(typed_text(text))
        elif kind == "SimulateKeystroke":
            code = action.get("KeyCode")
            if action.get("Modifiers", 0) or action.get("ReleaseAll", False):
                raise Unsupported("keystroke modifiers or ReleaseAll")
            if code not in KEY_CODES:
                raise Unsupported(f"unsupported key code {code}")
            parts.append("{" + KEY_CODES[code] + "}")
        elif kind == "Repeat":
            count = str(action.get("CountExpression", ""))
            if not count.isdecimal() or not 1 <= int(count) <= 10000:
                raise Unsupported("repeat count is not a fixed integer from 1 to 10000")
            body = actions_to_text(action.get("Actions", []))
            if len(body) * int(count) > 1_000_000:
                raise Unsupported("repeat expands beyond one million characters")
            parts.append(body * int(count))
        else:
            raise Unsupported(f"unsupported action {kind}")
    return "".join(parts)


def convert(groups: list) -> tuple[dict, dict]:
    snippets, imported, skipped = [], [], []
    seen = set()
    for group in groups:
        for macro in group.get("Macros", []):
            name = macro.get("Name", "Unnamed macro")
            try:
                if group.get("Activate", "Normal") != "Normal":
                    raise Unsupported("macro group has activation restrictions")
                if not group.get("IsActive", True) or not macro.get("IsActive", True):
                    raise Unsupported("macro or group is disabled")
                expansion = actions_to_text(macro.get("Actions", []))
                if not expansion:
                    raise Unsupported("no enabled actions")
            except Unsupported as error:
                skipped.append({"name": name, "reason": str(error)})
                continue
            triggers = macro.get("Triggers", [])
            if not triggers:
                skipped.append({"name": name, "reason": "no triggers"})
            for trigger in triggers:
                try:
                    if trigger.get("MacroTriggerType") != "TypedString":
                        raise Unsupported("only typed string triggers are supported")
                    if set(trigger) - {"MacroTriggerType", "TypedString", "SimulateDeletes"}:
                        raise Unsupported("typed trigger has additional matching options")
                    text = trigger.get("TypedString")
                    if text in seen:
                        raise Unsupported("duplicate typed trigger")
                    snippet = {"trigger": text, "expand": expansion,
                               "delete_trigger": trigger.get("SimulateDeletes", False)}
                    from_dict({"snippets": [snippet]})
                except (Unsupported, ValueError) as error:
                    skipped.append({"name": name, "reason": str(error)})
                    continue
                seen.add(text)
                snippets.append(snippet)
                imported.append({"name": name, "trigger": text})
    config = {"settings": {"key_delay": 0.01}, "snippets": snippets}
    from_dict(config)
    report = {"macro_count": sum(len(g.get("Macros", [])) for g in groups),
              "imported_macro_count": len({item["name"] for item in imported}),
              "snippet_count": len(snippets), "imported": imported, "skipped": skipped,
              "notes": ["Fixed repeats are expanded in order; disabled actions are omitted.",
                        "Typed triggers use keyboard-guru's case-sensitive suffix matching.",
                        "Text and keystrokes are preserved; playback timing may differ."]}
    return config, report


def write_private(path: Path, text: str) -> None:
    # Refuse overwrites: existing snippets must be merged deliberately.
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as stream:
        stream.write(text)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    groups = plistlib.loads(args.source.read_bytes())
    config, report = convert(groups)
    if args.output.exists() or args.report.exists():
        parser.error("output or report already exists; choose new paths")
    write_private(args.output, yaml.safe_dump(config, allow_unicode=True, sort_keys=False))
    write_private(args.report, json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(f"Imported {report['imported_macro_count']} macros as {report['snippet_count']} snippets; "
          f"{len(report['skipped'])} skipped entries. Report: {args.report}")


if __name__ == "__main__":
    main()
