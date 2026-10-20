"""Spot when the most recently typed characters spell out a trigger."""

from __future__ import annotations

from typing import Iterable, Optional


class Matcher:
    def __init__(self, triggers: Iterable[str]):
        # Longest first, so ";addr2" wins over ";addr" when both match.
        self._triggers = sorted(set(triggers), key=len, reverse=True)
        self._longest = max(map(len, self._triggers), default=0)
        self._buffer = ""

    def feed(self, char: str) -> Optional[str]:
        """Record a typed character; return the trigger it completes, if any."""
        if not self._longest:
            return None
        self._buffer = (self._buffer + char)[-self._longest :]
        for trigger in self._triggers:
            if self._buffer.endswith(trigger):
                self._buffer = ""
                return trigger
        return None

    def backspace(self) -> None:
        self._buffer = self._buffer[:-1]

    def reset(self) -> None:
        self._buffer = ""
