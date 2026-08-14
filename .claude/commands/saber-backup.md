---
description: Back up firmware and the whole SD card before changing anything
---

Make a copy of everything before the first modification. **Run this before any
other command that writes.**

This is the one step that turns every later mistake into an inconvenience
instead of a loss.

## Part 1: The SD card

The easy half, and the more valuable one - sound fonts are what make a saber
feel like a specific character, and some are hard or impossible to find again.

```powershell
$stamp = Get-Date -Format 'yyyy-MM-dd'
$dest  = "backup/sd-card-$stamp"
New-Item -ItemType Directory -Force $dest | Out-Null
Copy-Item "E:\*" $dest -Recurse -Force
```

**Then verify, do not assume.** Compare file counts and total size:

```powershell
$src = Get-ChildItem "E:\" -Recurse -File | Measure-Object -Property Length -Sum
$dst = Get-ChildItem $dest -Recurse -File | Measure-Object -Property Length -Sum
"source: $($src.Count) files, $([math]::Round($src.Sum/1GB,3)) GB"
"copy:   $($dst.Count) files, $([math]::Round($dst.Sum/1GB,3)) GB"
```

Report both numbers. If they differ, say so and stop - a partial backup that is
believed to be complete is worse than no backup.

⚠️ Cards are slow over USB. Expect several minutes for a full card, and do not
mistake slowness for a hang.

## Part 2: The firmware

Reading firmware is safe. **Writing it is out of scope for this toolkit** - see
`SAFETY.md`.

The board must be in bootloader (DFU) mode. On Proffieboard this can usually be
triggered **without opening the hilt or holding buttons**, using the "1200 bps
touch": opening the serial port at 1200 baud and closing it resets the board
into the bootloader.

```powershell
$p = New-Object System.IO.Ports.SerialPort 'COM5',1200
$p.Open(); Start-Sleep -Milliseconds 300; $p.Close()
```

The COM port disappears and a `VID_0483` device appears. Then dump it:

```
dfu-util -a 0 -s 0x8000000:0x40000 -U backup/firmware-<date>.bin
```

Record the size and a checksum next to the file. A Proffieboard v2 dump is
262144 bytes - if you get something else, note it rather than assuming it is fine.

If `dfu-util` cannot see the device, the driver is wrong - run `/saber-doctor`
step 4.

## Afterwards

Tell the user where the backup went and how big it is, and remind them that
`.gitignore` in this repository keeps backups and audio out of git on purpose -
sound font licensing is often unclear, and their card contents are theirs.

To leave bootloader mode: `dfu-util -a 0 -s 0x8000000:leave -D <the .bin>` or
simply power-cycle the saber.
