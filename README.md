# keyboard-guru

A tiny [Keyboard Maestro](https://www.keyboardmaestro.com/)-style text expander.
Type a trigger such as `;addr` in any app. keyboard-guru erases it and plays
back whatever you defined: text, then Tab to the next field, more text, Enter.

```yaml
snippets:
  - trigger: ";addr"
    expand: "Jane Doe{TAB}221B Baker Street{TAB}London{ENTER}"
```

## Quick start (macOS)

```sh
git clone https://github.com/nagarsuresh/keyboard-guru.git
cd keyboard-guru
python3 -m venv .venv
source .venv/bin/activate
pip install .

cp snippets.example.yaml ~/.keyboard-guru.yaml
keyboard-guru
```

The first run needs two permissions. Open **System Settings → Privacy &
Security** and add the terminal you run it from (Terminal, iTerm, ...) under
both **Accessibility** and **Input Monitoring**. Then quit and reopen the
terminal and run `keyboard-guru` again.

Leave it running in that terminal window and type `;sig` in any text field to try it.
Press Ctrl+C to stop. To keep it running without a Terminal window, see
[Running in the background](#running-in-the-background).

## Where it works

keyboard-guru watches the keyboard for the whole Mac, not for one app, so
triggers work wherever you type: Chrome (web pages and the address bar),
Safari, Gmail, Slack, Notes, VS Code and so on. The exceptions:

- **Password fields.** While a password field has focus, macOS hides
  keystrokes from tools like this (Secure Input), so triggers don't fire
  there. Some password managers and banking apps turn Secure Input on while
  they are open.
- **Forms that react to each field.** If a web page loads something after you
  Tab (an address lookup, say), it can drop keys. Add `{DELAY 0.3}` after that
  `{TAB}`, or raise `key_delay`.

## Running in the background

keyboard-guru keeps running as long as the Terminal window you started it from
stays open. That Terminal doesn't have to be the active app: minimise it and
work in Chrome as usual.

To keep it running after you close the Terminal window, start it with `nohup`
from the keyboard-guru folder:

```sh
cd keyboard-guru
nohup .venv/bin/keyboard-guru > ~/keyboard-guru.log 2>&1 & disown
```

It then runs until you log out or restart the Mac, and each expansion is
logged to `~/keyboard-guru.log`.

```sh
pgrep -fl bin/keyboard-guru   # is it running?
pkill -f bin/keyboard-guru    # stop it
```

After editing your snippets, stop it and start it again. Starting
automatically at login isn't built in yet.

The included script validates the configuration, prevents duplicate instances,
and records a PID and log under `.runtime/`:

```sh
./scripts/background.sh start
./scripts/background.sh status
./scripts/background.sh stop
# Optional explicit configuration:
./scripts/background.sh start /path/to/snippets.yaml
```

It uses `local/snippets.yaml` when present, otherwise `~/.keyboard-guru.yaml`.
After editing snippets, run `stop` then `start`. macOS Accessibility and Input
Monitoring permissions still apply. This starts the process for the current
login session; it does not register a login item.

## Importing Keyboard Maestro macros

Convert an exported `.kmmacros` file without running any of its actions:

```sh
mkdir -p local
.venv/bin/python -m keyboard_guru.import_km /path/to/export.kmmacros \
  --output local/snippets.yaml --report local/import-report.json
```

The importer supports typed string triggers, text typed into the frontmost app,
Tab/Enter/Space/Backspace/Delete/Escape/arrow keystrokes without modifiers, and
fixed repeats. It preserves trigger deletion, escapes literal braces, and omits
disabled actions. Multiple typed triggers become separate snippets.
Keyboard Maestro typing escapes such as `\b`, `\t`, `\r`, `\n`, and `\e` become
Backspace, Tab, Enter, and Escape key presses; `\\` stays a literal backslash.
Unsupported actions cause the entire macro to be skipped, with a reason in the report;
unsupported triggers are also reported. Hotkeys and system actions are not
supported. Trigger matching follows keyboard-guru's case-sensitive suffix rules,
and playback timing can differ from Keyboard Maestro.

Both output files are created with owner-only permissions and refuse to overwrite
existing files. `local/` and `.runtime/` are ignored by Git. The report includes
names and triggers, but no expansion text. Review the report before starting.

## Defining snippets

Snippets live in `~/.keyboard-guru.yaml`. You can pass a different file:
`keyboard-guru path/to/snippets.yaml`. See
[`snippets.example.yaml`](snippets.example.yaml) for a commented example.

```yaml
settings:
  key_delay: 0.01          # seconds between keystrokes (optional)

snippets:
  - trigger: ";sig"        # what you type
    expand: "Best regards,\nJane Doe"

  - trigger: ";addr"       # a list is joined, handy for long sequences
    expand:
      - "Jane Doe{TAB}"
      - "221B Baker Street{TAB}"
      - "{DELAY 0.2}{ENTER}"

  - trigger: "@@"          # keep the typed trigger and edit it yourself:
    delete_trigger: false  # "jane@@" becomes "jane@gmail.com"
    expand: "{BACKSPACE}gmail.com"
```

Inside `expand`, plain text is typed as-is and anything in braces is a key:

| Write | Does |
| --- | --- |
| `{TAB}` `{ENTER}` `{ESC}` `{SPACE}` | press that key |
| `{BACKSPACE}` | erase left (the Mac **delete** key) |
| `{DELETE}` | forward delete |
| `{UP}` `{DOWN}` `{LEFT}` `{RIGHT}` `{HOME}` `{END}` `{PAGEUP}` `{PAGEDOWN}` | move |
| `{F1}` … `{F12}` | function keys |
| `{TAB 3}` | press a key 3 times |
| `{CMD+A}` `{SHIFT+TAB}` `{CMD+SHIFT+Z}` | key combos (`CMD`, `CTRL`, `ALT`/`OPTION`, `SHIFT`) |
| `{DELAY 0.5}` | wait half a second, e.g. for a page to react |
| `{{` `}}` | a literal `{` or `}` |
| `\n` (in double quotes) | Enter |

Names are case-insensitive. Restart keyboard-guru after you edit the file. To
validate the file and see what each snippet will do, without typing anything,
run:

```sh
$ keyboard-guru --check
;sig
  press backspace x4
  type 'Best regards,\nJane Doe'
;addr
  press backspace x5
  type 'Jane Doe'
  press tab
  ...
```

## How it works

- keyboard-guru keeps the last few characters you typed. When they end with a
  trigger, it presses Backspace once per trigger character (unless
  `delete_trigger: false`), then plays the expansion.
- Fixing a typo with Backspace while typing a trigger is fine. Tab, Enter,
  arrow keys and Cmd/Ctrl shortcuts make it forget what you typed, so the
  trigger has to be typed again.
- Keys you press while a snippet is playing are not counted toward triggers.
- Triggers are case-sensitive. If one trigger ends with another (`;a` and
  `;ba`), the longer one wins. Start triggers with a rarely typed character
  such as `;` so they don't fire by accident.

## Other platforms

keyboard-guru also runs on Windows (use `{CTRL+…}` instead of `{CMD+…}`) and
on Linux under X11. Wayland isn't supported.

## Development

```sh
pip install -e '.[test]'
pytest
```

The code is in `keyboard_guru/`:

| File | Purpose |
| --- | --- |
| `macro.py` | parses `expand` strings into actions |
| `matcher.py` | spots triggers in typed text |
| `config.py` | loads and validates the YAML file |
| `engine.py` | the pynput keyboard listener and playback |
| `cli.py` | the command line |
