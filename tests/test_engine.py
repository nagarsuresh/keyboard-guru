from keyboard_guru.config import from_dict
from keyboard_guru.engine import Expander, Player
from keyboard_guru.macro import parse


class FakeKeyboard:
    def __init__(self):
        self.events = []

    def type(self, char):
        self.events.append(("type", char))

    def press(self, key):
        self.events.append(("press", key))

    def release(self, key):
        self.events.append(("release", key))


def make_player():
    keyboard = FakeKeyboard()
    sleeps = []
    player = Player(keyboard, resolve=lambda name: f"<{name}>", key_delay=0.01, sleep=sleeps.append)
    return player, keyboard, sleeps


def make_expander(snippets):
    player, keyboard, sleeps = make_player()
    config = from_dict({"snippets": snippets})
    return Expander(config.snippets, player, background=False), keyboard, sleeps


def test_player_types_characters_one_by_one():
    player, keyboard, sleeps = make_player()
    player.play(parse("hi"))
    assert keyboard.events == [("type", "h"), ("type", "i")]
    assert sleeps == [0.01, 0.01]


def test_player_presses_combos_and_repeats():
    player, keyboard, _ = make_player()
    player.play(parse("{CMD+A}{TAB 2}"))
    assert keyboard.events == [
        ("press", "<cmd>"),
        ("press", "<a>"),
        ("release", "<a>"),
        ("release", "<cmd>"),
        ("press", "<tab>"),
        ("release", "<tab>"),
        ("press", "<tab>"),
        ("release", "<tab>"),
    ]


def test_player_delays():
    player, keyboard, sleeps = make_player()
    player.play(parse("{DELAY 1.5}"))
    assert keyboard.events == []
    assert sleeps == [1.5]


def test_expander_erases_trigger_then_plays_snippet():
    expander, keyboard, _ = make_expander([{"trigger": ";x", "expand": "a{TAB}b"}])
    for char in "hello ;x":
        expander.typed(char)
    assert keyboard.events == [
        ("press", "<backspace>"),
        ("release", "<backspace>"),
        ("press", "<backspace>"),
        ("release", "<backspace>"),
        ("type", "a"),
        ("press", "<tab>"),
        ("release", "<tab>"),
        ("type", "b"),
    ]
    assert not expander.busy


def test_expander_can_keep_trigger():
    expander, keyboard, _ = make_expander(
        [{"trigger": "@@", "expand": "{BACKSPACE}gmail.com", "delete_trigger": False}]
    )
    for char in "jane@@":
        expander.typed(char)
    assert keyboard.events[:2] == [("press", "<backspace>"), ("release", "<backspace>")]
    assert "".join(char for kind, char in keyboard.events if kind == "type") == "gmail.com"


def test_expander_ignores_text_without_trigger():
    expander, keyboard, _ = make_expander([{"trigger": ";x", "expand": "y"}])
    for char in "just typing":
        expander.typed(char)
    assert keyboard.events == []


def test_expander_reset_breaks_a_trigger():
    expander, keyboard, _ = make_expander([{"trigger": ";x", "expand": "y"}])
    expander.typed(";")
    expander.reset()
    expander.typed("x")
    assert keyboard.events == []


def test_expander_survives_a_failing_keyboard(caplog):
    expander, keyboard, _ = make_expander([{"trigger": ";x", "expand": "y"}])

    def boom(char):
        raise OSError("no keyboard")

    keyboard.type = boom
    for char in ";x":
        expander.typed(char)
    assert "failed to expand ;x" in caplog.text
    assert not expander.busy
