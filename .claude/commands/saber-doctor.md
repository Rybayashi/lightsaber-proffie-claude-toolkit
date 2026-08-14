---
description: The computer cannot see the saber - work through it in order
---

Diagnose a saber that does not show up. Work the steps **in this order** - they
are sorted by how often each one turns out to be the answer, and each step
narrows the search rather than guessing.

## Step 1: Is anything arriving at all?

Before blaming drivers, find out whether the computer sees *any* new device.

```powershell
# with the saber UNPLUGGED
(Get-PnpDevice -PresentOnly).Count
# plug the saber in, wait 3 seconds, then again
(Get-PnpDevice -PresentOnly).Count
```

**Same number both times?** Then this is not a driver problem. Nothing is
reaching the computer electrically, so the answer is in the next two steps.
This single check saves hours of driver troubleshooting that could not have
worked.

**Number went up?** Skip to step 4.

## Step 2: Which port are you plugged into?

Many sabers expose **two USB ports that look equally plausible**:

| Port | Typical role |
|---|---|
| USB-C on the hilt or chassis | **charging only** - no data lines |
| micro-USB **on the board itself** | data - programming and serial |

The board's port is often inside the hilt and needs the chassis pulled out.
Being plugged into a charging port produces exactly the symptom in step 1:
the saber charges happily and the computer never sees it.

## Step 3: Is it a data cable?

Plenty of micro-USB cables carry power only. Test the same cable with a device
you know does data, or try another cable. This is worth ruling out before
opening anything up.

## Step 4: Driver, especially in DFU mode

If the saber appears as a COM port (`VID_1209`), you are done - it works.

If it appears as `VID_0483` (STM32 bootloader) but tools cannot reach it, the
driver is wrong. It needs **WinUSB**.

⚠️ **If the driver keeps reverting after you replace it, a background service
is fighting you.** Hardware vendors ship driver installers that claim STM32
devices in DFU mode and reinstall their own driver seconds after you change it.
This was traced once to a racing-wheel driver service - the symptom is that
every attempt appears to succeed and then silently undoes itself.

To confirm: change the driver, then re-check the device a minute later. If the
provider changed back, a service is responsible.

The fix has three parts:
1. Stop and disable the offending service
2. Install the WinUSB driver for the device
3. Verify the provider stayed changed

⚠️ **This writes to the user's computer, not to the saber.** It is outside the
"only write to the card" boundary, so **ask before doing it** and tell the user
how to reverse it - the service can be re-enabled afterwards.

See `docs/driver-war.md` for the full account.

## Step 5: Card visible but the saber is not, or vice versa

These are independent. A saber can talk over serial while refusing to present
its card - that is a normal state, not a fault. See `docs/sd-card.md`.

## Report what you ruled out

When you reach an answer, say which steps you eliminated and how. "It was the
charging port" is useful; "it works now" is not - the user will hit this again.
