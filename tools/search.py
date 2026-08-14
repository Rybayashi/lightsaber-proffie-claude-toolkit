"""Search transcribed lines by CONTENT, not by filename.

Filenames tell you nothing useful. "Hello there." lives in quote21.wav and runs
0.6 seconds -- a file most people would dismiss as too short to hold a sentence.
Being able to search by what is actually said is the whole point of building
the library in the first place.

USAGE
    python tools/search.py "i am your father"
    python tools/search.py "jedi" --font IWLuke --max-seconds 3
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# A transcription this uncertain is often invented. Whisper returns fluent
# sentences for audio containing no speech at all, so anything above this
# threshold gets flagged rather than trusted.
SUSPECT_NO_SPEECH_PROB = 0.3


def search(entries, phrase, font=None, max_seconds=None):
    """Entries whose transcribed text contains `phrase`, shortest first."""
    needle = phrase.lower().strip()
    hits = []
    for entry in entries:
        if not entry.get("is_speech"):
            continue
        if needle not in (entry.get("text") or "").lower():
            continue
        if font and entry["font"] != font:
            continue
        if max_seconds is not None and entry["seconds"] > max_seconds:
            continue
        hits.append(entry)
    return sorted(hits, key=lambda e: e["seconds"])


def play_command(entry) -> str:
    """A ProffieOS serial command that plays this file.

    The font prefix matters: `play` searches the active font first and then the
    card root, so prefixing lets you play a line from a font the current preset
    does not use.
    """
    return f"play {entry['font']}/{entry['file']}"


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Search saber quotes by what they actually say.")
    ap.add_argument("phrase")
    ap.add_argument("--library", default="sound-library.json")
    ap.add_argument("--font", default=None, help="limit to one font")
    ap.add_argument("--max-seconds", type=float, default=None,
                    help="useful when looking for a short announcement")
    args = ap.parse_args()

    library = Path(args.library)
    if not library.exists():
        print(f"No library at {library}.", file=sys.stderr)
        print("Build one first:  python tools/transcribe.py --source E:/",
              file=sys.stderr)
        return 1

    hits = search(json.loads(library.read_text("utf-8")), args.phrase,
                  args.font, args.max_seconds)
    if not hits:
        print("No match.")
        return 0

    flagged = False
    for entry in hits:
        suspect = entry.get("no_speech_prob", 0) > SUSPECT_NO_SPEECH_PROB
        flagged = flagged or suspect
        mark = "  [?]" if suspect else ""
        print(f'{entry["seconds"]:>5.1f}s  {entry["font"]}/{entry["file"]}{mark}')
        print(f'       "{entry["text"]}"')
        print(f"       {play_command(entry)}")

    if flagged:
        print("\n[?] = low transcription confidence. Listen to these before "
              "relying on them; the text may be invented.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
