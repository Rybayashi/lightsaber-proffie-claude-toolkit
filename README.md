<div align="center">

# 🗡️ lightsaber-proffie-claude-toolkit

**Find out what your saber actually says - then change it, reversibly.**

A card holds a thousand files named `quote17.wav` and no index. This transcribes
them, makes them searchable by what is *said*, and swaps them as an atomic batch
you can roll back. Plus the hardware traps that cost an evening each.

[![License: MIT](https://img.shields.io/badge/License-MIT-e0b64a.svg)](LICENSE)
![Python](https://img.shields.io/badge/python-3.11+-3776AB?logo=python&logoColor=white)
![Tests](https://img.shields.io/badge/tests-26%20passing-4c9a5e)
![ProffieOS](https://img.shields.io/badge/ProffieOS-7.15-6e9b46)

[**Start here**](#start-here-things-that-will-bite-you) ·
[The loop](#the-loop) ·
[Honest scope](#honest-scope) ·
[Safety](SAFETY.md)

</div>

```console
$ python tools/search.py "i am your father"

  3.9s  IWVader/quote17.wav
       "I am your father."
       play IWVader/quote17.wav
```

<!-- TODO: replace the console block above with a real screenshot once one exists:
     <img src="docs/screenshots/search-quote.png" alt="Searching sound fonts by content" width="820">
     Best shot: a terminal running the search above, on a real card. -->

> **On the saber, this reads anything and writes only to the memory card.
> It never writes firmware.** See [SAFETY.md](SAFETY.md).

---

## Start here: things that will bite you

**Most of the value in this repository is written down, not installed.** These
need nothing but a few minutes:

| | |
|---|---|
| **[The computer cannot see the saber](docs/first-contact.md)** | One check tells you whether a driver could possibly be the problem - before you spend an evening on drivers that were never the issue. Plus the two USB ports that look equally plausible, only one of which carries data. |
| **[The driver keeps changing back](docs/driver-war.md)** | Every attempt succeeds and is silently undone a minute later. A background service from unrelated hardware is claiming your board. |
| **[SD card: mounting, power, `presets.ini`](docs/sd-card.md)** | Why replugging the cable never fixes "No Media", why a low battery unmounts the card by itself, and the file that overrides your config **and survives a reflash**. |
| **[⭐ Sound font anatomy - and why the quote player goes quiet](docs/sound-anatomy.md)** | The answer to "my saber does not play quotes", which comes up regularly and usually goes unanswered. It is not broken. There is nothing to play, for a reason you can check in thirty seconds. |
| **[Flashing firmware](docs/flashing.md)** | Deliberately not automated here. What is worth knowing, and where to go instead. |

### The short version of the one people search for

The quote player's mode toggle sits **inside** the "does this font have quote
files" branch. A font with no `quote*.wav` therefore plays Force effects
forever, no matter what the controls documentation says - pointing the blade
down does nothing, because there is no second mode to reach.

And spoken lines are frequently filed as `force.wav` rather than `quote01.wav`,
so a font can be **full of dialogue and still have an empty quote player**. On
the card behind this repository, 33 files of speech were sitting under `force`
across six presets, and 14 of 23 presets had no quote files at all.

---

## Going further: read your own card

Font authors do not document their files, so the only way to find a specific
line is to listen to a thousand of them one at a time. This part turns the card
into something you can query:

```
   SD card              transcribe.py           search.py            batch_swap.ps1
 ~1000 .wav   ──▶   Whisper large-v3   ──▶   match on text   ──▶   atomic swap
  no index          + confidence marks       → play command        + rollback
                            │                       │
                            │                       └──▶  report.py  ──▶  the whole
                            │                                              card as a
                            │                                              readable list
                            └──▶  classify.py  ──▶  "is there a voice here at all?"
                                    CLAP              (catches wordless sounds)
```

Two ways to read the result. **Search** when you know roughly what you are after.
**`report.py`** when you do not — it writes one table per font, every spoken file
with its text, so you can skim a pack you have never heard:

```
## IWVader

| File | Sec | ? | Line |
|---|---:|:-:|---|
| `quote09.wav` | 0.8 |  | Good. |
| `quote13.wav` | 7.7 |  | Impressive. Most impressive. |
| `quote15.wav` | 4.4 |  | If you only knew the power of the dark side. |
```

Doubtful transcriptions are **marked rather than dropped**. Whisper returns fluent
sentences for audio with no speech in it, so the flag means "listen to this one
before trusting it", not "this is wrong" — unusual but real speech gets marked too.

Every step reads from the card; only the last one writes to it, and it backs up
what it replaces.

### The loop

```bash
# 1. What is connected?
/saber-status

# 2. Back up before touching anything
/saber-backup

# 3. Find out what your sounds say  (this is the interesting part)
python tools/transcribe.py --source E:/ --count-only   # scale first, no model
python tools/transcribe.py --source E:/

# 4. Read the whole card as a list, or search it by content
python tools/report.py                                 # -> sound-library.md
python tools/search.py "hello there"

# 5. Change something, as a reversible batch
.\tools\batch_swap.ps1 -Batch my-batch.json            # preview
.\tools\batch_swap.ps1 -Batch my-batch.json -Apply
```

With Claude Code, the same steps are `/saber-status`, `/saber-backup`,
`/saber-library`, `/saber-find`, `/saber-swap`.

### Optional: is there a voice here at all?

Speech recognition tells you *what* was said but cannot tell you whether
anything was said - on a blade hum it invents a sentence. It is also blind to
wordless human sounds, so a laugh or a growl looks identical to a sound effect.

```bash
python tools/classify.py --source E:/ --families force,quote
```

This scores a fixed list of labels rather than generating text, so it cannot
invent an answer - uncertainty is reported as uncertainty. The two tools fail in
opposite directions, which is what makes using both worthwhile.

### Requirements

- Python 3.11+
- ~3 GB for the transcription model, downloaded on first run
- An NVIDIA GPU makes this several times faster; CPU works and is slower
- The classifier is optional and pulls in torch - see `requirements.txt`

---

## Honest scope

Built and tested on **one** saber: Proffieboard v2.2, single button,
ProffieOS 7.15, Windows.

The documentation applies broadly. The card tools should work on any Proffie
card. The PowerShell scripts and the driver procedures are **Windows-specific**.
Everything else *should* work elsewhere and has not been tested there - if you
try it, say how it went.

---

## Credit where it is due

This sits on top of other people's work:

- **[Fredrik Hubinette](https://fredrik.hubbe.net/lightsaber/)** - Proffieboard
  and ProffieOS, without which none of this exists
- **[Fett263](https://www.fett263.com/)** - the prop file, style library and
  config generator that most Proffie sabers are actually built with.
  `docs/flashing.md` points at these tools rather than competing with them
- **[NoSloppy/SoundFontNamingConverter](https://github.com/NoSloppy/SoundFontNamingConverter)**
  - converts font naming and formats between saber platforms. Different problem
  to this repository, and the right tool when that is what you need
- **[theCrucible](https://crucible.hubbe.net/)** - where the community answers
  questions properly

Models used: [Whisper](https://github.com/openai/whisper) (MIT) and
[CLAP](https://huggingface.co/laion/larger_clap_general) (Apache-2.0), both run
locally. Nothing is uploaded.

## Licence

MIT - see [LICENSE](LICENSE).

Your sound fonts are not covered by it and are not included here. `.gitignore`
keeps audio out of this repository from the first commit, because font licensing
is frequently unclear and a file committed once stays in git history forever.
