"""Shared primitives for reading a ProffieOS sound font card.

Three tools in this repository need to answer the same two questions about a
file on the card: which font does it belong to, and what triggers it. This
module is the single place where those answers live.
"""

from __future__ import annotations

import re
import wave
from pathlib import Path, PurePath

# Families that are pure sound effects. Running speech recognition over these
# is worse than useless: on non-speech audio Whisper invents text, returning
# things like "Thank you." or trailing subtitle credits.
NOISE_FAMILIES = {
    "hum", "humm", "swng", "swing", "swingl", "swingh", "clsh", "clash",
    "in", "out", "poweron", "poweroff", "pwron", "pwroff",
    "lock", "lockup", "bgnlock", "endlock", "drag", "bgndrag", "enddrag",
    "melt", "bgnmelt", "endmelt", "lb", "bgnlb", "endlb", "lightning",
    "spin", "stab", "preon", "pstoff", "blaster", "bgnstab", "endstab",
    "ccbegin", "ccend", "ccchange", "menu", "beep", "bump", "click",
}

# Families that usually DO contain speech. Worth transcribing even when the
# speech detector is unsure.
SPEECH_FAMILIES = {"quote", "font", "boot", "force", "track"}

# Directories holding music rather than font effects.
SKIPPED_DIRECTORIES = {"tracks", "common"}

# Below this, audio is an artefact rather than a sentence.
MIN_SECONDS = 0.35

# Above this it is background music in practice. Transcribing it costs the
# most time and returns the least value -- nobody needs the lyrics here.
MAX_SECONDS = 30.0

_TRAILING_INDEX = re.compile(r"[\d_]+$")


def sound_family(filename: str) -> str:
    """Effect family from a filename: 'quote17.wav' -> 'quote'."""
    return _TRAILING_INDEX.sub("", PurePath(filename).stem).lower()


def split_font_path(path: PurePath, root: PurePath) -> tuple[str, str]:
    """Split a file path into (font name, path relative to the font directory).

    Fonts ship in two layouts::

        flat:       Emperor/font.wav
        directory:  Emperor/font/font.wav      (the directory is the effect)

    The font name comes from the FIRST directory under the scan root, never
    from the file's parent. Using the parent looks right on the flat layout
    and fails silently on the other one: in the original project it filed 80
    entries under fictional fonts called "font", "force" and "boot", and made
    six real fonts disappear from the library altogether. Nothing about the
    output looked wrong -- the fonts were simply missing.
    """
    relative = path.relative_to(root)
    parts = relative.parts
    if len(parts) == 1:  # file sitting loose in the scan root
        return root.name, parts[0]
    return parts[0], "/".join(parts[1:])


def effect_family(relative_path: str) -> str:
    """Effect family for a path relative to its font directory.

    In the directory layout the DIRECTORY decides, because files there are
    often named with bare digits ('force/0001.wav') and the filename carries
    no information at all.
    """
    parts = relative_path.split("/")
    if len(parts) > 1:
        return parts[0].lower()
    return sound_family(parts[-1])


def wav_duration(path: Path) -> float:
    """Duration in seconds, read from the WAV header.

    Falls back to an estimate from file size when the header is unreadable.
    A single damaged file on a card must never abort a whole scan.
    """
    try:
        with wave.open(str(path), "rb") as w:
            frames = w.getnframes()
            rate = w.getframerate() or 44100
            return frames / float(rate)
    except Exception:
        try:
            # 44.1 kHz / 16-bit / mono is the format ProffieOS expects
            return path.stat().st_size / 88200.0
        except OSError:
            return 0.0


def is_probably_noise(relative_path: str) -> bool:
    """True when the file's family is known to be a pure sound effect."""
    return effect_family(relative_path) in NOISE_FAMILIES


def is_probably_speech(relative_path: str) -> bool:
    """True when the file's family usually carries speech."""
    return effect_family(relative_path) in SPEECH_FAMILIES
