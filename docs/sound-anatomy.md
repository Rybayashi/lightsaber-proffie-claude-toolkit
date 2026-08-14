# How a sound font is organised, and why the quote player goes quiet

The most useful document here. It explains a symptom that comes up regularly and
usually goes unanswered: **"my saber does not play quotes."**

## Two layouts, both valid

Fonts ship in one of two shapes, and tools have to handle both:

```
flat:        MyFont/font.wav      MyFont/quote01.wav    MyFont/clsh01.wav
directory:   MyFont/font/font.wav MyFont/quote/quote01.wav
```

⚠️ **This breaks naive tooling in a way that produces no error.** If you take a
file's parent directory as the font name, the flat layout gives `MyFont` and the
directory layout gives `font`, `quote` or `clsh`.

Building a library that way files entries under fonts that do not exist and
makes real fonts vanish entirely - and nothing looks wrong, because the output
is well-formed. The correct rule is: **the font name is the first directory
under the card root**, never the file's parent.

⚠️ **The same trap when copying files.** Writing to `MyFont/font.wav` on a font
that uses the directory layout **reports success** and changes nothing, because
ProffieOS reads `MyFont/font/font.wav`. Always check the real path first.

## Families

The part of a filename before its trailing digits is its **family**, and the
family decides what triggers it:

| Family | Plays when |
|---|---|
| `hum` | the blade is on - loops continuously |
| `out` / `in` | ignition / retraction |
| `swng`, `swingl`, `swingh` | swings |
| `clsh` | blade clash |
| `blst` | blaster deflection |
| `lock` / `endlock` | blade lock |
| `stab` | thrust |
| `boot` | boot-up |
| `font` | **the preset announcing itself** on switch |
| `force` | Force gesture |
| `quote` | the quote player |

In the directory layout the **directory** decides, not the filename - files
there are often named with bare digits (`force/0001.wav`).

## ⭐ Why the quote player is silent

The quote player in the widely used Fett263 prop has a structure worth
understanding, because it explains the symptom completely:

```cpp
void CheckQuote() {
  if (SFX_quote) {                    // does this font have quote files?
    if (blade is pointing down) force_quote_ = !force_quote_;   // toggle mode
    ForceQuote();
  } else {
    SaberBase::DoForce();             // no quotes -> always a Force effect
  }
}
```

**The mode toggle lives inside the "this font has quotes" branch.**

So on a font with no `quote*.wav` files, pointing the blade down and holding
**does nothing at all**. There is no mode to switch into. Every attempt plays a
`force` sound instead - and if that font's Force sounds are effects rather than
speech, what you hear is a noise where you expected a line.

**Nothing is broken. There is simply nothing to play.**

## Two more ways to get silence, before the font is even to blame

An empty quote player is the cause people never find. These two are the causes
they find and misread, because both look exactly like "the gesture does not
work". All three can hide behind the same symptom at once.

### The gesture is not the same with the blade on and off

In the Fett263 prop the quote player is reached by **different controls
depending on blade state**:

| Blade | Control that reaches the quote player |
|---|---|
| **Off** | triple click (`EVENT_THIRD_SAVED_CLICK_SHORT`, `MODE_OFF`) |
| **On** | **long click** (`EVENT_CLICK_LONG`, `MODE_ON`) |

Triple-clicking with the blade **on** does not reach the quote player at all -
it calls `DoInteractiveBlast()`. You get a blaster deflection, or on some styles
nothing audible, and it reads as "the quote gesture is broken".

Worth knowing while testing: with the blade on, the same long click splits on
blade angle. Pointing **up** past 60° starts or stops the track player instead:

```cpp
case EVENTID(BUTTON_POWER, EVENT_CLICK_LONG, MODE_ON):
  if (fusor.angle1() > M_PI / 3) {   // blade up -> track player
    ...
  } else {
    CheckQuote();                    // otherwise -> quote player
  }
```

### The mode toggle needs a steeper angle than people assume

Look again at where the toggle sits:

```cpp
if (fusor.angle1() < - M_PI / 3)  {   // more than 60 degrees below horizontal
  force_quote_ = !force_quote_;        // only here does the mode flip
}
ForceQuote();                          // this just plays whatever mode is current
```

The gesture **plays** the current mode every time. It **switches** mode only if
the blade is more than **60° below horizontal at that moment** - which is
steeper than "angled towards the floor" and easy to under-do while sitting at a
desk with the saber in one hand.

So a font that does have quotes will still answer with a Force effect
indefinitely, simply because the mode never flipped.

One detail that compounds this: `force_quote_` is a **single flag for the whole
saber**, not per preset. Once flipped it stays flipped as you change fonts, so
the same gesture can behave differently on two presets tested minutes apart.

### Telling the three apart

| What you hear | Most likely cause |
|---|---|
| A Force effect, on every preset, whatever you do | mode never toggled - blade not steep enough |
| A Force effect on **some** presets, quotes on others | the fonts that stay silent have no `quote*.wav` |
| A blaster deflection, or nothing | triple click with the blade **on** - wrong control for that state |

## The reason this is easy to miss: speech filed as `force`

Font authors do not agree on where spoken lines belong. Many packs ship quotes
named `force.wav`, `force2.wav` and so on - this is common enough that the
ProffieOS author has described it as normal practice for at least one well-known
pack.

The consequence: **a font can be full of dialogue and still have an empty quote
player**, because every line is filed under a name the quote player never looks
at.

On the card that produced this document, **33 files of speech were sitting under
`force`** across six presets - one font alone had fourteen - while **14 of 23
presets had no quote files at all**.

⚠️ Counting these correctly takes care. A first pass reported far more, because
it trusted a transcription whenever the family name suggested speech - and that
swept in hallucinations like `"Thanks for watching!"` returned for a silent
Force effect. Check the confidence score, not just the presence of text.

## What to do about it

**Diagnose first.** For each preset's font, count files in each family. A font
with zero `quote*.wav` will never respond to the quote control, no matter what
the controls documentation says.

**Then decide what belongs where.** This is a judgement call, not a rule:

- **Spoken lines** - anything with words - belong in `quote`
- **Wordless vocal sounds** - a laugh, a growl, a shout with no words - are
  worth putting in `quote` too, since they are the character making a sound
  rather than the blade doing something
- **Sound effects** stay in `force`

⚠️ **Copy, do not rename.** Leaving the original `force` file in place keeps the
Force gesture working. There is no cost to having a sound in both places.

⚠️ **Keep numbering contiguous.** ProffieOS decides how many files exist by
looking at the range it finds, so a gap can silence everything after it. Number
`quote01`, `quote02`, `quote03` with nothing skipped.

## Finding out what the files actually say

None of the above tells you the **content**. For that, see
[../.claude/commands/saber-library.md](../.claude/commands/saber-library.md) -
transcribing the card turns a thousand opaque filenames into something you can
search by what is said.

Worth knowing before you start: it is common for a preset's announcement to be a
**duplicate of one of its own quotes**. Authors copy a line into the announcement
slot and leave the original in place, so the saber introduces itself with a
sentence it will say again later. On the card behind this document, **seven
presets did this** - invisible until every file had been transcribed.
