"""Transcribe the spoken lines on a ProffieOS sound font card.

WHY THIS EXISTS
    A card holds roughly a thousand files named like `quote17.wav`. Font authors
    do not document what is inside them, so the only way to find a specific line
    is to listen to files one at a time. After running this, you can search by
    CONTENT instead -- see tools/search.py.

WHY THE FILTERING MATTERS
    Whisper hallucinates on non-speech audio. Pointed at a blade hum it will
    happily return "Thank you." or trailing subtitle credits, with no signal that
    it made the text up. Three guards keep that out of the library:

      1. families known to be pure sound effects are skipped before transcription
      2. voice activity detection is enabled for everything else
      3. results with a high no-speech probability are marked, not trusted

    Even so, treat any short or odd-looking line as suspect and listen to it
    before relying on it.

USAGE
    python tools/transcribe.py --source E:/ --count-only
    python tools/transcribe.py --source E:/ --only IWVader,IWLuke
    python tools/transcribe.py --source /path/to/card-backup

The model (~3 GB) downloads on first run. Results are written incrementally, so
interrupting and re-running picks up where it stopped.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.sound_library import (  # noqa: E402
    MAX_SECONDS,
    MIN_SECONDS,
    NOISE_FAMILIES,
    SKIPPED_DIRECTORIES,
    SPEECH_FAMILIES,
    effect_family,
    split_font_path,
    wav_duration,
)


def _register_cuda_libraries() -> None:
    """Make pip-installed CUDA libraries visible to Windows.

    The nvidia-cublas-cu12 / nvidia-cudnn-cu12 packages put their DLLs in
    site-packages/nvidia/<lib>/bin, which Windows does not search. Without this
    the model loads fine and the FIRST transcription dies with
    "Library cublas64_12.dll is not found or cannot be loaded" -- a misleading
    error, because nothing is missing, only unfindable.
    """
    if os.name != "nt":
        return
    base = Path(sys.prefix) / "Lib" / "site-packages" / "nvidia"
    if not base.is_dir():
        return
    for directory in sorted(base.glob("*/bin")):
        try:
            os.add_dll_directory(str(directory))
        except (OSError, AttributeError):
            pass


@dataclass
class Entry:
    font: str
    file: str          # path relative to the font directory, e.g. "force/force2.wav"
    family: str        # ProffieOS effect family: quote, font, force, blst, ...
    seconds: float
    text: str
    is_speech: bool
    no_speech_prob: float
    avg_logprob: float


def collect_files(source: Path, include_all: bool, only: set[str] | None) -> list[Path]:
    """Files worth sending to the model."""
    found: list[Path] = []
    for path in sorted(source.rglob("*.wav")):
        font, relative = split_font_path(path, source)
        if only and font not in only:
            continue
        if not include_all:
            if any(part.lower() in SKIPPED_DIRECTORIES for part in path.parts):
                continue  # music, not character audio
            if effect_family(relative) in NOISE_FAMILIES:
                continue
            if wav_duration(path) > MAX_SECONDS:
                continue  # background music in practice
            # Unknown families are let through; VAD will sort them out.
        found.append(path)
    return found


def _report_scale(files: list[Path], source: Path) -> None:
    from collections import Counter

    total = sum(wav_duration(p) for p in files)
    print(f"Total audio: {total / 60:.1f} min")
    counts: Counter[str] = Counter()
    seconds: Counter[str] = Counter()
    for p in files:
        family = effect_family(split_font_path(p, source)[1])
        counts[family] += 1
        seconds[family] += wav_duration(p)
    print("\nFamilies (count / total seconds):")
    for family, n in counts.most_common(20):
        print(f"  {family:<14} {n:>5}   {seconds[family]:>7.1f} s")
    print(f"\nFonts covered: {len({split_font_path(p, source)[0] for p in files})}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Transcribe ProffieOS sound fonts.")
    ap.add_argument("--source", required=True,
                    help="card root or a backup directory, e.g. 'E:/'")
    ap.add_argument("--output", default="sound-library.json")
    ap.add_argument("--only", default="", help="limit to these fonts, comma separated")
    ap.add_argument("--all", action="store_true",
                    help="do not skip families known to be pure sound effects")
    ap.add_argument("--restart", action="store_true", help="ignore previous results")
    ap.add_argument("--count-only", action="store_true",
                    help="report scale and exit without loading the model")
    ap.add_argument("--model", default="large-v3")
    ap.add_argument("--device", default="auto", choices=["auto", "cuda", "cpu"])
    ap.add_argument("--language", default="en", help="forced language; empty to auto-detect")
    args = ap.parse_args()

    source = Path(args.source)
    if not source.exists():
        print(f"ERROR: cannot see source {source}", file=sys.stderr)
        print("If this is the saber's card, see docs/sd-card.md -- the card is only",
              file=sys.stderr)
        print("mounted while the saber is on and connected via its DATA port.", file=sys.stderr)
        return 1

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    previous: dict[str, dict] = {}
    if output.exists() and not args.restart:
        previous = {f"{e['font']}/{e['file']}": e
                    for e in json.loads(output.read_text("utf-8"))}
        print(f"Loaded {len(previous)} entries from a previous run.")

    only = {s.strip() for s in args.only.split(",") if s.strip()} or None
    files = collect_files(source, args.all, only)
    pending = [p for p in files
               if "/".join(split_font_path(p, source)) not in previous]

    print(f"Candidates: {len(files)} | new: {len(pending)}")

    if args.count_only:
        _report_scale(files, source)
        return 0

    if not pending:
        print("Nothing new to do.")
        return 0

    _register_cuda_libraries()
    from faster_whisper import WhisperModel

    device = args.device
    if device == "auto":
        device = "cpu"
        try:
            import ctranslate2

            if ctranslate2.get_cuda_device_count() > 0:
                device = "cuda"
        except Exception:
            pass
    if device == "cpu":
        print("Running on CPU -- expect this to take several times longer than on GPU.")

    compute_type = "float16" if device == "cuda" else "int8"
    print(f"Loading {args.model} on {device} (first run downloads ~3 GB)...")
    started = time.time()
    model = WhisperModel(args.model, device=device, compute_type=compute_type)
    print(f"Model ready in {time.time() - started:.1f} s.")

    entries = list(previous.values())
    started = time.time()

    for index, path in enumerate(pending, 1):
        seconds = wav_duration(path)
        font, relative = split_font_path(path, source)
        family = effect_family(relative)

        if seconds < MIN_SECONDS:
            # Too short to be a sentence; record it without asking the model.
            entries.append(asdict(Entry(font, relative, family, round(seconds, 2),
                                        "", False, 1.0, 0.0)))
            continue

        try:
            segments, _ = model.transcribe(
                str(path),
                language=args.language or None,
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 300},
                beam_size=5,
                # Without this, Whisper carries a hallucination from one file
                # into the next and repeats it.
                condition_on_previous_text=False,
            )
            segments = list(segments)
            text = " ".join(s.text.strip() for s in segments).strip()
            no_speech = min((s.no_speech_prob for s in segments), default=1.0)
            avg_logprob = max((s.avg_logprob for s in segments), default=-10.0)
        except Exception as exc:  # one bad file must not kill the whole run
            print(f"  ! {font}/{relative}: {exc}")
            continue

        is_speech = bool(text) and no_speech < 0.6 and avg_logprob > -1.2
        if family in SPEECH_FAMILIES and text:
            is_speech = True  # trust the family name for quote/font/boot/force

        entries.append(asdict(Entry(font, relative, family, round(seconds, 2),
                                    text, is_speech, round(no_speech, 3),
                                    round(avg_logprob, 3))))

        if index % 25 == 0 or index == len(pending):
            rate = index / max(time.time() - started, 0.001)
            remaining = (len(pending) - index) / max(rate, 0.001)
            print(f"  {index}/{len(pending)}  ({rate:.1f} files/s, "
                  f"~{remaining / 60:.1f} min left)")
            output.write_text(json.dumps(entries, ensure_ascii=False, indent=1), "utf-8")

    output.write_text(json.dumps(entries, ensure_ascii=False, indent=1), "utf-8")
    spoken = sum(1 for e in entries if e["is_speech"])
    print(f"\nDone: {len(entries)} files, {spoken} with speech. -> {output}")
    print("Next: python tools/search.py \"some phrase\"")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
