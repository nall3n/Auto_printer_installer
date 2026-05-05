#!/usr/bin/env python3
"""
Auto Printer Installer for Windows.

A Python port of Auto_printer_installer.ps1. Adds (or updates the IP of)
Windows network printers using PowerShell cmdlets under the hood.

Printer definitions can come from:
  * a JSON file   (-f printers.json)
  * a CSV  file   (-f printers.csv)
  * --add NAME:PORT_NAME:IP  (repeatable)
  * the built-in default list (used when nothing else is given)

Run as Administrator. Windows only.

Encoding note: the original PowerShell script had to be saved as ISO 8859-10
to render Swedish characters (ö, ä, å) correctly. That headache goes away
in Python: this file is UTF-8, configs are read as UTF-8, and PowerShell is
invoked with -EncodedCommand (UTF-16-LE) so the Windows code page never
gets a chance to mangle anything.
"""

from __future__ import annotations

import argparse
import base64
import csv
import ctypes
import json
import logging
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

DEFAULT_DRIVER = "Generic / Text Only"
DEFAULT_PORT_NUMBER = 9100


@dataclass
class Printer:
    name: str
    port_name: str
    ip: str


# Built-in defaults — same list as the original PowerShell array.
DEFAULT_PRINTERS: list[Printer] = [
    Printer("Bowlingbar",  "Bowlingbar",  "10.246.0.70"),
    Printer("Arkadbaren",  "Arkadbaren",  "10.246.0.71"),
    Printer("Runda Baren", "Runda_Baren", "10.246.0.72"),
    Printer("Loungebar",   "Loungebar",   "10.246.0.73"),
    Printer("Olearys kök", "Olearys_kok", "10.246.0.74"),
    Printer("Boston Kök",  "Boston_Kok",  "10.246.0.75"),
    Printer("Balkongbar",  "Balkongbar",  "10.246.0.76"),
    Printer("Förbeställt", "Forbestallt", "10.246.0.77"),
    Printer("Boston bar",  "Boston_bar",  "10.246.0.78"),
]


# ----------------------------------------------------------------------
# PowerShell helpers
# ----------------------------------------------------------------------

def _ps_quote(value: str) -> str:
    """Quote a value for safe use inside a PowerShell single-quoted string."""
    return "'" + value.replace("'", "''") + "'"


def run_powershell(command: str) -> tuple[int, str, str]:
    """Run a PowerShell command and return (exit_code, stdout, stderr).

    Uses -EncodedCommand (UTF-16-LE base64) so any Unicode in the command
    survives regardless of the system code page, and forces UTF-8 output
    so we can decode it cleanly on the Python side.
    """
    full = (
        "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
        + command
    )
    encoded = base64.b64encode(full.encode("utf-16-le")).decode("ascii")
    completed = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy", "Bypass",
            "-EncodedCommand", encoded,
        ],
        capture_output=True,
    )
    stdout = completed.stdout.decode("utf-8", errors="replace").strip()
    stderr = completed.stderr.decode("utf-8", errors="replace").strip()
    return completed.returncode, stdout, stderr


def get_existing_port_name(printer_name: str) -> str | None:
    """Return the port name of the existing printer, or None if not present."""
    cmd = (
        f"$ErrorActionPreference='SilentlyContinue'; "
        f"$p = Get-Printer -Name {_ps_quote(printer_name)}; "
        f"if ($p) {{ $p.PortName }}"
    )
    _code, out, _err = run_powershell(cmd)
    return out or None


def get_port_host_address(port_name: str) -> str | None:
    cmd = (
        f"$ErrorActionPreference='SilentlyContinue'; "
        f"$p = Get-PrinterPort -Name {_ps_quote(port_name)}; "
        f"if ($p) {{ $p.PrinterHostAddress }}"
    )
    _code, out, _err = run_powershell(cmd)
    return out or None


def add_printer_port(port_name: str, ip: str, port_number: int) -> None:
    cmd = (
        f"Add-PrinterPort -Name {_ps_quote(port_name)} "
        f"-PrinterHostAddress {_ps_quote(ip)} -PortNumber {port_number}"
    )
    code, _out, err = run_powershell(cmd)
    if code != 0:
        raise RuntimeError(f"Add-PrinterPort failed: {err}")


def remove_printer_port(port_name: str) -> None:
    cmd = f"Remove-PrinterPort -Name {_ps_quote(port_name)}"
    code, _out, err = run_powershell(cmd)
    if code != 0:
        raise RuntimeError(f"Remove-PrinterPort failed: {err}")


def set_printer_port(printer_name: str, port_name: str) -> None:
    cmd = (
        f"Set-Printer -Name {_ps_quote(printer_name)} "
        f"-PortName {_ps_quote(port_name)}"
    )
    code, _out, err = run_powershell(cmd)
    if code != 0:
        raise RuntimeError(f"Set-Printer failed: {err}")


def add_printer(printer_name: str, port_name: str, driver: str) -> None:
    cmd = (
        f"Add-Printer -DriverName {_ps_quote(driver)} "
        f"-Name {_ps_quote(printer_name)} -PortName {_ps_quote(port_name)}"
    )
    code, _out, err = run_powershell(cmd)
    if code != 0:
        raise RuntimeError(f"Add-Printer failed: {err}")


