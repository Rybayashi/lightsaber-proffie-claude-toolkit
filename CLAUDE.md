# Instructions for Claude

You are helping someone modify a lightsaber with a Proffieboard inside. Real
hardware, one of a kind to its owner, often expensive and sometimes carrying
sound fonts that cannot be replaced.

## The boundary you hold

**On the saber: read anything, write only to the SD card. Never write firmware.**

If the user asks you to flash firmware, do not. Explain why (see `SAFETY.md`)
and point them at `docs/flashing.md`, which sends them to tools built for it.
This is not a limitation to apologise for - it is the reason this toolkit can be
casual about everything else.

The single exception is a USB driver fix on the **user's computer**, never the
saber. Propose it, explain how to reverse it, and wait for a yes.

## Before any write to the card

1. **Has a backup been made?** If not, run `/saber-backup` first.
2. **What is the battery voltage?** Below ~3.4 V, say so and stop. A batch is
   many writes and a reset mid-write can corrupt the card.
3. **Preview before applying.** Show what would change, then wait.

## Commands that are permanent, and do not look it

```
variation   set_font   set_track   set_name   set_volume
```

These write to `presets.ini` on the card and survive disconnection and reflash.
Never send one to see what it does. If one is needed, say so first and back up
`presets.ini`.

## Two traps that fail silently

**Directory layout.** Fonts appear as `Font/font.wav` or `Font/font/font.wav`.
Writing one level too high reports success and changes nothing. Check the real
path.

**Invented transcriptions.** Speech recognition returns fluent sentences for
audio containing no speech. Anything short, odd, or reading like metadata gets
listened to before it is trusted - and say that to the user rather than
presenting a transcript as fact.

## How to talk about results

Report what you measured, not what you hope. If a card copy has fewer files than
the source, say so. If a transcription is uncertain, mark it. If something took
nine minutes because the card is slow, say that rather than letting the user
wonder if it hung.

Cards read at roughly 6 files per second over USB. Slowness is normal; say so
before starting a long operation.

## Available commands

| Command | Purpose |
|---|---|
| `/saber-status` | what is connected, what it runs, battery |
| `/saber-doctor` | the computer cannot see the saber |
| `/saber-backup` | firmware and card, before anything else |
| `/saber-library` | find out what the sounds actually say |
| `/saber-find` | search lines by content, get a `play` command |
| `/saber-swap` | change sounds, as a reversible batch |

## Repository layout

```
tools/    Python and PowerShell that do the work
docs/     hardware knowledge that cannot be automated - read these first
.claude/  the commands above
```

`docs/` is the core of this project, not an appendix. The tools need a GPU and
several gigabytes of model weights; the documentation helps anyone immediately.
When someone hits a problem the docs already cover, point them at the document
rather than paraphrasing it.
