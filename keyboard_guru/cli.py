"""Command line entry point: ``keyboard-guru [--check] [CONFIG]``."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional

from .config import DEFAULT_PATH, ConfigError, load
from .macro import PressKeys


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="keyboard-guru",
        description="Type a trigger like ';addr' and have it replaced by text and keystrokes.",
    )
    parser.add_argument(
        "config",
        nargs="?",
        type=Path,
        default=DEFAULT_PATH,
        help=f"snippets file (default: {DEFAULT_PATH})",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate the file and list what each snippet will do, without listening",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="keyboard-guru: %(message)s")

    try:
        config = load(args.config)
    except ConfigError as err:
        print(f"keyboard-guru: {err}", file=sys.stderr)
        if not args.config.exists():
            print("Copy snippets.example.yaml there to get started.", file=sys.stderr)
        return 1

    if args.check:
        for snippet in config.snippets:
            print(snippet.trigger)
            if snippet.delete_trigger:
                print(f"  {PressKeys(('backspace',), len(snippet.trigger))}")
            for action in snippet.actions:
                print(f"  {action}")
        return 0

    from .engine import run

    triggers = ", ".join(snippet.trigger for snippet in config.snippets)
    print(f"keyboard-guru: watching for {triggers}. Press Ctrl+C to stop.")
    try:
        run(config)
    except KeyboardInterrupt:
        return 0
    except (ImportError, RuntimeError) as err:
        print(f"keyboard-guru: {err}", file=sys.stderr)
        return 1
    return 0
