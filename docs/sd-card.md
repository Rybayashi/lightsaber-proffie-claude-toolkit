# The SD card: mounting, power, and the file that overrides your config

Three things about the card that are not obvious and cost real time.

## "No Media" - and why replugging does not help

```powershell
Get-Disk | Where-Object FriendlyName -like '*DOSFS*'
```

`OperationalStatus: No Media` means the board is running but is not presenting
the card to the computer.

This happens after the card is ejected from the host side, or when ProffieOS
takes the card for itself. Once in that state, ProffieOS remembers that the host
ejected the media and does not offer it again.

⚠️ **Unplugging and replugging the USB cable does not fix it.** The board is
powered by the **battery**, so the cable coming and going changes nothing about
its state. It never restarts, so it never reconsiders.

⚠️ **Pressing the power button usually does not fix it either.** On most sabers
that button controls the *blade*, not the board. The board keeps running.

**The proof of which happened:** if the board really restarted, the **COM port
disappears and comes back**. If the COM port stayed put the whole time, nothing
was power-cycled.

**What actually works:** a real power cycle - the hilt's kill switch if it has
one, or removing and reinserting the cell.

## Low battery unmounts the card by itself

If the board is short of power it sheds load, and the card is one of the first
things to go. You will see messages like:

```
Unmounting SD Card.
Amplifier off.
```

Check the voltage with the `battery` command over serial. A full 18650 reads
about 4.1-4.2 V. **Below roughly 3.4 V the blade dims and the board can reset.**

⚠️ **Never write to the card on a low cell.** Card changes come in batches -
many writes in a row - and a board that resets partway through can leave the
filesystem damaged. Reading is fine; writing is not worth the risk.

⚠️ Remember that on most sabers **the data port does not charge**. A long
session over USB drains the cell rather than topping it up.

## `presets.ini` silently overrides your config

This one causes a specific, baffling symptom: **a preset plays the wrong font**,
and the config file clearly says otherwise.

ProffieOS stores runtime state on the card in `presets.ini`. When something
changes a preset from the saber itself - the Edit Mode menu, or a serial command
like `set_font` - the new value is written there.

**That file wins over the config, and it survives a firmware reflash.** So you
can rebuild and re-upload firmware, watch it succeed, and get the old behaviour
back, because the override was never in the firmware to begin with.

**How to spot it:** in `list_presets`, an overridden font often carries a suffix
such as `;common`. That is the sign that the value came from saved state rather
than the config.

**Two ways out:**

- set it deliberately from the saber: `set_preset <n>` then `set_font <FontName>`
  (this writes to `presets.ini` too, but now with the value you want)
- delete `presets.ini` with the saber powered off - ProffieOS rebuilds it from
  the config on next boot

⚠️ Deleting it discards **all** saved state, including volume and any colours
tuned on the saber. Back it up first.

## Commands that write permanently

These look like ordinary serial commands and are not:

```
variation   set_font   set_track   set_name   set_volume
```

Every one of them writes to `presets.ini` and outlives disconnection. During
development of this toolkit, a single exploratory `variation` sent to see what
it did **permanently changed a preset's colour**, and it took a while to work
out why the saber no longer matched its own config.

Before experimenting, read the current state with `show_current_preset` so you
can put it back.

## Cards are slow

Measured over USB mass storage: roughly **6 files per second** when reading
headers. A card with 3000 files is therefore several minutes of pure I/O before
any processing begins.

**Do not mistake slowness for a hang.** If you can, copy the card to local disk
first and work against the copy - it is several times faster and takes load off
a saber that may be running on battery.
