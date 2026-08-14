# Safety boundary

> **On the saber, this toolkit reads anything and writes only to the memory card.
> It never writes firmware.**

That sentence defines the whole project. Everything below explains it.

## Why the line is drawn there

The risk is not symmetrical.

The worst outcome of a card operation is a preset that sounds wrong, with a
`.bak` copy sitting next to it and one command to undo. The worst outcome of a
firmware mistake is someone's saber not booting.

Those deserve different levels of caution, and blending them into one tool would
mean treating the safe thing with the ceremony of the dangerous one, or - far
worse - the reverse.

## What this toolkit does

**Reads, always safe:**

- detects the saber, its board, firmware version, button count, battery
- reads firmware to a backup file
- copies the whole SD card
- transcribes and classifies the sounds on the card

**Writes to the SD card, reversible:**

- replaces sound files, in checked batches, keeping a `.bak` of every original

**Never:**

- writes, uploads or modifies firmware
- deletes anything without a backup
- sends audio or card contents anywhere - transcription runs locally on your
  machine

## The one exception, and it is not the saber

`/saber-doctor` may install a **USB driver on your computer** when the bootloader
device has the wrong one, and may disable a background service that keeps
reverting it (see [docs/driver-war.md](docs/driver-war.md)).

That is a change to **your machine, not your saber**. It sits outside the rule
above, which is exactly why it is called out here rather than buried. It will
always be proposed before it happens, and it is reversible - re-enabling the
service restores the original behaviour.

## Rules the batch tool follows

These exist because each one prevents a specific way of losing work:

**A batch is all-or-nothing.** Every source and target is checked before
anything is written. One missing file blocks the whole run - a batch applied
halfway leaves the saber in a state no document describes.

**An existing `.bak` is never overwritten.** Running the same batch twice would
otherwise back up the *already modified* file and destroy the only copy of the
original.

**Preview is the default.** Writing requires asking for it explicitly.

## Two things to check before writing to the card

**Battery.** Below roughly 3.4 V the board can reset. A batch is many writes in
a row, and a reset partway through can damage the filesystem. Read the voltage
first - `/saber-status` reports it.

**Backup.** Run `/saber-backup` before the first change. Sound fonts are often
hard to find again.

## Your card contents stay yours

`.gitignore` excludes `*.wav`, generated libraries and firmware dumps from the
first commit onwards. Sound font licensing is frequently unclear, and a file
committed once stays in git history forever.

These tools work on your card, in place. Nothing is uploaded and nothing is
redistributed.
