---
description: Find the saber and report what it is - board, firmware, battery, card
---

Report the current state of the connected saber. **Read only** - this command
changes nothing.

## What to gather

**1. Is it there, and in which mode?**

```powershell
[System.IO.Ports.SerialPort]::GetPortNames()
Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -match 'VID_1209|VID_0483' } |
    Select-Object Status, FriendlyName, InstanceId
```

- `VID_1209` = ProffieOS running normally, talks over a COM port
- `VID_0483` = STM32 bootloader (DFU mode) - firmware can be read or written,
  but the saber is not running

If neither appears, stop here and run `/saber-doctor`.

**2. What is it running?** Open the COM port at **115200, 8N1, DTR and RTS on**,
then send these one at a time and read the replies:

| Command | Tells you |
|---|---|
| `version` | ProffieOS version, config file name, prop file, button count, build date |
| `battery` | cell voltage |
| `list_presets` | presets with their fonts and tracks |

An unknown command answers `Whut?` - that is ProffieOS, not an error.

**3. Is the card mounted?**

```powershell
Get-Disk | Where-Object FriendlyName -like '*DOSFS*' | Select-Object FriendlyName, OperationalStatus
```

`No Media` means the board is running but is not presenting the card. See
`docs/sd-card.md` - this needs a real power cycle, not a cable replug.

## Reporting the battery

A full 18650 cell reads about 4.1-4.2 V. **Below roughly 3.4 V the blade dims
and the board can reset.**

Say so plainly when the voltage is low, and add the consequence: **do not write
to the card on a low cell.** A reset in the middle of a write can corrupt the
filesystem, and card writes come in batches.

Note that on most sabers the **data port does not charge**. Working over USB
drains the cell; charging happens through a separate port.

## Never send these while "just checking"

`variation` `set_font` `set_track` `set_name` `set_volume`

They are **persistent** - written to `presets.ini` on the card, surviving
disconnection and even a firmware reflash. A single exploratory `variation`
command permanently changed a preset's colour during development of this
toolkit. If you need one of them, say so first and back up `presets.ini`.
