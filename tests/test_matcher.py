from keyboard_guru.matcher import Matcher


def feed(matcher, text):
    return [matcher.feed(char) for char in text]


def test_fires_on_last_character():
    matcher = Matcher([";addr"])
    assert feed(matcher, ";add") == [None] * 4
    assert matcher.feed("r") == ";addr"


def test_fires_after_other_text():
    matcher = Matcher([";sig"])
    assert feed(matcher, "thanks ;sig")[-1] == ";sig"


def test_buffer_clears_after_a_match():
    matcher = Matcher(["ab"])
    assert feed(matcher, "ab") == [None, "ab"]
    assert matcher.feed("b") is None


def test_backspace_corrects_a_typo():
    matcher = Matcher([";sig"])
    feed(matcher, ";sx")
    matcher.backspace()
    assert feed(matcher, "ig")[-1] == ";sig"


def test_reset_forgets_typed_text():
    matcher = Matcher([";sig"])
    feed(matcher, ";si")
    matcher.reset()
    assert matcher.feed("g") is None


def test_longest_trigger_wins():
    matcher = Matcher(["dr", ";addr"])
    assert feed(matcher, ";addr")[-1] == ";addr"


def test_case_sensitive():
    matcher = Matcher([";sig"])
    assert feed(matcher, ";SIG")[-1] is None


def test_no_triggers():
    matcher = Matcher([])
    assert matcher.feed("a") is None
