"""Tests for the readable listing built from a transcribed sound library."""

from tools.report import build, suspect_reason

ENTRIES = [
    {"font": "IWVader", "file": "quote17.wav", "family": "quote",
     "seconds": 3.9, "text": "I am your father.", "is_speech": True,
     "no_speech_prob": 0.01},
    {"font": "IWVader", "file": "quote09.wav", "family": "quote",
     "seconds": 0.8, "text": "Good.", "is_speech": True,
     "no_speech_prob": 0.05},
    {"font": "IWVader", "file": "clsh01.wav", "family": "clsh",
     "seconds": 0.8, "text": "", "is_speech": False, "no_speech_prob": 1.0},
    {"font": "Emperor", "file": "force/force2.wav", "family": "force",
     "seconds": 2.4, "text": "I am the Senate.", "is_speech": True,
     "no_speech_prob": 0.03},
    # Whisper's stock filler on a file that it also rates as non-speech.
    {"font": "Emperor", "file": "force/force6.wav", "family": "force",
     "seconds": 8.8, "text": "Thank you.", "is_speech": True,
     "no_speech_prob": 0.91},
]


def test_only_spoken_files_reach_the_listing(tmp_path):
    out = tmp_path / "library.md"
    spoken, fonts, _ = build(ENTRIES, out, None)

    assert spoken == 4          # clsh01 has no speech and is left out
    assert fonts == 2
    assert "clsh01.wav" not in out.read_text("utf-8")


def test_grouped_by_font_with_a_table_each(tmp_path):
    out = tmp_path / "library.md"
    build(ENTRIES, out, None)
    text = out.read_text("utf-8")

    assert "## IWVader" in text
    assert "## Emperor" in text
    assert "| File | Sec | ? | Line |" in text
    assert "I am your father." in text


def test_font_filter_narrows_the_listing(tmp_path):
    out = tmp_path / "library.md"
    spoken, fonts, _ = build(ENTRIES, out, "iwvader")   # case-insensitive

    assert fonts == 1
    assert spoken == 2
    assert "Emperor" not in out.read_text("utf-8")


def test_doubtful_transcriptions_are_marked_not_dropped(tmp_path):
    out = tmp_path / "library.md"
    _, _, flagged = build(ENTRIES, out, None)
    text = out.read_text("utf-8")

    assert flagged == 1
    assert "Thank you." in text      # kept, so it can be judged by ear
    assert "⚠️" in text


def test_stock_phrase_alone_is_not_enough_to_flag():
    """The phrase only counts against a file the model also doubts."""
    confident = {"font": "F", "file": "q.wav", "seconds": 1.0,
                 "text": "Yeah.", "is_speech": True, "no_speech_prob": 0.02}
    assert suspect_reason(confident) == ""


def test_long_file_with_almost_no_text_is_flagged():
    sparse = {"font": "F", "file": "q.wav", "seconds": 12.0,
              "text": "Hm.", "is_speech": True, "no_speech_prob": 0.1}
    assert suspect_reason(sparse) != ""


def test_pipe_in_a_line_does_not_break_the_table(tmp_path):
    out = tmp_path / "library.md"
    entries = [{"font": "F", "file": "q.wav", "seconds": 2.0,
                "text": "one | two", "is_speech": True, "no_speech_prob": 0.01}]
    build(entries, out, None)

    row = [ln for ln in out.read_text("utf-8").splitlines() if "q.wav" in ln][0]
    assert "one \\| two" in row     # escaped, so it stays inside one cell
    # 4 columns => 5 cell borders; the escaped pipe must not add a sixth.
    assert row.replace("\\|", "").count("|") == 5
