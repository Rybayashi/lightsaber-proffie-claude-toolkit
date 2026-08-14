# When the driver keeps changing back

A rare failure with a distinctive signature, and one that will waste a whole
evening if you have not seen it before.

## The symptom

You put the saber into bootloader mode. It shows up as `VID_0483` (STM32 DFU).
Tools like `dfu-util` cannot reach it, so you replace the driver with WinUSB.

**The change appears to succeed. A minute later the old driver is back.**

Repeat it and the same thing happens. Every attempt reports success. Nothing
sticks. It looks like the tool is broken, or the board, or Windows.

## The cause

**A background service is claiming the device and reinstalling its own driver.**

Hardware vendors ship driver installer services that watch for devices matching
certain IDs and configure them automatically. Some of these match STM32 devices
in DFU mode - which is not unreasonable, because plenty of consumer hardware has
an STM32 inside.

The case that produced this document was a **racing-wheel driver installer
service**. It had no connection to lightsabers whatsoever; it simply saw an
STM32 in DFU mode and helpfully took ownership of it, seconds after every manual
change.

## How to confirm it

Change the driver, wait a minute, then look at the device again and check the
**driver provider**:

```powershell
Get-PnpDevice -PresentOnly | Where-Object InstanceId -match 'VID_0483' |
    Get-PnpDeviceProperty -KeyName 'DEVPKEY_Device_DriverProvider'
```

If the provider reverted to a hardware vendor's name, a service is responsible.

To find candidates, look at running services from hardware vendors whose devices
you own - the name usually contains the vendor, and installer services often
have `install` in the name.

## The fix

Three steps, in order:

1. **Stop and disable the service** that is claiming the device
2. **Install the WinUSB driver** for it
3. **Verify the provider stayed changed** - wait a minute and re-check

Skipping step 3 is how people conclude the fix did not work when it did, or the
reverse.

## Reversing it

⚠️ **This changes the user's computer, not the saber.** It sits outside the
"only write to the card" boundary this toolkit otherwise holds to, so it needs
explicit consent and a way back.

Re-enabling the service restores the original behaviour. Note the service name
and its original startup type **before** changing anything, so it can be put
back exactly as it was.

⚠️ **It can come back.** Reinstalling or updating the vendor's software may
re-enable the service, and the symptom returns identically. If a saber that used
to flash fine suddenly stops, check this first rather than last.

## Why this is documented at all

Nothing here is specific to sabers, which is exactly why it is hard to find:
searching for saber-related terms will not turn it up, and the symptom looks
like a broken tool rather than a conflict. Knowing the shape of it - *"success,
then silently undone"* - is most of the fix.
