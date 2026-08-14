---
description: Change what a preset says - as one reversible batch on the card
---

Replace sounds on the card. Collect the changes into **one batch**, check
everything, then write once.

## Know which kind of change this is

| | Card | Config |
|---|---|---|
| **What** | announcements, quotes, any font sound | colours, blade styles, preset order, font assignment |
| **How** | copy a `.wav` | recompile and flash firmware |
| **Undo** | copy the file back | another flash |
| **Risk** | low | real |

This command handles the **left column only**. This toolkit does not flash
firmware - see `SAFETY.md`.

## Before writing anything

**1. The card must be mounted.** If it shows `No Media`, see `docs/sd-card.md` -
this needs a power cycle, not a cable replug.

**2. Check the battery.** `/saber-status` reports it. **Below roughly 3.4 V, do
not write.** A batch is many writes in a row, and a board that resets mid-write
can corrupt the filesystem. Say this out loud rather than proceeding quietly.

**3. Back up first** if `/saber-backup` has not been run.

## Write the batch

A batch is a JSON list - see `examples/swap-batch.example.json`:

```json
[
  {
    "id": "D1",
    "description": "why this change, in a few words",
    "source": "card:IWLuke/quote16.wav",
    "target": "L-Skywalker/font01.wav",
    "backup": true
  }
]
```

`source` may be `card:<path>` for a file already on the card, or a path on disk
for audio prepared elsewhere. Set `backup` to `false` only when the target does
not exist yet - a file the batch is adding rather than replacing.

**Record why.** In a month the reason is the only thing that separates a
deliberate choice from an accident.

## Apply it

```powershell
.\tools\batch_swap.ps1 -Batch my-batch.json            # preview - always first
.\tools\batch_swap.ps1 -Batch my-batch.json -Apply
.\tools\batch_swap.ps1 -Batch my-batch.json -Rollback  # undo
```

The script checks **every** source and target before writing **anything**. A
batch applied halfway leaves the saber in a state no document describes, so a
single missing file blocks the whole run - by design, not as an inconvenience.

## Two traps worth naming

⚠️ **Directory layout.** Fonts come in two shapes: `Font/font.wav` and
`Font/font/font.wav`. Copying one level too high **reports no error** - the file
lands somewhere ProffieOS never looks, and nothing changes. Check the real path
before writing the batch.

⚠️ **Format.** ProffieOS wants 44.1 kHz / 16-bit / mono. The script validates
this, but audio brought in from outside usually needs conversion first, and
often needs its **volume matched** - a clip pulled from a video can be far
quieter than the font around it and end up inaudible on the saber.

## Afterwards

Verify by comparing hashes of source and target - byte-identical means the right
file landed. Then refresh the library, or it will describe the old contents:

```bash
python tools/transcribe.py --source E:/ --restart
```
