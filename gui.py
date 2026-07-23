#!/usr/bin/env python3
import csv
import ipaddress
import threading
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

from main import get_current_subnet, scan_network


class IPHunterApp:
    """A small, focused desktop dashboard for discovering devices on a LAN."""

    COLORS = {
        "navy": "#0B1220",
        "navy_soft": "#111B2E",
        "panel": "#FFFFFF",
        "canvas": "#F4F7FB",
        "border": "#DFE7F1",
        "text": "#172033",
        "muted": "#667085",
        "muted_light": "#98A2B3",
        "blue": "#3974F6",
        "blue_dark": "#285BCC",
        "blue_soft": "#EDF3FF",
        "green": "#12A66A",
        "green_soft": "#EAF8F2",
        "orange": "#E78A24",
        "red": "#D94B4B",
        "white": "#FFFFFF",
    }

    def __init__(self, root):
        self.root = root
        self.root.title("IPHunter — Network Discovery")
        self.root.geometry("1160x720")
        self.root.minsize(920, 610)
        self.root.configure(bg=self.COLORS["canvas"])

        self.subnet_var = tk.StringVar(value=get_current_subnet() or "")
        self.status_var = tk.StringVar(value="Ready to scan")
        self.status_detail_var = tk.StringVar(value="Enter a subnet or use the detected network")
        self.search_var = tk.StringVar()
        self.host_count_var = tk.StringVar(value="0")
        self.vendor_count_var = tk.StringVar(value="0")
        self.last_scan_var = tk.StringVar(value="Never")
        self.scan_in_progress = False
        self.all_hosts = []
        self.sort_column = "ip"
        self.sort_reverse = False

        self._configure_styles()
        self._build_ui()
        self.search_var.trace_add("write", lambda *_: self._render_hosts())

    def _configure_styles(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")

        style.configure(
            "Primary.TButton",
            background=self.COLORS["blue"],
            foreground=self.COLORS["white"],
            bordercolor=self.COLORS["blue"],
            focusthickness=0,
            focuscolor=self.COLORS["blue"],
            padding=(18, 11),
            font=("TkDefaultFont", 10, "bold"),
        )
        style.map(
            "Primary.TButton",
            background=[("disabled", "#AFC4F4"), ("active", self.COLORS["blue_dark"])],
            bordercolor=[("disabled", "#AFC4F4"), ("active", self.COLORS["blue_dark"])],
        )
        style.configure(
            "Secondary.TButton",
            background=self.COLORS["white"],
            foreground=self.COLORS["text"],
            bordercolor=self.COLORS["border"],
            focusthickness=0,
            focuscolor=self.COLORS["white"],
            padding=(14, 10),
            font=("TkDefaultFont", 10, "bold"),
        )
        style.map("Secondary.TButton", background=[("active", "#F8FAFC")])
        style.configure(
            "IPHunter.Treeview",
            background=self.COLORS["panel"],
            fieldbackground=self.COLORS["panel"],
            foreground=self.COLORS["text"],
            rowheight=44,
            borderwidth=0,
            relief="flat",
            font=("TkDefaultFont", 10),
        )
        style.configure(
            "IPHunter.Treeview.Heading",
            background="#F8FAFC",
            foreground=self.COLORS["muted"],
            borderwidth=0,
            relief="flat",
            padding=(12, 11),
            font=("TkDefaultFont", 9, "bold"),
        )
        style.map(
            "IPHunter.Treeview",
            background=[("selected", self.COLORS["blue_soft"])],
            foreground=[("selected", self.COLORS["text"])],
        )
        style.map("IPHunter.Treeview.Heading", background=[("active", "#F1F5F9")])
        style.configure(
            "Scan.Horizontal.TProgressbar",
            troughcolor="#DCE6F7",
            background=self.COLORS["blue"],
            borderwidth=0,
            thickness=4,
        )

    def _build_ui(self):
        self._build_header()

        content = tk.Frame(self.root, bg=self.COLORS["canvas"])
        content.pack(fill="both", expand=True, padx=28, pady=(24, 22))

        self._build_scan_card(content)
        self._build_stats(content)
        self._build_results(content)
        self._build_status_bar(content)

    def _build_header(self):
        header = tk.Frame(self.root, bg=self.COLORS["navy"], height=78)
        header.pack(fill="x")
        header.pack_propagate(False)

        inner = tk.Frame(header, bg=self.COLORS["navy"])
        inner.pack(fill="both", expand=True, padx=28)

        logo = tk.Canvas(inner, width=38, height=38, bg=self.COLORS["navy"], highlightthickness=0)
        logo.pack(side="left", pady=20)
        logo.create_oval(3, 3, 35, 35, fill=self.COLORS["blue"], outline="")
        logo.create_oval(11, 11, 27, 27, outline=self.COLORS["white"], width=2)
        logo.create_oval(17, 17, 21, 21, fill=self.COLORS["white"], outline="")
        logo.create_line(19, 3, 19, 10, fill=self.COLORS["white"], width=2)
        logo.create_line(19, 28, 19, 35, fill=self.COLORS["white"], width=2)

        brand = tk.Frame(inner, bg=self.COLORS["navy"])
        brand.pack(side="left", padx=(11, 0), pady=16)
        tk.Label(
            brand,
            text="IPHunter",
            bg=self.COLORS["navy"],
            fg=self.COLORS["white"],
            font=("TkDefaultFont", 17, "bold"),
        ).pack(anchor="w")
        tk.Label(
            brand,
            text="NETWORK DISCOVERY",
            bg=self.COLORS["navy"],
            fg="#8190AA",
            font=("TkDefaultFont", 8, "bold"),
        ).pack(anchor="w")

        badge = tk.Frame(inner, bg=self.COLORS["navy_soft"], padx=12, pady=7)
        badge.pack(side="right", pady=22)
        tk.Label(badge, text="●", bg=self.COLORS["navy_soft"], fg=self.COLORS["green"], font=("TkDefaultFont", 9)).pack(side="left")
        tk.Label(
            badge,
            text="LOCAL SCANNER",
            bg=self.COLORS["navy_soft"],
            fg="#B9C5D8",
            font=("TkDefaultFont", 8, "bold"),
        ).pack(side="left", padx=(6, 0))

    def _build_scan_card(self, parent):
        card = tk.Frame(parent, bg=self.COLORS["panel"], highlightbackground=self.COLORS["border"], highlightthickness=1)
        card.pack(fill="x")

        body = tk.Frame(card, bg=self.COLORS["panel"])
        body.pack(fill="x", padx=22, pady=18)
        body.columnconfigure(0, weight=1)

        tk.Label(
            body,
            text="Network range",
            bg=self.COLORS["panel"],
            fg=self.COLORS["text"],
            font=("TkDefaultFont", 11, "bold"),
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            body,
            text="CIDR notation, for example 192.168.1.0/24",
            bg=self.COLORS["panel"],
            fg=self.COLORS["muted"],
            font=("TkDefaultFont", 9),
        ).grid(row=1, column=0, sticky="w", pady=(3, 10))

        entry_shell = tk.Frame(body, bg=self.COLORS["white"], highlightbackground="#CCD6E4", highlightthickness=1)
        entry_shell.grid(row=2, column=0, sticky="ew", padx=(0, 12))
        tk.Label(entry_shell, text="◎", bg=self.COLORS["white"], fg=self.COLORS["blue"], font=("TkDefaultFont", 15, "bold")).pack(side="left", padx=(13, 7))
        self.subnet_entry = tk.Entry(
            entry_shell,
            textvariable=self.subnet_var,
            bd=0,
            relief="flat",
            bg=self.COLORS["white"],
            fg=self.COLORS["text"],
            insertbackground=self.COLORS["text"],
            font=("TkFixedFont", 11),
        )
        self.subnet_entry.pack(side="left", fill="x", expand=True, ipady=11, padx=(0, 10))
        self.subnet_entry.bind("<Return>", lambda _event: self.start_scan())

        self.detect_button = ttk.Button(body, text="Detect subnet", style="Secondary.TButton", command=self.detect_subnet)
        self.detect_button.grid(row=2, column=1, padx=(0, 10))
        self.scan_button = ttk.Button(body, text="Scan network", style="Primary.TButton", command=self.start_scan)
        self.scan_button.grid(row=2, column=2)

    def _build_stats(self, parent):
        stats = tk.Frame(parent, bg=self.COLORS["canvas"])
        stats.pack(fill="x", pady=16)
        for index in range(3):
            stats.columnconfigure(index, weight=1, uniform="stat")

        self._stat_card(stats, 0, "ACTIVE HOSTS", self.host_count_var, self.COLORS["blue"], "Devices responding")
        self._stat_card(stats, 1, "VENDORS FOUND", self.vendor_count_var, self.COLORS["green"], "Identified manufacturers")
        self._stat_card(stats, 2, "LAST SCAN", self.last_scan_var, self.COLORS["orange"], "Local time")

    def _stat_card(self, parent, column, title, variable, accent, caption):
        padx = (0, 8) if column == 0 else ((8, 0) if column == 2 else 8)
        card = tk.Frame(parent, bg=self.COLORS["panel"], highlightbackground=self.COLORS["border"], highlightthickness=1)
        card.grid(row=0, column=column, sticky="ew", padx=padx)
        tk.Frame(card, bg=accent, width=4).pack(side="left", fill="y")
        text = tk.Frame(card, bg=self.COLORS["panel"])
        text.pack(side="left", fill="both", expand=True, padx=16, pady=12)
        tk.Label(text, text=title, bg=self.COLORS["panel"], fg=self.COLORS["muted"], font=("TkDefaultFont", 8, "bold")).pack(anchor="w")
        tk.Label(text, textvariable=variable, bg=self.COLORS["panel"], fg=self.COLORS["text"], font=("TkDefaultFont", 18, "bold")).pack(anchor="w", pady=(2, 0))
        tk.Label(text, text=caption, bg=self.COLORS["panel"], fg=self.COLORS["muted_light"], font=("TkDefaultFont", 8)).pack(anchor="w", pady=(1, 0))

    def _build_results(self, parent):
        panel = tk.Frame(parent, bg=self.COLORS["panel"], highlightbackground=self.COLORS["border"], highlightthickness=1)
        panel.pack(fill="both", expand=True)

        toolbar = tk.Frame(panel, bg=self.COLORS["panel"])
        toolbar.pack(fill="x", padx=18, pady=14)
        tk.Label(toolbar, text="Discovered devices", bg=self.COLORS["panel"], fg=self.COLORS["text"], font=("TkDefaultFont", 12, "bold")).pack(side="left")

        self.export_button = ttk.Button(toolbar, text="Export CSV", style="Secondary.TButton", command=self.export_csv, state="disabled")
        self.export_button.pack(side="right")

        search_shell = tk.Frame(toolbar, bg="#F8FAFC", highlightbackground=self.COLORS["border"], highlightthickness=1)
        search_shell.pack(side="right", padx=(0, 10))
        tk.Label(search_shell, text="⌕", bg="#F8FAFC", fg=self.COLORS["muted"], font=("TkDefaultFont", 14)).pack(side="left", padx=(10, 5))
        search_entry = tk.Entry(
            search_shell,
            textvariable=self.search_var,
            width=23,
            bd=0,
            relief="flat",
            bg="#F8FAFC",
            fg=self.COLORS["text"],
            insertbackground=self.COLORS["text"],
            font=("TkDefaultFont", 9),
        )
        search_entry.pack(side="left", ipady=8, padx=(0, 9))
        search_entry.insert(0, "")

        columns = ("ip", "status", "latency", "mac", "vendor")
        table_shell = tk.Frame(panel, bg=self.COLORS["panel"])
        table_shell.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(table_shell, columns=columns, show="headings", style="IPHunter.Treeview")
        headings = {
            "ip": "IP ADDRESS",
            "status": "STATUS",
            "latency": "LATENCY",
            "mac": "MAC ADDRESS",
            "vendor": "VENDOR / DEVICE",
        }
        widths = {"ip": 155, "status": 105, "latency": 120, "mac": 180, "vendor": 310}
        for key in columns:
            self.tree.heading(key, text=headings[key], command=lambda col=key: self.sort_by(col))
            self.tree.column(key, width=widths[key], minwidth=80, anchor="w", stretch=key == "vendor")

        self.tree.tag_configure("even", background=self.COLORS["white"])
        self.tree.tag_configure("odd", background="#FBFCFE")
        self.tree.tag_configure("raspberry", background="#F1EAFB", foreground="#5B2B82")
        self.tree.tag_configure("nvidia", background="#EEF8E5", foreground="#356900")
        self.tree.tag_configure("empty", foreground=self.COLORS["muted_light"])

        scrollbar = ttk.Scrollbar(table_shell, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self._show_empty_state("No scan results yet", "Run a scan to discover devices on your network")

    def _build_status_bar(self, parent):
        bar = tk.Frame(parent, bg=self.COLORS["canvas"])
        bar.pack(fill="x", pady=(12, 0))
        self.status_dot = tk.Label(bar, text="●", bg=self.COLORS["canvas"], fg=self.COLORS["green"], font=("TkDefaultFont", 9))
        self.status_dot.pack(side="left")
        tk.Label(bar, textvariable=self.status_var, bg=self.COLORS["canvas"], fg=self.COLORS["text"], font=("TkDefaultFont", 9, "bold")).pack(side="left", padx=(5, 0))
        tk.Label(bar, textvariable=self.status_detail_var, bg=self.COLORS["canvas"], fg=self.COLORS["muted"], font=("TkDefaultFont", 9)).pack(side="left", padx=(8, 0))
        self.progress = ttk.Progressbar(bar, mode="indeterminate", length=150, style="Scan.Horizontal.TProgressbar")
        self.progress.pack(side="right")

    def detect_subnet(self):
        subnet = get_current_subnet()
        if subnet:
            self.subnet_var.set(subnet)
            self.status_var.set("Subnet detected")
            self.status_detail_var.set(subnet)
            self.status_dot.configure(fg=self.COLORS["green"])
        else:
            self._show_error("Could not detect an active IPv4 subnet.")

    def start_scan(self):
        if self.scan_in_progress:
            return

        subnet = self.subnet_var.get().strip()
        if subnet:
            try:
                ipaddress.ip_network(subnet, strict=False)
            except ValueError:
                self._show_error("Enter a valid subnet in CIDR notation, such as 192.168.1.0/24.")
                self.subnet_entry.focus_set()
                return

        self.scan_in_progress = True
        self.scan_button.configure(state="disabled", text="Scanning…")
        self.detect_button.configure(state="disabled")
        self.export_button.configure(state="disabled")
        self.subnet_entry.configure(state="disabled")
        self.status_var.set("Scanning network")
        self.status_detail_var.set(subnet or "Detecting the current subnet")
        self.status_dot.configure(fg=self.COLORS["blue"])
        self.progress.start(12)
        self.all_hosts = []
        self._show_empty_state("Scanning for active hosts…", "This may take a moment")

        worker = threading.Thread(target=self._scan_worker, args=(subnet or None,), daemon=True)
        worker.start()

    def _scan_worker(self, subnet):
        try:
            scanned_subnet, hosts = scan_network(subnet)
            self.root.after(0, self._scan_complete, scanned_subnet, hosts)
        except Exception as exc:
            self.root.after(0, self._scan_failed, str(exc))

    def _scan_complete(self, subnet, hosts):
        self.all_hosts = hosts
        self.subnet_var.set(subnet)
        self.host_count_var.set(str(len(hosts)))
        vendors = {host["vendor"] for host in hosts if host["vendor"] not in ("N/A", "Unknown")}
        self.vendor_count_var.set(str(len(vendors)))
        self.last_scan_var.set(datetime.now().strftime("%I:%M %p").lstrip("0"))
        self.status_var.set("Scan complete")
        self.status_detail_var.set(f"{len(hosts)} active host{'s' if len(hosts) != 1 else ''} found on {subnet}")
        self.status_dot.configure(fg=self.COLORS["green"])
        self._render_hosts()
        self._set_idle()

    def _scan_failed(self, error_message):
        self.status_var.set("Scan failed")
        self.status_detail_var.set(error_message)
        self.status_dot.configure(fg=self.COLORS["red"])
        self._show_empty_state("Unable to complete scan", error_message)
        self._set_idle()
        messagebox.showerror("IPHunter", error_message)

    def _set_idle(self):
        self.scan_in_progress = False
        self.progress.stop()
        self.scan_button.configure(state="normal", text="Scan network")
        self.detect_button.configure(state="normal")
        self.subnet_entry.configure(state="normal")
        if self.all_hosts:
            self.export_button.configure(state="normal")

    def _show_empty_state(self, title, detail):
        self._clear_rows()
        self.tree.insert("", "end", values=(title, "", detail, "", ""), tags=("empty",))

    def _render_hosts(self):
        self._clear_rows()
        query = self.search_var.get().strip().lower()
        hosts = [host for host in self.all_hosts if not query or any(query in str(value).lower() for value in host.values())]
        hosts = sorted(hosts, key=self._sort_key, reverse=self.sort_reverse)

        if not hosts:
            if self.all_hosts and query:
                self._show_empty_state("No matching devices", "Try a different search term")
            elif not self.scan_in_progress:
                self._show_empty_state("No active hosts found", "Try scanning another subnet")
            return

        for index, host in enumerate(hosts):
            status = "●  Up" if host["status"].lower() == "up" else host["status"]
            vendor = host["vendor"].lower()
            if "raspberry" in vendor:
                row_tag = "raspberry"
            elif "nvidia" in vendor:
                row_tag = "nvidia"
            else:
                row_tag = "even" if index % 2 == 0 else "odd"
            self.tree.insert(
                "",
                "end",
                values=(host["ip"], status, host["latency"], host["mac"], host["vendor"]),
                tags=(row_tag,),
            )

    def _sort_key(self, host):
        value = host.get(self.sort_column, "")
        if self.sort_column == "ip":
            try:
                return int(ipaddress.ip_address(value))
            except ValueError:
                return 0
        if self.sort_column == "latency":
            try:
                return float(str(value).split()[0])
            except (ValueError, IndexError):
                return float("inf")
        return str(value).lower()

    def sort_by(self, column):
        if column == self.sort_column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = column
            self.sort_reverse = False
        self._render_hosts()

    def export_csv(self):
        if not self.all_hosts:
            return
        filename = f"iphunter-scan-{datetime.now():%Y%m%d-%H%M}.csv"
        path = filedialog.asksaveasfilename(
            title="Export scan results",
            defaultextension=".csv",
            initialfile=filename,
            filetypes=(("CSV files", "*.csv"), ("All files", "*.*")),
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=("ip", "status", "latency", "mac", "vendor"))
                writer.writeheader()
                writer.writerows(self.all_hosts)
            self.status_var.set("Export complete")
            self.status_detail_var.set(path)
            self.status_dot.configure(fg=self.COLORS["green"])
        except OSError as exc:
            self._show_error(f"Could not export results: {exc}")

    def _show_error(self, message):
        self.status_var.set("Action needed")
        self.status_detail_var.set(message)
        self.status_dot.configure(fg=self.COLORS["red"])
        messagebox.showerror("IPHunter", message)

    def _clear_rows(self):
        for item in self.tree.get_children():
            self.tree.delete(item)


def main():
    root = tk.Tk()
    IPHunterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
