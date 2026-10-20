from pathlib import Path

import pytest

from keyboard_guru.config import ConfigError, from_dict, load
from keyboard_guru.macro import PressKeys, TypeText

EXAMPLE = Path(__file__).parent.parent / "snippets.example.yaml"


def test_example_file_loads():
    config = load(EXAMPLE)
    assert [snippet.trigger for snippet in config.snippets] == [";sig", ";addr", ";email", "@@", ";()"]
    assert config.key_delay == 0.01


def test_snippet_defaults():
    config = from_dict({"snippets": [{"trigger": ";hi", "expand": "Hello{ENTER}"}]})
    (snippet,) = config.snippets
    assert snippet.trigger == ";hi"
    assert snippet.actions == (TypeText("Hello"), PressKeys(("enter",)))
    assert snippet.delete_trigger is True
    assert config.key_delay == 0.01


def test_expand_list_is_joined():
    config = from_dict({"snippets": [{"trigger": "x", "expand": ["a{TAB}", "b"]}]})
    assert config.snippets[0].expand == "a{TAB}b"


def test_settings():
    config = from_dict(
        {
            "settings": {"key_delay": 0},
            "snippets": [{"trigger": "x", "expand": "y", "delete_trigger": False}],
        }
    )
    assert config.key_delay == 0
    assert config.snippets[0].delete_trigger is False


def test_missing_file(tmp_path):
    with pytest.raises(ConfigError, match="not found"):
        load(tmp_path / "nope.yaml")


def test_invalid_yaml(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text("snippets: [", encoding="utf-8")
    with pytest.raises(ConfigError, match="not valid YAML"):
        load(path)


@pytest.mark.parametrize(
    "data, message",
    [
        (None, "needs a 'snippets:' list"),
        ({"snippets": []}, "is empty"),
        ({"snippets": [{}], "extra": 1}, "unknown field"),
        ({"snippets": ["x"]}, "expected 'trigger:'"),
        ({"snippets": [{"trigger": "", "expand": "y"}]}, "non-empty string"),
        ({"snippets": [{"trigger": 5, "expand": "y"}]}, "non-empty string"),
        ({"snippets": [{"trigger": "a\tb", "expand": "y"}]}, "tabs or newlines"),
        ({"snippets": [{"trigger": "x"}]}, "string or a list of strings"),
        ({"snippets": [{"trigger": "x", "expand": ["a", 1]}]}, "string or a list of strings"),
        ({"snippets": [{"trigger": "x", "expnd": "y"}]}, r"unknown field\(s\) expnd"),
        ({"snippets": [{"trigger": "x", "expand": "{NOPE}"}]}, r"snippet #1 \(x\): unknown key"),
        ({"snippets": [{"trigger": "x", "expand": "y", "delete_trigger": "no"}]}, "true or false"),
        ({"snippets": [{"trigger": "x", "expand": "a"}, {"trigger": "x", "expand": "b"}]}, "defined twice"),
        ({"settings": {"key_delay": -1}, "snippets": [{"trigger": "x", "expand": "y"}]}, "key_delay"),
        ({"settings": {"key_delay": True}, "snippets": [{"trigger": "x", "expand": "y"}]}, "key_delay"),
        ({"settings": {"speed": 1}, "snippets": [{"trigger": "x", "expand": "y"}]}, "settings: unknown"),
    ],
)
def test_errors(data, message):
    with pytest.raises(ConfigError, match=message):
        from_dict(data)