# ----------------------------------------------------------------------
# Core logic — mirrors the foreach in the PowerShell script
# ----------------------------------------------------------------------

def install_printer(printer: Printer, driver: str, port_number: int,
                    log: logging.Logger) -> None:
    log.info("Processing '%s' (%s)", printer.name, printer.ip)
    existing_port = get_existing_port_name(printer.name)

    if existing_port:
        log.info("  Printer exists on port '%s'", existing_port)
        current_ip = get_port_host_address(existing_port)
        log.debug("  current IP: %s", current_ip)
        if current_ip != printer.ip:
            log.info("  IP differs (was %s, now %s) — reconfiguring port",
                     current_ip, printer.ip)
            # Move the printer onto a placeholder port so the old TCP port
            # can be removed, then create the new port and reassign.
            set_printer_port(printer.name, "COM1:")
            remove_printer_port(existing_port)
            add_printer_port(printer.port_name, printer.ip, port_number)
            set_printer_port(printer.name, printer.port_name)
            log.info("  -> %s", printer.ip)
        else:
            log.info("  Already pointing at %s; nothing to do.", printer.ip)
    else:
        log.info("  Adding new printer")
        add_printer_port(printer.port_name, printer.ip, port_number)
        add_printer(printer.name, printer.port_name, driver)
        log.info("  Added.")


# ----------------------------------------------------------------------
# Loading printer definitions from disk
# ----------------------------------------------------------------------

REQUIRED_KEYS = ("name", "port_name", "ip")


def _printer_from_dict(d: dict) -> Printer:
    missing = [k for k in REQUIRED_KEYS if k not in d or d[k] in (None, "")]
    if missing:
        raise ValueError(f"Missing keys {missing} in entry: {d!r}")
    return Printer(name=str(d["name"]),
                   port_name=str(d["port_name"]),
                   ip=str(d["ip"]))


def load_from_json(path: Path) -> list[Printer]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("JSON file must contain a list of printer objects")
    return [_printer_from_dict(d) for d in data]


def load_from_csv(path: Path) -> list[Printer]:
    # utf-8-sig handles the BOM Excel writes when saving "CSV UTF-8".
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("CSV file appears to be empty")
        return [_printer_from_dict(row) for row in reader]


def load_from_file(path: Path) -> list[Printer]:
    suffix = path.suffix.lower()
    if suffix == ".json":
        return load_from_json(path)
    if suffix == ".csv":
        return load_from_csv(path)
    raise ValueError(
        f"Unsupported file extension '{suffix}' (use .json or .csv)"
    )


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------

def parse_inline_printers(items: list[str]) -> list[Printer]:
    out: list[Printer] = []
    for item in items:
        parts = item.split(":")
        if len(parts) != 3:
            raise ValueError(
                f"Invalid --add value '{item}'. "
                "Expected NAME:PORT_NAME:IP."
            )
        out.append(Printer(parts[0], parts[1], parts[2]))
    return out


def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Install / update Windows network printers."
    )
    parser.add_argument(
        "-f", "--file",
        type=Path,
        help="JSON or CSV file with printer definitions.",
    )
    parser.add_argument(
        "-a", "--add",
        action="append",
        default=[],
        metavar="NAME:PORT_NAME:IP",
        help="Add a single printer inline (repeatable).",
    )
    parser.add_argument(
        "--driver",
        default=DEFAULT_DRIVER,
        help=f"Printer driver (default: {DEFAULT_DRIVER!r}).",
    )
    parser.add_argument(
        "--port-number",
        type=int,
        default=DEFAULT_PORT_NUMBER,
        help=f"TCP port (default: {DEFAULT_PORT_NUMBER}).",
    )
    parser.add_argument(
        "--use-defaults",
        action="store_true",
        help="Also include the built-in default printer list.",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose logging.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )
    log = logging.getLogger("printer-installer")

    if sys.platform != "win32":
        log.error("This script must be run on Windows.")
        return 1
    if not is_admin():
        log.warning(
            "Not running as Administrator — printer cmdlets will likely fail."
        )

    # Build the list of printers to process.
    printers: list[Printer] = []
    try:
        if args.file:
            log.info("Loading printers from %s", args.file)
            printers.extend(load_from_file(args.file))
        if args.add:
            printers.extend(parse_inline_printers(args.add))
        if not printers or args.use_defaults:
            if not printers:
                log.info("No printers given — using built-in defaults.")
            else:
                log.info("Appending built-in defaults.")
            printers.extend(DEFAULT_PRINTERS)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        log.error("Failed to load printers: %s", exc)
        return 2

    failed = 0
    for p in printers:
        try:
            install_printer(p, args.driver, args.port_number, log)
        except Exception as exc:
            log.error("'%s' failed: %s", p.name, exc)
            failed += 1

    if failed:
        log.error("%d printer(s) failed.", failed)
        return 3
    log.info("All printers processed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
