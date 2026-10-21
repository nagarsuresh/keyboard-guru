#!/bin/bash
set -euo pipefail
umask 077

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STATE="$ROOT/.runtime"
BIN="$ROOT/.venv/bin/keyboard-guru"
PID_FILE="$STATE/keyboard-guru.pid"
LOG="$STATE/keyboard-guru.log"
mkdir -p "$STATE"

if ! mkdir "$STATE/control.lock" 2>/dev/null; then
  echo "Another background control operation is running: $STATE/control.lock" >&2
  exit 1
fi
trap 'rmdir "$STATE/control.lock"' EXIT

running() {
  [[ -f "$PID_FILE" ]] || return 1
  PID="$(cat "$PID_FILE")"
  [[ "$PID" =~ ^[0-9]+$ ]] || return 1
  kill -0 "$PID" 2>/dev/null || return 1
  [[ "$(ps -p "$PID" -o command=)" == *"$BIN"* ]]
}

case "${1:-start}" in
  start)
    if running; then
      echo "keyboard-guru is already running (PID $PID)."
      exit 0
    fi
    DEFAULT_CONFIG="$HOME/.keyboard-guru.yaml"
    if [[ -f "$ROOT/local/snippets.yaml" ]]; then
      DEFAULT_CONFIG="$ROOT/local/snippets.yaml"
    fi
    CONFIG="${2:-$DEFAULT_CONFIG}"
    if [[ ! -x "$BIN" ]]; then
      echo "Install first: python3 -m venv .venv && .venv/bin/pip install ." >&2
      exit 1
    fi
    # Validate without printing any expansion contents to a terminal or log.
    "$ROOT/.venv/bin/python" -c 'import sys; from pathlib import Path; from keyboard_guru.config import load; load(Path(sys.argv[1]))' "$CONFIG"
    nohup "$BIN" "$CONFIG" </dev/null >>"$LOG" 2>&1 &
    PID=$!
    echo "$PID" > "$PID_FILE"
    sleep 1
    if ! running; then
      echo "Startup failed. See $LOG" >&2
      exit 1
    fi
    echo "keyboard-guru started (PID $PID). Log: $LOG"
    echo "If triggers do not fire, allow your terminal under Accessibility and Input Monitoring."
    ;;
  stop)
    if running; then
      kill "$PID"
      for ((attempt=0; attempt<50; attempt++)); do
        if ! running; then break; fi
        sleep 0.1
      done
      if running; then
        echo "Process $PID has not stopped; leaving its PID file in place." >&2
        exit 1
      fi
      echo "keyboard-guru stopped."
    else
      echo "keyboard-guru is not running."
    fi
    # Truncating is safe even when the old PID file was stale.
    : > "$PID_FILE"
    ;;
  status)
    if running; then
      echo "keyboard-guru is running (PID $PID). Log: $LOG"
    else
      echo "keyboard-guru is not running."
      exit 1
    fi
    ;;
  *) echo "Usage: $0 {start [CONFIG]|stop|status}" >&2; exit 2 ;;
esac
