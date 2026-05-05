@echo off
REM Launches the GUI version of the printer installer.
REM pythonw.exe runs without a console window. If you'd rather see stdout
REM (for debugging), swap pythonw -> python.

start "" pythonw "%~dp0auto_printer_installer_gui.py"
