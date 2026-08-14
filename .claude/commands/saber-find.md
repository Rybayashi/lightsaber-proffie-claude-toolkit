---
description: Find a line by what it says, then play it on the saber
---

Search the transcribed library by content and hand back something the user can
run immediately.

```bash
python tools/search.py "i am your father"
python tools/search.py "jedi" --font IWLuke --max-seconds 3
```

Requires a library built by `/saber-library`.

## Never pick a file by its name or its length

This is the mistake the whole library exists to prevent.

`"Hello there."` lives in `quote21.wav` and runs **0.6 seconds** - a file that
looks far too short to hold a sentence, and was dismissed as exactly that during
development before transcription proved otherwise. Filenames are indexes, not
descriptions, and length tells you nothing about content.

## Playing it

Search output includes a ready `play` command:

```
play IWVader/quote17.wav
```

Send it over the serial port. ProffieOS looks inside the **active font** first
and then from the card root, so the font prefix is what lets a preset play a
line belonging to a different character.

`play` is safe - it changes nothing.

## Choosing well

When helping pick a line, weigh these:

**Length.** An announcement that runs five seconds delays every preset switch by
five seconds, forever. Shorter is usually better; `search.py` sorts shortest
first for this reason.

**Uniqueness.** Check whether the phrase already appears elsewhere in the font.
A line used as both the announcement and a Force quote makes the saber repeat
itself, and this is common - font authors copy a quote into the announcement
slot and leave the original in place.

**Confidence.** Anything flagged `[?]` needs listening to first. The text may
be invented.

## What comes next

Changing what a preset says is a card operation - no recompiling, no firmware
flash, and reversible. See `/saber-swap`.
