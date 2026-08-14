# The computer cannot see the saber

The most common first problem, and the one most likely to be blamed on the wrong
thing. Work through this in order.

## Start with a question you can answer definitively

Before touching drivers, find out whether *anything* is arriving:

```powershell
# saber UNPLUGGED
(Get-PnpDevice -PresentOnly).Count
# plug it in, wait three seconds
(Get-PnpDevice -PresentOnly).Count
```

**If the number does not change, this is not a driver problem.** Nothing is
reaching the computer electrically. No amount of driver work can fix that, and
people lose entire evenings there.

That is the whole value of this step: it turns "something is wrong somewhere"
into one of two specific questions.

## If nothing arrives: you are probably in the wrong port

Many sabers expose **two USB ports that look equally reasonable**:

| Port | What it usually does |
|---|---|
| **USB-C** on the hilt or chassis | **charging only** - no data lines connected |
| **micro-USB on the board** | data - serial and programming |

The board's port often sits inside the hilt and needs the chassis slid out to
reach. This produces a perfectly consistent, perfectly misleading symptom: the
saber charges, so it is clearly alive, and the computer never sees it.

⚠️ **Consequence worth knowing:** because the data port does not charge, working
over USB **drains the battery**. A long session can take a cell from full to
below its safe working voltage. Charge through the other port at the same time
if you can - they are independent.

## If nothing arrives and the port is right: the cable

A large share of micro-USB cables are power-only. Test the same cable with a
device you know does data, or simply try another cable. Cheap to rule out,
embarrassing to discover late.

## If a device appears

Check which one:

```powershell
Get-PnpDevice -PresentOnly |
    Where-Object { $_.InstanceId -match 'VID_1209|VID_0483' } |
    Select-Object Status, FriendlyName, InstanceId
```

| ID | Meaning |
|---|---|
| `VID_1209` | ProffieOS is running - you get a COM port and can talk to it |
| `VID_0483` | STM32 bootloader (DFU) - firmware can be read or written, the saber is not running |

A COM port means you are done. Open it at **115200, 8N1, DTR and RTS enabled**
and send `version`.

An unknown command answers `Whut?`. That is ProffieOS being ProffieOS, and it
is a useful sign: it means the link works.

If you see `VID_0483` but tools cannot reach it, the driver is wrong - see
[driver-war.md](driver-war.md).

## Things that are not faults

- **A COM port but no card.** These are independent. See [sd-card.md](sd-card.md).
- **The port vanishing and returning.** That is the board resetting, which is
  what a firmware upload or a 1200-baud touch is supposed to cause.
