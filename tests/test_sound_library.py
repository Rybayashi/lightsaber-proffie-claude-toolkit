"""Tests for the shared sound-library primitives.

These cover the two mistakes that cost the most in the original project:
resolving a font name from the wrong directory level, and deciding a file's
effect family from its name when the directory is what actually decides it.
"""

from pathlib import PurePosixPath
import wave

import pytest

from tools.sound_library import (
    NOISE_FAMILIES,
    SPEECH_FAMILIES,
    effect_family,
    sound_family,
    split_font_path,
    wav_duration,
)


def test_sound_family_strips_trailing_digits():
    assert sound_family("quote17.wav") == "quote"
    assert sound_family("swingl02.wav") == "swingl"
    assert sound_family("font.wav") == "font"


def test_sound_family_strips_trailing_underscores():
    assert sound_family("blst_1.wav") == "blst"


def test_split_font_path_flat_layout():
    root = PurePosixPath("/card")
    assert split_font_path(PurePosixPath("/card/Emperor/font.wav"), root) == (
        "Emperor",
        "font.wav",
    )


def test_split_font_path_directory_layout():
    """Font name must come from the first directory under the scan root.

    Fonts ship in two layouts: flat (Emperor/font.wav) and directory-based
    (Emperor/font/font.wav). Taking the file's parent directory looks correct
    on the flat layout and silently breaks on the other one -- in the original
    project it filed 80 entries under fictional fonts named "font", "force"
    and "boot", and made 6 real fonts vanish from the library entirely.
    """
    root = PurePosixPath("/card")
    assert split_font_path(PurePosixPath("/card/Emperor/font/font.wav"), root) == (
        "Emperor",
        "font/font.wav",
    )


def test_split_font_path_file_at_root():
    root = PurePosixPath("/card")
    assert split_font_path(PurePosixPath("/card/loose.wav"), root) == (
        "card",
        "loose.wav",
    )


def test_effect_family_uses_directory_when_present():
    """In the directory layout, files are often named with bare digits."""
    assert effect_family("force/0001.wav") == "force"
    assert effect_family("font/font2.wav") == "font"


def test_effect_family_falls_back_to_filename_when_flat():
    assert effect_family("quote17.wav") == "quote"


def test_speech_and_noise_families_are_disjoint():
    """A family cannot be both 'always noise' and 'usually speech'."""
    assert not (NOISE_FAMILIES & SPEECH_FAMILIES)


def test_wav_duration_reads_header(tmp_path):
    p = tmp_path / "tone.wav"
    with wave.open(str(p), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(44100)
        w.writeframes(b"\x00\x00" * 44100)
    assert wav_duration(p) == pytest.approx(1.0, abs=0.01)


def test_wav_duration_survives_a_broken_header(tmp_path):
    """A card with a truncated file must not abort a whole scan."""
    p = tmp_path / "broken.wav"
    p.write_bytes(b"not really a wav")
    assert wav_duration(p) >= 0.0
