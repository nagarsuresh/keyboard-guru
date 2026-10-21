import pytest

from keyboard_guru.config import from_dict
from keyboard_guru.import_km import convert, write_private
from keyboard_guru.macro import PressKeys, TypeText


def macro(actions, triggers=None, **extra):
    return {"Name": "Example", "Actions": actions, "Triggers": triggers or [
        {"MacroTriggerType": "TypedString", "TypedString": ";x", "SimulateDeletes": True}
    ], **extra}


def text(value, **extra):
    return {"MacroActionType": "InsertText", "Action": "ByTyping", "Text": value, **extra}


def test_conversion_preserves_literal_braces_keys_repeats_and_disabled_actions():
    config, report = convert([{"Macros": [macro([
        text("hello {TAB}"), text("omitted", IsActive=False),
        {"MacroActionType": "SimulateKeystroke", "KeyCode": 48, "Modifiers": 0},
        {"MacroActionType": "Repeat", "CountExpression": "3", "Actions": [
            {"MacroActionType": "SimulateKeystroke", "KeyCode": 123}
        ]},
    ])]}])
    snippet = from_dict(config).snippets[0]
    assert snippet.delete_trigger
    assert snippet.actions == (TypeText("hello {TAB}"), PressKeys(("tab",)),
                               PressKeys(("left",)), PressKeys(("left",)),
                               PressKeys(("left",)))
    assert report["snippet_count"] == 1
    assert report["skipped"] == []


def test_aliases_preserve_delete_setting():
    config, _ = convert([{"Macros": [macro([text("hello")], [
        {"MacroTriggerType": "TypedString", "TypedString": ";a", "SimulateDeletes": True},
        {"MacroTriggerType": "TypedString", "TypedString": ";b", "SimulateDeletes": False},
    ])]}])
    assert [s.delete_trigger for s in from_dict(config).snippets] == [True, False]


def test_km_backspaces_play_as_keys_before_replacement_text():
    config, _ = convert([{"Macros": [macro([text(r"\b\b\b"), text("replacement")])]}])
    actions = from_dict(config).snippets[0].actions
    assert actions == (PressKeys(("backspace",)),) * 3 + (TypeText("replacement"),)
    from keyboard_guru.engine import Expander, Player
    from test_engine import FakeKeyboard

    keyboard = FakeKeyboard()
    player = Player(keyboard, resolve=lambda name: name, sleep=lambda seconds: None)
    expander = Expander(from_dict(config).snippets, player, background=False)
    for char in ";x":
        expander.typed(char)
    # Two keys erase the trigger; three more implement KM's explicit \b escapes.
    assert keyboard.events[:10] == [("press", "backspace"), ("release", "backspace")] * 5
    assert keyboard.events[10:] == [("type", char) for char in "replacement"]


def test_km_typing_escapes_preserve_literal_backslashes_braces_and_unicode():
    config, _ = convert([{"Macros": [macro([
        text("é{literal}" + r"\\b\t\r\n\e" + r"\!\_")
    ])]}])
    assert from_dict(config).snippets[0].actions == (
        TypeText("é{literal}\\b"), PressKeys(("tab",)), PressKeys(("enter",)),
        PressKeys(("enter",)), PressKeys(("esc",)), TypeText(r"\!\_"),
    )


def test_actual_backspace_control_character_is_also_a_key():
    config, _ = convert([{"Macros": [macro([text("x\by")])]}])
    assert from_dict(config).snippets[0].actions == (
        TypeText("x"), PressKeys(("backspace",)), TypeText("y"),
    )


@pytest.mark.parametrize("action", [
    {"MacroActionType": "SystemAction", "SystemAction": "LoginWindow"},
    text("%Variable%name%"),
    text("hello", TargetingType="Specific"),
    {"MacroActionType": "Repeat", "CountExpression": "variable", "Actions": [text("x")]},
])
def test_unsupported_macro_is_skipped_entirely(action):
    config, report = convert([{"Macros": [
        macro([text("keep")]), {**macro([text("partial"), action]), "Name": "Unsupported"}
    ]}])
    assert len(config["snippets"]) == 1
    assert report["skipped"][0]["name"] == "Unsupported"


def test_private_outputs_refuse_overwrite(tmp_path):
    path = tmp_path / "snippets.yaml"
    write_private(path, "private")
    assert path.stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        write_private(path, "replacement")
    assert path.read_text() == "private"
