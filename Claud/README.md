# Auto Printer Installer (Python)

A Python port of `Auto_printer_installer.ps1`. It installs Windows network
printers (TCP/IP, port 9100 by default) and updates the IP of an existing
printer if it has changed.

## Requirements

- Windows
- Python 3.10+ (uses `int | None` style typing — drop the `from __future__
  import annotations` line and that requirement goes away if needed)
- Run as **Administrator** (printer cmdlets need it)

The script doesn't need any third-party packages — it shells out to the
same PowerShell cmdlets the original script used (`Get-Printer`,
`Add-PrinterPort`, etc.).

## Usage

Built-in default list (same printers as the original script):

    python auto_printer_installer.py

From a JSON file:

    python auto_printer_installer.py -f printers.json

From a CSV file:

    python auto_printer_installer.py -f printers.csv

Add printers inline (repeatable):

    python auto_printer_installer.py -a "Bar1:Bar1:10.0.0.50" -a "Bar2:Bar2:10.0.0.51"

Mix file + defaults:

    python auto_printer_installer.py -f printers.json --use-defaults

Override driver or TCP port:

    python auto_printer_installer.py -f printers.json --driver "Generic / Text Only" --port-number 9100

Verbose logging:

    python auto_printer_installer.py -f printers.json -v

## File formats

### JSON

```json
[
  { "name": "Bowlingbar",  "port_name": "Bowlingbar",  "ip": "10.246.0.70" },
  { "name": "Olearys kök", "port_name": "Olearys_kok", "ip": "10.246.0.74" }
]
```

### CSV

```
name,port_name,ip
Bowlingbar,Bowlingbar,10.246.0.70
Olearys kök,Olearys_kok,10.246.0.74
```

Both files are read as UTF-8 (CSV also accepts a UTF-8 BOM, which is what
Excel writes when you choose "CSV UTF-8"). Save with UTF-8 encoding and
Swedish characters work out of the box.

## A note on encoding

The original PowerShell script had to be saved as **ISO 8859-10** so that
characters like `ö` and `ä` rendered correctly when PowerShell read the
file using the system code page.

That's no longer a concern here:

- The `.py` file is UTF-8 (Python 3's default).
- JSON and CSV configs are read as UTF-8.
- PowerShell is invoked with `-EncodedCommand` (UTF-16-LE), so the system
  code page is bypassed entirely on the way in.
- `[Console]::OutputEncoding` is forced to UTF-8 on the way out.

So you can edit any of these files in any modern editor as long as you
save them as UTF-8.

## Logic

For each printer in the list:

1. Look it up by name with `Get-Printer`.
2. **Exists?** Get the IP its current port points at.
   - If the IP matches the config: do nothing.
   - If it differs: move the printer onto `COM1:`, drop the old TCP port,
     create the new one, point the printer at it.
3. **Doesn't exist?** Create the TCP port and `Add-Printer` it.

Same flow as the PowerShell script.

## GUI version

There's also a Tkinter GUI:

    python auto_printer_installer_gui.py

…or double-click `run_gui.bat`. The window lets you:

- Type a printer manually (Name / Port name / IP) and click **Add**
  (Enter in any field also adds it).
- Click **Load from file…** to import a JSON or CSV.
- Click **Add built-in defaults** to drop in the original 9 printers.
- Click **Save list…** to export the current list as JSON or CSV.
- Select a row and press **Delete** (or click **Remove selected**) to
  drop it. Double-click a row to copy it back into the entry fields for
  editing.
- Adjust the driver name and TCP port at the top.
- Click **Install printers** — installs run on a background thread so
  the UI stays responsive, and the **Log** panel shows progress.

Tkinter ships with the standard Python Windows installer, so no extra
packages are needed. The GUI just imports from `auto_printer_installer.py`,
so both share the same logic and encoding handling.

## Files

- `auto_printer_installer.py` — the core script (CLI)
- `auto_printer_installer_gui.py` — the Tkinter GUI
- `printers.json` — example JSON config
- `printers.csv` — example CSV config
- `run.bat` — CLI launcher (Windows)
- `run_gui.bat` — GUI launcher (Windows)
