<#
.SYNOPSIS
    Swap sound files on a saber's SD card as one atomic batch.

.DESCRIPTION
    Reads a batch definition from JSON and applies it to the card. Sound changes
    live on the card, so they need no recompiling and no firmware flash -- and
    every one of them is reversible.

    THE ORDER IS THE POINT: this script checks every source and every target
    BEFORE it writes anything. A batch applied halfway is worse than a batch not
    applied at all, because it leaves the saber in a state no document describes.

    ENCODING: this file is deliberately plain ASCII. PowerShell 5.1 reads files
    without a BOM as ANSI and breaks on non-ASCII characters inside strings.

.PARAMETER Card
    Drive or directory of the SD card. Default E:.

.PARAMETER Batch
    Path to the batch definition JSON. See examples/swap-batch.example.json.

.PARAMETER Apply
    Without this switch nothing is written -- the script only reports what it
    would do. Writing requires asking for it.

.PARAMETER Rollback
    Restore originals from their .bak copies and delete files the batch added.

.EXAMPLE
    .\tools\batch_swap.ps1 -Batch my-batch.json
    Preview. Always start here.

.EXAMPLE
    .\tools\batch_swap.ps1 -Batch my-batch.json -Apply

.NOTES
    If the card is not visible, see docs/sd-card.md. The card only mounts while
    the saber is powered on and connected through its DATA port -- and after an
    eject it needs a real power cycle, not just a cable replug.
#>

[CmdletBinding()]
param(
    [string]$Card = "E:",
    [Parameter(Mandatory = $true)][string]$Batch,
    [switch]$Apply,
    [switch]$Rollback
)

