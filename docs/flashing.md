# Flashing firmware - deliberately not automated here

This toolkit does not flash firmware, and the omission is a decision rather than
an unfinished feature.

## Why not

**The risk is not comparable to anything else here.** Replacing a sound on the
card leaves a `.bak` beside it and takes one command to undo. A bad firmware
write leaves someone with a saber that does not boot. It is recoverable, but it
is a different kind of afternoon.

**Better tools already exist.** [Fett263's Config Helper][helper] and
[Style Library][styles] are mature, actively maintained, and cover far more
ground than anything that could be bolted on here. Competing with them would
produce something worse that also goes stale.

So this file records what is worth knowing, and then points you at the people
who do this properly.

[helper]: https://www.fett263.com/fett263-os7-config-helper.html
[styles]: https://www.fett263.com/fett263-proffieOS7-style-library.html

## Things worth knowing before you flash

**Back up first.** Read the existing firmware to a file - see
[../.claude/commands/saber-backup.md](../.claude/commands/saber-backup.md).
Reading is safe and gives you a way back.

**Memory is a real ceiling.** A Proffieboard v2 has **256 KB** of flash, and an
elaborate config with a couple of dozen presets can use most of it. Compile
before you upload and read the reported size - the compiler tells you the
percentage used, and finding out you do not fit is far better than finding out
during the upload.

**⚠️ Options in the board menu are not the same as `#define`s.** Some behaviour
is selected when the firmware is *built*, in the board options, not in the
config file. Mass storage - the card appearing as a drive - is one of these: the
matching `#define` alone will not produce it if the build option is not set. This
is a genuinely confusing failure, because the config looks correct.

**Saved state outlives the flash.** `presets.ini` on the card is not touched by
uploading firmware, so a preset changed from the saber keeps its overridden font
or colour afterwards. See [sd-card.md](sd-card.md). If a reflash "did not take",
this is usually why.

**Entering bootloader mode rarely needs disassembly.** Opening the serial port
at 1200 baud and closing it resets the board into DFU - no buttons, no opening
the hilt.

**If `dfu-util` cannot see the board**, the driver is the problem, and possibly
something is fighting you for it - see [driver-war.md](driver-war.md).

## What can be done safely from here

Reading is always safe:

- back up the current firmware
- read the version, config name, prop file and button count with `version`
- compile a config **without uploading it**, just to learn whether it fits

That last one is genuinely useful and carries no risk at all. If it lands in
this toolkit later, it will be as *"will this fit?"* - never as *"upload it for
me."*

## Where to go

- **[ProffieOS documentation](https://pod.hubbe.net/)** - the reference
- **[ProffieOS wiki](https://github.com/profezzorn/ProffieOS/wiki)** - including
  a page on keeping edits when uploading, which pairs with the `presets.ini`
  behaviour described above
- **[theCrucible](https://crucible.hubbe.net/)** - the community forum, and the
  right place to ask when something specific goes wrong
- **[Fett263](https://www.fett263.com/)** - config and style generation, prop
  documentation, and update guides
