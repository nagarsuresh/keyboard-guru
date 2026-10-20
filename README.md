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
Press Ctrl+C to stop.

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

## Limitations

- macOS blocks keyboard monitoring in password fields and some apps (Secure Input).
- If an app drops keystrokes, raise `key_delay` or add `{DELAY …}` steps.
- It also runs on Windows (use `{CTRL+…}` instead of `{CMD+…}`) and on Linux
  under X11. Wayland isn't supported.

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
