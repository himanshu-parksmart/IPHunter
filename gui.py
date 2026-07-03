#!/usr/bin/env python3
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from main import get_current_subnet, scan_network


class IPHunterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("IPHunter")
        self.root.geometry("900x520")
        self.root.minsize(760, 420)

        self.subnet_var = tk.StringVar(value=get_current_subnet() or "")
        self.status_var = tk.StringVar(value="Ready.")
        self.scan_in_progress = False

        self._build_ui()

    def _build_ui(self):
        container = ttk.Frame(self.root, padding=16)
        container.pack(fill="both", expand=True)

        controls = ttk.Frame(container)
        controls.pack(fill="x")

        ttk.Label(controls, text="Subnet").grid(row=0, column=0, sticky="w")
        subnet_entry = ttk.Entry(controls, textvariable=self.subnet_var)
        subnet_entry.grid(row=1, column=0, sticky="ew", padx=(0, 12))

        self.scan_button = ttk.Button(controls, text="Scan Network", command=self.start_scan)
        self.scan_button.grid(row=1, column=1, sticky="ew")

        self.refresh_button = ttk.Button(controls, text="Detect Subnet", command=self.detect_subnet)
        self.refresh_button.grid(row=1, column=2, sticky="ew", padx=(12, 0))

        controls.columnconfigure(0, weight=1)

        columns = ("ip", "status", "latency", "mac", "vendor")
        self.tree = ttk.Treeview(container, columns=columns, show="headings", height=16)
        headings = {
            "ip": "IP Address",
            "status": "Status",
            "latency": "Latency",
            "mac": "MAC Address",
            "vendor": "Vendor / Device",
        }
        widths = {
            "ip": 150,
            "status": 90,
            "latency": 120,
            "mac": 170,
            "vendor": 320,
        }
        for key in columns:
            self.tree.heading(key, text=headings[key])
            self.tree.column(key, width=widths[key], anchor="w", stretch=key == "vendor")

        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True, pady=(16, 0))
        scrollbar.pack(side="right", fill="y", pady=(16, 0))

        status_bar = ttk.Label(container, textvariable=self.status_var, anchor="w")
        status_bar.pack(fill="x", pady=(12, 0))

    def detect_subnet(self):
        subnet = get_current_subnet()
        if subnet:
            self.subnet_var.set(subnet)
            self.status_var.set(f"Detected subnet: {subnet}")
        else:
            messagebox.showerror("IPHunter", "Could not detect the current subnet.")

    def start_scan(self):
        if self.scan_in_progress:
            return

        subnet = self.subnet_var.get().strip() or None
        self.scan_in_progress = True
        self.scan_button.configure(state="disabled")
        self.refresh_button.configure(state="disabled")
        self.status_var.set("Scanning network...")
        self._clear_rows()

        worker = threading.Thread(target=self._scan_worker, args=(subnet,), daemon=True)
        worker.start()

    def _scan_worker(self, subnet):
        try:
            scanned_subnet, hosts = scan_network(subnet)
            self.root.after(0, self._scan_complete, scanned_subnet, hosts)
        except Exception as exc:
            self.root.after(0, self._scan_failed, str(exc))

    def _scan_complete(self, subnet, hosts):
        for host in hosts:
            self.tree.insert("", "end", values=(host["ip"], host["status"], host["latency"], host["mac"], host["vendor"]))
        self.subnet_var.set(subnet)
        self.status_var.set(f"Scan finished. Found {len(hosts)} active host(s) on {subnet}.")
        self._set_idle()

    def _scan_failed(self, error_message):
        messagebox.showerror("IPHunter", error_message)
        self.status_var.set(error_message)
        self._set_idle()

    def _set_idle(self):
        self.scan_in_progress = False
        self.scan_button.configure(state="normal")
        self.refresh_button.configure(state="normal")

    def _clear_rows(self):
        for item in self.tree.get_children():
            self.tree.delete(item)


def main():
    root = tk.Tk()
    ttk.Style().theme_use("default")
    app = IPHunterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
