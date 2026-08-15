---
name: run-lightsaber-toolkit
description: Run, smoke-test, and drive the Proffieboard saber toolkit — transcribe a sound card, search quotes by content, swap files as a reversible batch, run the tests. Use when asked to run, start, build, test, verify, or demo this toolkit, or to check that a change did not break the tools. Works with no lightsaber and no 3 GB model.
---

# Running the saber toolkit

This is **not an app with a window**. It is five command-line tools that read a
Proffieboard's SD card, transcribe the sound fonts with Whisper, and swap files
as reversible batches. Two things a fresh clone does **not** have: a lightsaber,
and the ~3 GB Whisper model.

**So the agent path is a driver that fakes the card and skips the model.** It
generates WAV files, hands the tools a hand-written library, and exercises every
command that does not need Whisper — including a real preview → apply → rollback
cycle on disk.

All paths below are relative to the repo root.

## Run this first

```bash
python .claude/skills/run-lightsaber-toolkit/driver.py
```

Takes about 30 seconds. Ends with `all checks passed` (exit 0) or
`FAILED (n): ...` (exit 1). It prints which optional dependencies are present,
builds a fake card in a temp directory, runs 18 checks, and deletes the temp
directory afterwards.

To inspect the fake card instead of deleting it:

```bash
python .claude/skills/run-lightsaber-toolkit/driver.py --keep
```

What it covers:

| Step | Tool | What is asserted |
|---|---|---|
| scan | `transcribe.py --count-only` | reports scale, **does not** pull the model |
| report | `report.py` | groups by font, drops non-speech, **flags** doubtful text |
| search | `search.py` | finds a line by content, returns a ready `play` command; clean miss |
| swap | `batch_swap.ps1` | preview writes nothing; `-Apply` replaces + keeps `.bak`; `-Rollback` restores |
| tests | `pytest -q` | 33 tests |

Verified on Windows 11 / Python 3.11.9 / Windows PowerShell 5.1.

## Prerequisites

Python 3.11+ and PowerShell. Nothing else is needed for the driver — it runs on
a bare interpreter with no `pip install` at all.

The driver reports these as MISSING and skips the paths that need them:

```bash
pip install faster-whisper        # full transcription; downloads ~3 GB on first run
pip install transformers torch    # classify.py (speech-vs-sound); ~740 MB
```

## Run the tools by hand

Only after the driver passes. **`--source` and `-Card` take any directory**, so
everything below works without a saber — point them at a folder of `.wav` files.
A real card mounts at `E:` on Windows.

```bash
# how big is the job? no model needed, safe anywhere
python tools/transcribe.py --source /path/to/wavs --count-only
#   -> Candidates: 8 | new: 8 / Total audio: 0.3 min / families breakdown

# the library as readable tables -> sound-library.md
python tools/report.py
#   -> sound-library.md  --  1 lines across 1 fonts

# find a line by what is actually said
python tools/search.py "i am your father"
#   ->   1.3s  IWVader/quote02.wav
#        "I am your father."
#        play IWVader/quote02.wav
```

Both `report.py` and `search.py` read `sound-library.json` from the **current
directory** unless you pass `--library`.

Full transcription needs the model and writes that library:

```bash
python tools/transcribe.py --source /path/to/wavs     # requires faster-whisper
```

File swaps — **always preview first**. The driver runs this whole cycle against
a temp directory; the same three commands work on a real card:

```powershell
.\tools\batch_swap.ps1 -Card <dir-or-E:> -Batch examples\swap-batch.example.json
.\tools\batch_swap.ps1 -Card <dir-or-E:> -Batch examples\swap-batch.example.json -Apply
.\tools\batch_swap.ps1 -Card <dir-or-E:> -Batch examples\swap-batch.example.json -Rollback
```

⚠️ `examples/swap-batch.example.json` references real font names
(`IWLuke`, `Emperor`, …). Against a card that lacks them the preview stops with
`missing source` and writes nothing — which is the gate working, not a bug.

## Test

```bash
python -m pytest -q
```

33 tests, ~2 s. **Must be run from the repo root** — see Gotchas.

## Gotchas

**Heavy imports are lazy, so failure arrives late.** `transcribe.py` imports
`faster_whisper` at line 172 *inside* `main()`, and `classify.py` imports
`transformers` at line 153 inside a constructor. `--help` and `--count-only`
therefore work fine without either, and you only discover the missing package
after the tool has already started printing progress. The driver's preflight
exists specifically to surface this before you waste a run.

**`classify.py` on an empty directory exits 0 with `No matching files.`** — it
never reaches the import, so a missing `transformers` looks like success. Point
it at a directory that actually contains `.wav` files before concluding it works.

**The tools are CWD-relative.** `search.py` and `report.py` default to
`sound-library.json` in the *current* directory, not next to the script. Run
from the repo root, or pass `--library` / `--out` explicitly.

**`pytest` must run from the repo root.** From anywhere else it fails with
4 collection errors — `conftest.py` is what puts the repo on `sys.path`, and
pytest only picks it up when rootdir is the repo.

**`batch_swap.ps1` takes `-Card <anything>`, not just a drive letter.** That is
what makes hardware-free testing possible; the driver passes it a temp directory.

**A batch that declares `backup: false` on an existing target is a hard error,**
not a warning. This is deliberate — it means the batch is stale or already
applied, and overwriting without a backup would be unrecoverable.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `ModuleNotFoundError: No module named 'faster_whisper'` after progress output | Full transcription needs the model. `pip install faster-whisper`, or use `--count-only`. |
| `ModuleNotFoundError: No module named 'transformers'` | `classify.py` only. `pip install transformers torch`. |
| `No library at sound-library.json.` | Running from the wrong directory, or the library was never built. `cd` to the repo root or pass `--library`. |
| `ERROR: cannot see source E:\` | The card only mounts while the saber is **on** and connected through its **data** port. See `docs/sd-card.md`. Any directory works instead. |
| pytest: `Interrupted: 4 errors during collection` | Ran pytest from outside the repo. `cd` to the repo root. |
| Driver prints `PowerShell not found` | `batch_swap.ps1` cannot be exercised. Install `pwsh`; the other 15 checks still run. |
| `Cannot open DFU device` while flashing | Driver problem on the *board*, not this toolkit. See `docs/driver-war.md`. |

## What this toolkit will not do

It **reads anything on the saber and writes only to the SD card. It never writes
firmware.** That boundary is in `CLAUDE.md` as a rule the agent holds — if asked
to flash, refuse and point at `docs/flashing.md`. It is the reason everything
else can be relaxed about backups.
