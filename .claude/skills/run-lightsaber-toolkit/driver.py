#!/usr/bin/env python3
"""End-to-end smoke test for the toolkit — no saber, no 3 GB model.

The tools normally read a real Proffieboard SD card and transcribe it with
Whisper. Neither is available to someone who just cloned this repo, so this
driver builds a fake card out of generated WAV files, hands the tools a
hand-written library, and drives every command that does not need the model:

    scan      transcribe.py --count-only   (reports scale, skips the model)
    report    report.py                    (library JSON -> readable tables)
    search    search.py                    (find a line by what is said)
    swap      batch_swap.ps1               (preview -> apply -> rollback)
    tests     pytest

Everything happens in a temp directory that is deleted afterwards. Nothing
touches a real card.

USAGE
    python .claude/skills/run-lightsaber-toolkit/driver.py
    python .claude/skills/run-lightsaber-toolkit/driver.py --keep   # inspect the fake card
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import struct
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]

# Font layout mirrors a real card: one font flat, one with subdirectories,
# because ProffieOS accepts both and the tools have to cope with each.
FONTS = {
    "IWVader": {
        "flat": True,
        "files": {
            "font.wav": 3.9, "quote01.wav": 2.8, "quote02.wav": 1.3,
            "quote03.wav": 0.8, "hum.wav": 4.0, "clsh1.wav": 0.9,
            "blst1.wav": 0.7, "swng1.wav": 0.5,
        },
    },
    "Emperor": {
        "flat": False,  # font/font.wav, force/force1.wav — directory layout
        "files": {
            "font/font.wav": 2.4, "force/force1.wav": 2.2,
            "force/force2.wav": 3.5, "hum.wav": 4.0, "clsh1.wav": 0.9,
        },
    },
}

LIBRARY = [
    {"font": "IWVader", "file": "quote01.wav", "family": "quote", "seconds": 2.8,
     "text": "What is thy bidding, my master?", "is_speech": True, "no_speech_prob": 0.01},
    {"font": "IWVader", "file": "quote02.wav", "family": "quote", "seconds": 1.3,
     "text": "I am your father.", "is_speech": True, "no_speech_prob": 0.01},
    {"font": "IWVader", "file": "quote03.wav", "family": "quote", "seconds": 0.8,
     "text": "Good.", "is_speech": True, "no_speech_prob": 0.04},
    {"font": "IWVader", "file": "clsh1.wav", "family": "clsh", "seconds": 0.9,
     "text": "", "is_speech": False, "no_speech_prob": 1.0},
    {"font": "Emperor", "file": "force/force2.wav", "family": "force", "seconds": 3.5,
     "text": "I am the Senate.", "is_speech": True, "no_speech_prob": 0.03},
    # Whisper's stock filler on audio with no speech — report.py must FLAG this,
    # not drop it, because unusual real speech would be lost by deleting on suspicion.
    {"font": "Emperor", "file": "force/force1.wav", "family": "force", "seconds": 2.2,
     "text": "Thank you.", "is_speech": True, "no_speech_prob": 0.93},
]

OK, FAIL = "  [ ok ]", "  [FAIL]"
failures: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    print(f"{OK if condition else FAIL} {label}" + (f"  {detail}" if detail else ""))
    if not condition:
        failures.append(label)


def write_wav(path: Path, seconds: float, freq: int = 220) -> None:
    """44.1 kHz / mono / 16-bit — the only format ProffieOS accepts."""
    path.parent.mkdir(parents=True, exist_ok=True)
    rate = 44100
    with wave.open(str(path), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        frames = bytearray()
        for i in range(int(rate * seconds)):
            frames += struct.pack("<h", int(12000 * math.sin(2 * math.pi * freq * i / rate)))
        w.writeframes(bytes(frames))


def build_card(root: Path) -> int:
    count = 0
    for font, spec in FONTS.items():
        for name, secs in spec["files"].items():
            write_wav(root / font / name, secs, 220 if "quote" in name else 90)
            count += 1
    return count


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def powershell() -> str | None:
    for exe in ("pwsh", "powershell"):
        if shutil.which(exe):
            return exe
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true", help="do not delete the fake card")
    args = ap.parse_args()

    work = Path(tempfile.mkdtemp(prefix="saber-smoke-"))
    card = work / "card"
    lib = work / "sound-library.json"
    print(f"repo: {REPO}\nwork: {work}\n")

    # Both heavy deps are imported LAZILY inside the tools, so --help and
    # --count-only work without them and the failure only shows up mid-run.
    # Say up front what is and is not available.
    print("optional dependencies:")
    for mod, tool, why in (("faster_whisper", "transcribe.py", "full transcription (~3 GB model)"),
                           ("transformers", "classify.py", "speech-vs-sound classifier")):
        try:
            __import__(mod)
            print(f"  present  {mod:16} -> {tool} fully usable")
        except ImportError:
            print(f"  MISSING  {mod:16} -> {tool} limited: {why} unavailable")
    print("  (this driver deliberately exercises only the paths that need neither)\n")

    try:
        n = build_card(card)
        print(f"fake card: {n} WAV files across {len(FONTS)} fonts "
              f"(one flat layout, one with subdirectories)\n")

        # --- scan: reports scale WITHOUT downloading the model -----------------
        r = run([sys.executable, "tools/transcribe.py", "--source", str(card),
                 "--count-only"], REPO)
        check("transcribe --count-only exits 0", r.returncode == 0,
              r.stderr.strip().splitlines()[-1] if r.returncode else "")
        check("...and reports files it would transcribe",
              any(ch.isdigit() for ch in r.stdout), r.stdout.strip().replace("\n", " | ")[:96])
        check("...without pulling the 3 GB model", "large-v3" not in r.stdout.lower())

        lib.write_text(json.dumps(LIBRARY, ensure_ascii=False, indent=1), "utf-8")

        # --- report: library -> readable tables ---------------------------------
        out_md = work / "sound-library.md"
        r = run([sys.executable, "tools/report.py", "--library", str(lib),
                 "--out", str(out_md)], REPO)
        check("report.py exits 0", r.returncode == 0, r.stderr.strip()[:96])
        md = out_md.read_text("utf-8") if out_md.exists() else ""
        check("report groups by font", "## IWVader" in md and "## Emperor" in md)
        check("report keeps only spoken files", "clsh1.wav" not in md)
        check("report FLAGS doubtful text instead of dropping it",
              "Thank you." in md and "⚠️" in md)

        # --- search: find a line by what is said --------------------------------
        r = run([sys.executable, "tools/search.py", "i am your father",
                 "--library", str(lib)], REPO)
        check("search finds the line", r.returncode == 0 and "quote02.wav" in r.stdout)
        check("...and returns a ready play command", "play IWVader/quote02.wav" in r.stdout,
              r.stdout.strip().splitlines()[-1].strip() if r.stdout.strip() else "")
        r = run([sys.executable, "tools/search.py", "zzz-no-such-line",
                 "--library", str(lib)], REPO)
        check("search reports a miss cleanly", r.returncode == 0 and "No match" in r.stdout)

        # --- swap: preview -> apply -> rollback ---------------------------------
        ps = powershell()
        if not ps:
            print(f"{FAIL} PowerShell not found — batch_swap.ps1 skipped")
            failures.append("batch_swap.ps1 unavailable")
        else:
            batch = work / "batch.json"
            batch.write_text(json.dumps([{
                "id": "S1", "preset": 12, "font": "IWVader",
                "source": "card:IWVader/quote03.wav", "target": "IWVader/font.wav",
                "backup": True, "description": "announcement <- Good.",
            }], indent=1), "utf-8")
            script = str(REPO / "tools" / "batch_swap.ps1")
            before = (card / "IWVader" / "font.wav").stat().st_size

            r = run([ps, "-NoProfile", "-File", script, "-Card", str(card),
                     "-Batch", str(batch)], REPO)
            check("batch_swap preview exits 0", r.returncode == 0, r.stderr.strip()[:96])
            check("...and writes nothing without -Apply",
                  (card / "IWVader" / "font.wav").stat().st_size == before)

            r = run([ps, "-NoProfile", "-File", script, "-Card", str(card),
                     "-Batch", str(batch), "-Apply"], REPO)
            check("batch_swap -Apply exits 0", r.returncode == 0, r.stderr.strip()[:96])
            check("...target replaced",
                  (card / "IWVader" / "font.wav").stat().st_size != before)
            check("...original kept as .bak", (card / "IWVader" / "font.wav.bak").exists())

            r = run([ps, "-NoProfile", "-File", script, "-Card", str(card),
                     "-Batch", str(batch), "-Rollback"], REPO)
            check("batch_swap -Rollback exits 0", r.returncode == 0, r.stderr.strip()[:96])
            check("...original restored",
                  (card / "IWVader" / "font.wav").stat().st_size == before)

        # --- the project's own tests --------------------------------------------
        r = run([sys.executable, "-m", "pytest", "-q"], REPO)
        last = [l for l in r.stdout.strip().splitlines() if l.strip()]
        check("pytest passes", r.returncode == 0, last[-1] if last else r.stderr[:96])

    finally:
        if args.keep:
            print(f"\nfake card kept at: {work}")
        else:
            shutil.rmtree(work, ignore_errors=True)

    print()
    if failures:
        print(f"FAILED ({len(failures)}): " + "; ".join(failures))
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
