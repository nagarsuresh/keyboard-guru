"""Watch the keyboard, spot triggers, and play back their actions."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Iterable

from .config import Config, Snippet
from .macro import Action, Delay, PressKeys, TypeText
from .matcher import Matcher

log = logging.getLogger(__name__)

# Pause before replaying (so the app has received the trigger's last key)
# and after (so our own keystrokes have drained before we listen again).
SETTLE_SECONDS = 0.05

PERMISSION_HINT = (
    "On macOS, open System Settings > Privacy & Security and allow your terminal app "
    "under both Accessibility and Input Monitoring, then restart keyboard-guru."
)


class Player:
    """Sends actions to a keyboard controller.

    ``keyboard`` is a pynput ``Controller`` (or a fake in tests) and
    ``resolve`` turns a canonical key name such as "tab" into a key it accepts.
    """

    def __init__(
        self,
        keyboard: Any,
        resolve: Callable[[str], Any],
        key_delay: float = 0.01,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self._keyboard = keyboard
        self._resolve = resolve
        self._key_delay = key_delay
        self.sleep = sleep

    def play(self, actions: Iterable[Action]) -> None:
        for action in actions:
            if isinstance(action, TypeText):
                for char in action.text:
                    self._keyboard.type(char)
                    self.sleep(self._key_delay)
            elif isinstance(action, PressKeys):
                self.press(action.keys, action.times)
            elif isinstance(action, Delay):
                self.sleep(action.seconds)

    def press(self, names: Iterable[str], times: int = 1) -> None:
        keys = [self._resolve(name) for name in names]
        for _ in range(times):
            for key in keys:
                self._keyboard.press(key)
            for key in reversed(keys):
                self._keyboard.release(key)
            self.sleep(self._key_delay)


class Expander:
    """Feeds typed characters to a Matcher and runs the snippet it finds.

    The snippet runs on a background thread so the keyboard listener is never
    blocked; while it runs, ``busy`` is set and incoming keys should be ignored.
    """

    def __init__(self, snippets: Iterable[Snippet], player: Player, background: bool = True):
        self._snippets = {snippet.trigger: snippet for snippet in snippets}
        self._matcher = Matcher(self._snippets)
        self._player = player
        self._background = background
        self._busy = threading.Event()

    @property
    def busy(self) -> bool:
        return self._busy.is_set()

    def typed(self, char: str) -> None:
        trigger = self._matcher.feed(char)
        if trigger is None:
            return
        self._busy.set()
        snippet = self._snippets[trigger]
        if self._background:
            threading.Thread(target=self._expand, args=(snippet,), daemon=True).start()
        else:
            self._expand(snippet)

    def backspace(self) -> None:
        self._matcher.backspace()

    def reset(self) -> None:
        self._matcher.reset()

    def _expand(self, snippet: Snippet) -> None:
        try:
            self._player.sleep(SETTLE_SECONDS)
            if snippet.delete_trigger:
                self._player.press(["backspace"], times=len(snippet.trigger))
            self._player.play(snippet.actions)
            self._player.sleep(SETTLE_SECONDS)
            log.info("expanded %s", snippet.trigger)
        except Exception:
            log.exception("failed to expand %s", snippet.trigger)
        finally:
            self._matcher.reset()
            self._busy.clear()


def run(config: Config) -> None:
    """Listen to the keyboard and expand snippets until interrupted."""
    # Imported here: pynput needs a display/accessibility access as soon as it
    # loads, and the rest of the package (and its tests) shouldn't.
    from pynput import keyboard

    Key = keyboard.Key

    def resolve(name: str) -> Any:
        return name if len(name) == 1 else Key[name]

    def keys(*names: str) -> set:
        return {getattr(Key, name) for name in names if hasattr(Key, name)}

    # Cmd/Ctrl mean a shortcut (Cmd+V, Ctrl+A...) rather than typing.
    shortcut_modifiers = keys("cmd", "cmd_l", "cmd_r", "ctrl", "ctrl_l", "ctrl_r")
    # Shift/Option change which character is typed, so they don't interrupt.
    typing_modifiers = keys("shift", "shift_l", "shift_r", "alt", "alt_l", "alt_r", "alt_gr", "caps_lock")
    held = set()

    player = Player(keyboard.Controller(), resolve, config.key_delay)
    expander = Expander(config.snippets, player)

    def on_press(key: Any, injected: bool) -> None:
        # Ignore the keystrokes we send ourselves.
        if injected or expander.busy:
            return
        if key in shortcut_modifiers:
            held.add(key)
            return
        if key in typing_modifiers:
            return
        char = " " if key == Key.space else getattr(key, "char", None)
        if held:
            expander.reset()
        elif char:
            expander.typed(char)
        elif key == Key.backspace:
            expander.backspace()
        else:
            # Tab, Enter, arrows...: the cursor has moved, so start over.
            expander.reset()

    def on_release(key: Any, injected: bool) -> None:
        held.discard(key)

    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.wait()
        if getattr(listener, "IS_TRUSTED", True) is False:
            log.warning("keyboard-guru isn't allowed to watch the keyboard yet. %s", PERMISSION_HINT)
        listener.join()
    # join() only returns by itself when the listener couldn't start.
    raise RuntimeError(f"the keyboard listener stopped. {PERMISSION_HINT}")
