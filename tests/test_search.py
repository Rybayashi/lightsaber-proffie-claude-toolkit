"""Tests for content search over a transcribed sound library."""

from tools.search import play_command, search

ENTRIES = [
    {"font": "IWVader", "file": "quote17.wav", "family": "quote",
     "seconds": 3.9, "text": "I am your father.", "is_speech": True,
     "no_speech_prob": 0.01},
    {"font": "IWLuke", "file": "quote16.wav", "family": "quote",
     "seconds": 4.7, "text": "I am a Jedi, like my father before me.",
     "is_speech": True, "no_speech_prob": 0.02},
    {"font": "IWVader", "file": "clsh01.wav", "family": "clsh",
     "seconds": 0.8, "text": "", "is_speech": False, "no_speech_prob": 1.0},
    {"font": "Emperor", "file": "force/force2.wav", "family": "force",
     "seconds": 2.4, "text": "I am the Senate.", "is_speech": True,
     "no_speech_prob": 0.03},
]


def test_search_is_case_insensitive():
    assert len(search(ENTRIES, "I AM YOUR FATHER")) == 1


def test_search_matches_a_substring_across_entries():
    assert len(search(ENTRIES, "father")) == 2


def test_search_can_filter_by_font():
    hits = search(ENTRIES, "father", font="IWLuke")
    assert len(hits) == 1 and hits[0]["font"] == "IWLuke"


def test_search_can_filter_by_duration():
    """A saber announcement that runs five seconds is usually too long."""
    hits = search(ENTRIES, "father", max_seconds=4.0)
    assert len(hits) == 1 and hits[0]["file"] == "quote17.wav"


def test_search_ignores_entries_without_speech():
    assert search(ENTRIES, "clsh") == []


def test_search_returns_shortest_first():
    """Shorter lines make better announcements, so surface them first."""
    hits = search(ENTRIES, "i am")
    assert [h["seconds"] for h in hits] == sorted(h["seconds"] for h in hits)


def test_play_command_uses_a_font_relative_path():
    """ProffieOS `play` looks in the active font first, then from the card root.

    Prefixing with the font name is what makes it possible to play a line from
    a DIFFERENT font than the preset currently uses.
    """
    assert play_command(ENTRIES[0]) == "play IWVader/quote17.wav"


def test_play_command_keeps_directory_layout_paths_intact():
    assert play_command(ENTRIES[3]) == "play Emperor/force/force2.wav"
