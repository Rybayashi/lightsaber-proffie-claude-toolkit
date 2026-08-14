---
description: Find out what every sound on your card actually says
---

Build a searchable library of the spoken lines on the card. This is the point
where the user stops guessing what their saber can say.

## Why this exists

A card holds roughly a thousand files named `quote17.wav`, `force03.wav` and so
on. Font authors do not document them. The only alternative is listening to
files one at a time, which nobody finishes.

## Run it

```bash
# See the scale first - this loads no model and takes seconds
python tools/transcribe.py --source E:/ --count-only

# Then the real run
python tools/transcribe.py --source E:/
```

The model (~3 GB) downloads on first use. Results are written incrementally, so
an interrupted run resumes.

⚠️ **Reading from the card is slow** - measured at roughly 6 files per second
over USB. A thousand files is therefore several minutes of I/O before the model
even becomes the bottleneck. Tell the user the estimate up front and do not
mistake slowness for a hang.

⚠️ **Copy the card to disk first if you can** (see `/saber-backup`) and run
against the copy. It is several times faster and takes load off a saber that may
be running on battery.

## Read the results honestly

Report the shape of what came back: how many files, how many contain speech,
how many fonts.

**Then say clearly that some transcriptions are invented.** Speech recognition
does not return "nothing here" for a blade hum - it returns a fluent sentence.
Real examples from this toolkit's development:

- a silent file transcribed as trailing subtitle credits
- a four-minute fight scene that produced `"I don't know."` every 30 seconds,
  matching the music rather than any dialogue

Entries carry `no_speech_prob`. Anything above ~0.3, anything very short, and
anything that reads like metadata should be listened to before it is trusted.

## Optional: is there a voice here at all?

Whisper answers *what was said*. It cannot answer *was anything said* - and it
is blind to wordless human sounds: a laugh, a grunt, a roar carry no words, so
it returns nothing and they look identical to sound effects.

```bash
python tools/classify.py --source E:/ --families force,quote
```

This scores each file against a fixed list of labels, so it cannot invent an
answer - uncertainty shows up as a narrow margin and is reported as uncertain
rather than guessed.

**The two disagree in opposite directions, and that is useful.** Whisper is
precise on words and blind to wordless voice; the classifier catches wordless
voice and sometimes misses clear speech. When Whisper returns a coherent full
sentence with low `no_speech_prob`, trust Whisper. When Whisper returns nothing
but the classifier says voice, it is probably a laugh or a growl.

Files where both are unsure are the ones worth the user's ears.

## Then

```bash
python tools/search.py "some phrase"
```
