#!/usr/bin/env python3
"""
Tkinter GUI for the auto printer installer.

Wraps auto_printer_installer.py with:
  * Manual entry of printer rows
  * Load / save JSON or CSV files
  * A live install log
  * Driver / TCP port controls

Run as Administrator (printer cmdlets require it). Windows only.
"""

from __future__ import annotations

import csv as csv_module
import json
import logging
import queue
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

# Re-use everything from the CLI script
from auto_printer_installer import (
    DEFAULT_DRIVER,
    DEFAULT_PORT_NUMBER,
    DEFAULT_PRINTERS,
    Printer,
    install_printer,
    is_admin,
    load_from_file,
)


# ----------------------------------------------------------------------
# Bridge logging records onto the Tk main thread via a queue
# ----------------------------------------------------------------------
class QueueLogHandler(logging.Handler):
    def __init__(self, q: queue.Queue):
        super().__init__()
        self.q = q

    def emit(self, record):
        try:
            self.q.put(self.format(record))
        except Exception:
            self.handleError(record)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Auto Printer Installer")
        self.geometry("780x700")
        self.minsize(680, 560)

        # Logging -> queue -> Text widget
        self.log_queue: queue.Queue[str] = queue.Queue()
        self.log = logging.getLogger("printer-installer")
        self.log.setLevel(logging.INFO)
        for h in list(self.log.handlers):
            self.log.removeHandler(h)
        handler = QueueLogHandler(self.log_queue)
        handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        self.log.addHandler(handler)

        self._build_ui()
        self.after(100, self._drain_log_queue)

        if sys.platform == "win32" and not is_admin():
            messagebox.showwarning(
                "Not running as Administrator",
                "Printer cmdlets require Administrator rights. Re-launch the "
                "tool from an elevated shell or shortcut, or installs will "
                "fail."
            )

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self):
        pad = {"padx": 8, "pady": 4}

        # ---- Settings ----
        settings = ttk.LabelFrame(self, text="Settings")
        settings.pack(fill="x", **pad)

        ttk.Label(settings, text="Driver:").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        self.driver_var = tk.StringVar(value=DEFAULT_DRIVER)
        ttk.Entry(settings, textvariable=self.driver_var, width=40).grid(
            row=0, column=1, sticky="ew", padx=4, pady=4
        )
        ttk.Label(settings, text="TCP port:").grid(row=0, column=2, sticky="w", padx=4, pady=4)
        self.port_var = tk.StringVar(value=str(DEFAULT_PORT_NUMBER))
        ttk.Entry(settings, textvariable=self.port_var, width=8).grid(
            row=0, column=3, sticky="w", padx=4, pady=4
        )
        settings.columnconfigure(1, weight=1)

        # ---- Manual entry ----
        manual = ttk.LabelFrame(self, text="Add a printer manually")
        manual.pack(fill="x", **pad)

        ttk.Label(manual, text="Name:").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        self.name_var = tk.StringVar()
        name_entry = ttk.Entry(manual, textvariable=self.name_var, width=22)
        name_entry.grid(row=0, column=1, sticky="ew", padx=4, pady=4)

        ttk.Label(manual, text="Port name:").grid(row=0, column=2, sticky="w", padx=4, pady=4)
        self.port_name_var = tk.StringVar()
        pn_entry = ttk.Entry(manual, textvariable=self.port_name_var, width=20)
        pn_entry.grid(row=0, column=3, sticky="ew", padx=4, pady=4)

        ttk.Label(manual, text="IP:").grid(row=0, column=4, sticky="w", padx=4, pady=4)
        self.ip_var = tk.StringVar()
        ip_entry = ttk.Entry(manual, textvariable=self.ip_var, width=16)
        ip_entry.grid(row=0, column=5, sticky="ew", padx=4, pady=4)

        ttk.Button(manual, text="Add", command=self._on_add_manual).grid(
            row=0, column=6, padx=4, pady=4
        )
        manual.columnconfigure(1, weight=1)
        manual.columnconfigure(3, weight=1)
        manual.columnconfigure(5, weight=1)

        # Pressing Enter in any of the three fields adds the printer
        for entry in (name_entry, pn_entry, ip_entry):
            entry.bind("<Return>", lambda _e: self._on_add_manual())

        # ---- File operations ----
        fileops = ttk.Frame(self)
        fileops.pack(fill="x", **pad)
        ttk.Button(fileops, text="Load from file…", command=self._on_load_file).pack(
            side="left", padx=4
        )
        ttk.Button(fileops, text="Add built-in defaults", command=self._on_add_defaults).pack(
            side="left", padx=4
        )
        ttk.Button(fileops, text="Save list…", command=self._on_save_file).pack(
            side="left", padx=4
        )

        # ---- Printer list ----
        list_frame = ttk.LabelFrame(self, text="Printers to install")
        list_frame.pack(fill="both", expand=True, **pad)

        cols = ("name", "port_name", "ip")
        self.tree = ttk.Treeview(list_frame, columns=cols, show="headings", height=8)
        self.tree.heading("name", text="Name")
        self.tree.heading("port_name", text="Port name")
        self.tree.heading("ip", text="IP")
        self.tree.column("name", width=220)
        self.tree.column("port_name", width=200)
        self.tree.column("ip", width=140)

        scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(4, 0), pady=4)
        scroll.pack(side="right", fill="y", padx=(0, 4), pady=4)

        # Delete key removes selected; double-click pre-fills the manual entry
        self.tree.bind("<Delete>", lambda _e: self._on_remove_selected())
        self.tree.bind("<Double-1>", self._on_tree_double_click)

        list_actions = ttk.Frame(self)
        list_actions.pack(fill="x", **pad)
        ttk.Button(list_actions, text="Remove selected", command=self._on_remove_selected).pack(
            side="left", padx=4
        )
        ttk.Button(list_actions, text="Clear all", command=self._on_clear).pack(
            side="left", padx=4
        )
        self.count_var = tk.StringVar(value="0 printers")
        ttk.Label(list_actions, textvariable=self.count_var).pack(side="right", padx=4)

        # ---- Install button ----
        action = ttk.Frame(self)
        action.pack(fill="x", **pad)
        self.install_btn = ttk.Button(action, text="Install printers", command=self._on_install)
        self.install_btn.pack(side="right", padx=4)

        # ---- Log ----
        log_frame = ttk.LabelFrame(self, text="Log")
        log_frame.pack(fill="both", expand=True, **pad)
        self.log_text = tk.Text(log_frame, height=10, wrap="none", state="disabled")
        log_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        self.log_text.pack(side="left", fill="both", expand=True, padx=(4, 0), pady=4)
        log_scroll.pack(side="right", fill="y", padx=(0, 4), pady=4)

    # ------------------------------------------------------------------
    # List helpers
    # ------------------------------------------------------------------
    def _printers_in_list(self) -> list[Printer]:
        out: list[Printer] = []
        for iid in self.tree.get_children():
            vals = self.tree.item(iid, "values")
            out.append(Printer(vals[0], vals[1], vals[2]))
        return out

    def _add_printer_row(self, p: Printer) -> bool:
        # Skip exact duplicates
        for iid in self.tree.get_children():
            vals = self.tree.item(iid, "values")
            if (vals[0], vals[1], vals[2]) == (p.name, p.port_name, p.ip):
                return False
        self.tree.insert("", "end", values=(p.name, p.port_name, p.ip))
        self._update_count()
        return True

    def _update_count(self):
        n = len(self.tree.get_children())
        self.count_var.set(f"{n} printer{'s' if n != 1 else ''}")

    # ------------------------------------------------------------------
    # Log helpers
    # ------------------------------------------------------------------
    def _append_log(self, line: str):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", line + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _drain_log_queue(self):
        try:
            while True:
                self._append_log(self.log_queue.get_nowait())
        except queue.Empty:
            pass
        self.after(100, self._drain_log_queue)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------
    def _on_add_manual(self):
        name = self.name_var.get().strip()
        port_name = self.port_name_var.get().strip()
        ip = self.ip_var.get().strip()
        if not (name and port_name and ip):
            messagebox.showerror("Missing fields", "Please fill in Name, Port name and IP.")
            return
        added = self._add_printer_row(Printer(name, port_name, ip))
        if added:
            self.name_var.set("")
            self.port_name_var.set("")
            self.ip_var.set("")
        else:
            messagebox.showinfo("Duplicate", "That printer is already in the list.")

    def _on_tree_double_click(self, _event):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], "values")
        self.name_var.set(vals[0])
        self.port_name_var.set(vals[1])
        self.ip_var.set(vals[2])

    def _on_load_file(self):
        path_str = filedialog.askopenfilename(
            title="Open printer definitions",
            filetypes=[
                ("JSON or CSV", "*.json *.csv"),
                ("JSON", "*.json"),
                ("CSV", "*.csv"),
                ("All files", "*.*"),
            ],
        )
        if not path_str:
            return
        try:
            printers = load_from_file(Path(path_str))
        except Exception as exc:
            messagebox.showerror("Load failed", str(exc))
            return
        added = sum(1 for p in printers if self._add_printer_row(p))
        self.log.info("Loaded %d printer(s) from %s (%d new)",
                      len(printers), path_str, added)

    def _on_add_defaults(self):
        added = sum(1 for p in DEFAULT_PRINTERS if self._add_printer_row(p))
        self.log.info("Added %d default printer(s)", added)

    def _on_save_file(self):
        printers = self._printers_in_list()
        if not printers:
            messagebox.showinfo("Nothing to save", "List is empty.")
            return
        path_str = filedialog.asksaveasfilename(
            title="Save printer list",
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("CSV", "*.csv")],
        )
        if not path_str:
            return
        path = Path(path_str)
        try:
            if path.suffix.lower() == ".csv":
                with path.open("w", encoding="utf-8-sig", newline="") as f:
                    w = csv_module.writer(f)
                    w.writerow(["name", "port_name", "ip"])
                    for p in printers:
                        w.writerow([p.name, p.port_name, p.ip])
            else:
                with path.open("w", encoding="utf-8") as f:
                    json.dump(
                        [{"name": p.name, "port_name": p.port_name, "ip": p.ip}
                         for p in printers],
                        f, ensure_ascii=False, indent=2,
                    )
            self.log.info("Saved %d printer(s) to %s", len(printers), path)
        except Exception as exc:
            messagebox.showerror("Save failed", str(exc))

    def _on_remove_selected(self):
        for iid in self.tree.selection():
            self.tree.delete(iid)
        self._update_count()

    def _on_clear(self):
        if not self.tree.get_children():
            return
        if messagebox.askyesno("Clear list", "Remove all printers from the list?"):
            for iid in self.tree.get_children():
                self.tree.delete(iid)
            self._update_count()

    def _on_install(self):
        printers = self._printers_in_list()
        if not printers:
            messagebox.showinfo("Empty list", "Add some printers first.")
            return
        try:
            port_number = int(self.port_var.get())
        except ValueError:
            messagebox.showerror("Invalid port", "TCP port must be an integer.")
            return
        driver = self.driver_var.get().strip()
        if not driver:
            messagebox.showerror("Invalid driver", "Driver name is required.")
            return
        if sys.platform != "win32":
            messagebox.showerror("Wrong OS", "This must be run on Windows.")
            return

        self.install_btn.configure(state="disabled", text="Installing…")
        threading.Thread(
            target=self._install_thread,
            args=(printers, driver, port_number),
            daemon=True,
        ).start()

    def _install_thread(self, printers, driver, port_number):
        failed = 0
        for p in printers:
            try:
                install_printer(p, driver, port_number, self.log)
            except Exception as exc:
                self.log.error("'%s' failed: %s", p.name, exc)
                failed += 1
        if failed:
            self.log.error("%d printer(s) failed.", failed)
        else:
            self.log.info("All printers processed successfully.")
        self.after(0, lambda: self.install_btn.configure(
            state="normal", text="Install printers"
        ))


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