$ErrorActionPreference = "Stop"
$CardRoot = $Card.TrimEnd('\')

function Test-WavFormat {
    # ProffieOS wants 44.1 kHz / 16-bit / mono.
    #
    # The 'fmt ' chunk is NOT always at offset 12. Some files carry a 'JUNK'
    # chunk before it, which pushes 'fmt ' further in. Reading fixed offsets
    # 22/24/34 then lands inside the JUNK block and reports nonsense such as
    # "0 Hz / 3 channels". So walk the chunk list instead of assuming a
    # canonical 44-byte header.
    param([string]$Path)
    try {
        $bytes = [System.IO.File]::ReadAllBytes($Path)
        if ($bytes.Length -lt 44) { return "shorter than a WAV header" }
        if ([System.Text.Encoding]::ASCII.GetString($bytes, 0, 4) -ne "RIFF") { return "not a WAV file" }
        if ([System.Text.Encoding]::ASCII.GetString($bytes, 8, 4) -ne "WAVE") { return "RIFF but not WAVE" }

        $pos = 12
        while ($pos + 8 -le $bytes.Length) {
            $id = [System.Text.Encoding]::ASCII.GetString($bytes, $pos, 4)
            $size = [BitConverter]::ToUInt32($bytes, $pos + 4)
            if ($id -eq "fmt ") {
                $d = $pos + 8
                if ($d + 16 -gt $bytes.Length) { return "'fmt ' chunk truncated" }
                $channels = [BitConverter]::ToUInt16($bytes, $d + 2)
                $rate = [BitConverter]::ToUInt32($bytes, $d + 4)
                $bits = [BitConverter]::ToUInt16($bytes, $d + 14)
                if ($rate -ne 44100 -or $channels -ne 1 -or $bits -ne 16) {
                    return "$rate Hz / $channels ch / $bits bit (expected 44100/1/16)"
                }
                return $null
            }
            $pos = $pos + 8 + $size + ($size % 2)   # chunks are word-aligned
        }
        return "no 'fmt ' chunk found"
    } catch {
        return "unreadable: $($_.Exception.Message)"
    }
}

function Resolve-Source {
    param([string]$Source)
    if ([System.IO.Path]::IsPathRooted($Source)) { return $Source }
    if ($Source -like "card:*") { return Join-Path $CardRoot $Source.Substring(5) }
    return $Source   # relative to the current directory
}

# --- load the batch ----------------------------------------------------------
if (-not (Test-Path $Batch)) {
    Write-Host "ERROR: no batch file at $Batch" -ForegroundColor Red
    exit 1
}
$operations = Get-Content $Batch -Raw | ConvertFrom-Json
if (-not $operations) {
    Write-Host "ERROR: batch file is empty" -ForegroundColor Red
    exit 1
}

# --- card --------------------------------------------------------------------
Write-Host ""
if (-not (Test-Path "$CardRoot\")) {
    Write-Host "ERROR: cannot see the card at $CardRoot\" -ForegroundColor Red
    Write-Host ""
    Write-Host "  The card mounts only while the saber is on and connected through its"
    Write-Host "  DATA port. After an eject it needs a real power cycle -- replugging the"
    Write-Host "  cable is not enough, because the board runs on its own battery."
    Write-Host "  See docs/sd-card.md."
    exit 1
}

# --- rollback ----------------------------------------------------------------
if ($Rollback) {
    Write-Host "=== ROLLBACK ===" -ForegroundColor Yellow
    $undone = 0
    foreach ($op in $operations) {
        $target = Join-Path $CardRoot $op.target
        $backup = "$target.bak"
        if ($op.backup) {
            if (Test-Path $backup) {
                Copy-Item $backup $target -Force
                Remove-Item $backup -Force
                Write-Host "  restored  $($op.id)  $($op.target)"
                $undone++
            }
        } elseif (Test-Path $target) {
            Remove-Item $target -Force
            Write-Host "  removed   $($op.id)  $($op.target)  (added by this batch)"
            $undone++
        }
    }
    Write-Host ""
    Write-Host "Rolled back $undone operations." -ForegroundColor Green
    exit 0
}

# --- verification, always ----------------------------------------------------
$mode = "preview only"
if ($Apply) { $mode = "APPLY" }

Write-Host "=== CHECKING ===" -ForegroundColor Cyan
Write-Host "Card: $CardRoot   Operations: $($operations.Count)   Mode: $mode"
Write-Host ""

$errors = @()
$warnings = @()

foreach ($op in $operations) {
    $source = Resolve-Source $op.source
    $target = Join-Path $CardRoot $op.target
    $backup = "$target.bak"
    $notes = @()

    if (-not (Test-Path $source)) {
        $errors += "$($op.id): missing source  $source"
        $notes += "NO SOURCE"
    } else {
        $formatProblem = Test-WavFormat $source
        if ($formatProblem) {
            $errors += "$($op.id): source format - $formatProblem"
            $notes += "FORMAT"
        }
    }

    if ($op.backup -and -not (Test-Path $target)) {
        $errors += "$($op.id): no target file to replace  $target"
        $notes += "NO TARGET"
    }

    # An existing .bak means this batch already ran once. Backing up again would
    # capture the ALREADY MODIFIED file and destroy the only copy of the original.
    if (Test-Path $backup) {
        $warnings += "$($op.id): backup already exists - it will be KEPT, not overwritten"
        $notes += "bak exists"
    }

    $status = "ok  "
    if ($notes -contains "NO SOURCE" -or $notes -contains "FORMAT" -or $notes -contains "NO TARGET") {
        $status = "FAIL"
    }
    $colour = "Gray"
    if ($status -eq "FAIL") { $colour = "Red" }

    Write-Host ("  [{0}] {1,-6} {2}" -f $status, $op.id, $op.description) -ForegroundColor $colour
    if ($notes.Count -gt 0) {
        Write-Host ("         {0}" -f ($notes -join ", ")) -ForegroundColor DarkYellow
    }
}

Write-Host ""
foreach ($w in $warnings) { Write-Host "  NOTE: $w" -ForegroundColor Yellow }

if ($errors.Count -gt 0) {
    Write-Host ""
    Write-Host "CHECK FAILED - $($errors.Count) problem(s). Nothing was written." -ForegroundColor Red
    foreach ($e in $errors) { Write-Host "  - $e" -ForegroundColor Red }
    exit 1
}

Write-Host "Check passed - every source and target is in place." -ForegroundColor Green

if (-not $Apply) {
    Write-Host ""
    Write-Host "That was a preview. To apply:" -ForegroundColor Cyan
    Write-Host "  .\tools\batch_swap.ps1 -Batch $Batch -Apply"
    exit 0
}

# --- apply -------------------------------------------------------------------
Write-Host ""
Write-Host "=== APPLYING ===" -ForegroundColor Cyan

$done = 0
foreach ($op in $operations) {
    $source = Resolve-Source $op.source
    $target = Join-Path $CardRoot $op.target
    $backup = "$target.bak"

    if ($op.backup -and -not (Test-Path $backup)) {
        Copy-Item $target $backup
    }
    Copy-Item $source $target -Force
    Write-Host "  $($op.id.PadRight(6))  ->  $($op.target)" -ForegroundColor Green
    $done++
}

Write-Host ""
Write-Host "Applied $done operations." -ForegroundColor Green
Write-Host ""
Write-Host "NEXT:" -ForegroundColor Cyan
Write-Host "  1. Listen to the presets you changed."
Write-Host "  2. Refresh your library:  python tools/transcribe.py --source `"$CardRoot/`" --restart"
Write-Host ""
Write-Host "  Undo:  .\tools\batch_swap.ps1 -Batch $Batch -Rollback" -ForegroundColor DarkGray
