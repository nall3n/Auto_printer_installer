@echo off
REM Launches the Python printer installer.
REM Adjust the path below to where you keep the script.

REM Use the JSON config that lives next to this .bat:
python "%~dp0auto_printer_installer.py" -f "%~dp0printers.json"

REM Examples (uncomment one):
REM python "%~dp0auto_printer_installer.py"                     -- built-in defaults
REM python "%~dp0auto_printer_installer.py" -f "%~dp0printers.csv"
REM python "%~dp0auto_printer_installer.py" -a "TestBar:TestBar:10.0.0.99"

pause
