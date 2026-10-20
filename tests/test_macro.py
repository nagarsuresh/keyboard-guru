import pytest

from keyboard_guru.macro import Delay, MacroError, PressKeys, TypeText, parse


def test_plain_text():
    assert parse("hello world") == [TypeText("hello world")]


def test_empty_string():
    assert parse("") == []


def test_text_and_keys():
    assert parse("Jane{TAB}Doe{ENTER}") == [
        TypeText("Jane"),
        PressKeys(("tab",)),
        TypeText("Doe"),
        PressKeys(("enter",)),
    ]


def test_names_are_case_insensitive_and_have_aliases():
    assert parse("{Return}{bs}{Escape}{PgDn}") == [
        PressKeys(("enter",)),
        PressKeys(("backspace",)),
        PressKeys(("esc",)),
        PressKeys(("page_down",)),
    ]


def test_repeat_count():
    assert parse("{BACKSPACE 3}") == [PressKeys(("backspace",), 3)]


def test_key_combos():
    assert parse("{CMD+A}{Shift+Tab}{ctrl+alt+delete}{OPTION+F12}") == [
        PressKeys(("cmd", "a")),
        PressKeys(("shift", "tab")),
        PressKeys(("ctrl", "alt", "delete")),
        PressKeys(("alt", "f12")),
    ]


def test_combo_with_plus_key():
    assert parse("{CMD++}") == [PressKeys(("cmd", "+"))]


def test_single_character_key():
    assert parse("{x}") == [PressKeys(("x",))]


def test_delay():
    assert parse("a{DELAY 0.5}b{WAIT 2}") == [
        TypeText("a"),
        Delay(0.5),
        TypeText("b"),
        Delay(2.0),
    ]


def test_escaped_braces():
    assert parse("{{TAB}} and }}") == [TypeText("{TAB} and }")]


def test_newline_stays_in_text():
    assert parse("a\nb") == [TypeText("a\nb")]


@pytest.mark.parametrize(
    "source, message",
    [
        ("{TAB", "unmatched '{'"),
        ("TAB}", "unmatched '}'"),
        ("{}", "can't understand"),
        ("{TAB 1 2}", "can't understand"),
        ("{NOPE}", "unknown key 'nope'"),
        ("{HYPER+A}", "unknown modifier 'hyper'"),
        ("{TAB 0}", "repeat count"),
        ("{TAB x}", "repeat count"),
        ("{DELAY}", "needs a number of seconds"),
        ("{DELAY -1}", "needs a number of seconds"),
        ("{DELAY soon}", "needs a number of seconds"),
    ],
)
def test_errors(source, message):
    with pytest.raises(MacroError, match=message):
        parse(source)


def test_descriptions():
    assert str(TypeText("hi")) == "type 'hi'"
    assert str(PressKeys(("cmd", "a"))) == "press cmd+a"
    assert str(PressKeys(("tab",), 3)) == "press tab x3"
    assert str(Delay(0.5)) == "wait 0.5s"
