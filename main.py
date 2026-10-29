#!/usr/bin/env python3
import argparse
from functools import lru_cache
import ipaddress
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys

import psutil
from tabulate import tabulate


def get_current_subnet():
    """Detect the subnet of the active network interface."""
    addrs = psutil.net_if_addrs()
    for _, addr_list in addrs.items():
        for addr in addr_list:
            if addr.family != socket.AF_INET:
                continue
            ip = addr.address
            netmask = addr.netmask
            if not netmask or ip.startswith("127."):
                continue
            try:
                network = ipaddress.IPv4Network(f"{ip}/{netmask}", strict=False)
                return str(network)
            except ValueError:
                continue
    return None


def parse_windows_ssid(output):
    """Extract the connected SSID from ``netsh wlan show interfaces``."""
    match = re.search(r"^\s*SSID\s*:\s*(.+?)\s*$", output, re.MULTILINE | re.IGNORECASE)
    return match.group(1) if match else None


def parse_macos_ssid(output):
    """Extract an unredacted SSID from networksetup or privileged wdutil."""
    patterns = (
        r"Current Wi-Fi Network:\s*(.+)$",
        r"^\s*SSID\s*:\s*(.+?)\s*$",
    )
    for pattern in patterns:
        match = re.search(pattern, output, re.MULTILINE | re.IGNORECASE)
        if match:
            ssid = match.group(1).strip()
            if ssid and ssid.lower() != "<redacted>":
                return ssid
    return None


def get_connected_ssid(native_authorization=False):
    """Return the current Wi-Fi network name, or None when unavailable."""
    if sys.platform == "win32":
        commands = [["netsh", "wlan", "show", "interfaces"]]
    elif sys.platform == "darwin":
        # Wi-Fi is normally en0, but can be en1 on Macs with other adapters.
        commands = [
            ["networksetup", "-getairportnetwork", "en0"],
            ["networksetup", "-getairportnetwork", "en1"],
            [
                "osascript",
                "-l",
                "JavaScript",
                "-e",
                'ObjC.import("CoreWLAN"); const i=$.CWWiFiClient.sharedWiFiClient.interface; '
                'i && i.ssid ? ObjC.unwrap(i.ssid) : ""',
            ],
            ["sudo", "-n", "/usr/bin/wdutil", "info"],
        ]
        if native_authorization:
            commands.append(
                [
                    "osascript",
                    "-e",
                    'do shell script "/usr/bin/wdutil info" with administrator privileges',
                ]
            )
    else:
        commands = [["nmcli", "-t", "-f", "ACTIVE,SSID", "device", "wifi"]]

    for command in commands:
        if not shutil.which(command[0]):
            continue
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=5)
        except (OSError, subprocess.SubprocessError):
            continue

        output = f"{result.stdout}\n{result.stderr}".strip()
        if sys.platform == "win32":
            ssid = parse_windows_ssid(output)
        elif sys.platform == "darwin":
            ssid = parse_macos_ssid(output)
            if command[:3] == ["osascript", "-l", "JavaScript"] and output and "Error:" not in output:
                ssid = output.strip()
        else:
            match = re.search(r"^yes:(.+)$", output, re.MULTILINE | re.IGNORECASE)
            ssid = match.group(1).replace(r"\:", ":").strip() if match else None
        if ssid:
            return ssid
    return None


def find_nmap_executable():
    """Find nmap from PATH or common GUI-app installation locations."""
    path_match = shutil.which("nmap")
    if path_match:
        return path_match
    candidates = [
        Path("/opt/homebrew/bin/nmap"),
        Path("/usr/local/bin/nmap"),
        Path("C:/Program Files/Nmap/nmap.exe"),
        Path("C:/Program Files (x86)/Nmap/nmap.exe"),
    ]
    return str(next((path for path in candidates if path.is_file()), "")) or None


def build_nmap_command(subnet, executable="nmap", privileged=False):
    """Build the nmap discovery command, optionally elevating it on macOS."""
    command = [executable, "-sn", subnet]
    if privileged and sys.platform == "darwin" and hasattr(os, "geteuid") and os.geteuid() != 0:
        return ["sudo", "-p", "IPHunter needs administrator access for MAC discovery. Password: ", *command]
    return command


def parse_nmap_output(output):
    """Parse nmap ping-scan output into structured host rows."""
    hosts = []
    current_ip, hostname, latency, mac, vendor = None, None, None, None, None

    for line in output.splitlines():
        if line.startswith("Nmap scan report for"):
            if current_ip:
                hosts.append(
                    {
                        "ip": current_ip,
                        "hostname": hostname or "N/A",
                        "status": "Up",
                        "latency": latency or "N/A",
                        "mac": mac or "N/A",
                        "vendor": vendor or "N/A",
                    }
                )
            # Reports with reverse DNS use: "hostname (192.168.1.10)".
            # Keep only the address so it can be matched with the ARP cache.
            address_match = re.search(r"\(?((?:\d{1,3}\.){3}\d{1,3})\)?\s*$", line)
            current_ip = address_match.group(1) if address_match else line.split()[-1]
            report_target = line.removeprefix("Nmap scan report for ").strip()
            hostname = report_target[: report_target.rfind(" (")] if report_target.endswith(f"({current_ip})") else None
            latency, mac, vendor = None, None, None
        elif "Host is up" in line:
            match = re.search(r"\((.*?) latency\)", line)
            latency = match.group(1) if match else "N/A"
        elif "MAC Address:" in line:
            parts = line.split("MAC Address:")[1].strip().split(" ", 1)
            mac = parts[0]
            vendor = parts[1].strip("()") if len(parts) > 1 else "Unknown"

    if current_ip:
        hosts.append(
            {
                "ip": current_ip,
                "hostname": hostname or "N/A",
                "status": "Up",
                "latency": latency or "N/A",
                "mac": mac or "N/A",
                "vendor": vendor or "N/A",
            }
        )

    return hosts


def normalize_mac(mac):
    """Return a consistent uppercase MAC address, or None for invalid entries."""
    parts = re.split(r"[:-]", mac.strip())
    if len(parts) != 6 or any(not re.fullmatch(r"[0-9A-Fa-f]{1,2}", part) for part in parts):
        return None
    return ":".join(part.zfill(2).upper() for part in parts)


def parse_neighbor_output(output):
    """Parse macOS, Linux, or Windows ARP/neighbor output into IP-to-MAC rows."""
    entries = {}
    ip_pattern = re.compile(r"(?<![\d.])((?:\d{1,3}\.){3}\d{1,3})(?![\d.])")
    mac_pattern = re.compile(r"(?<![0-9A-Fa-f])((?:[0-9A-Fa-f]{1,2}[:-]){5}[0-9A-Fa-f]{1,2})(?![0-9A-Fa-f])")

    for line in output.splitlines():
        ip_match = ip_pattern.search(line)
        mac_match = mac_pattern.search(line)
        if not ip_match or not mac_match:
            continue
        try:
            ipaddress.ip_address(ip_match.group(1))
        except ValueError:
            continue
        mac = normalize_mac(mac_match.group(1))
        if mac and mac != "FF:FF:FF:FF:FF:FF":
            entries[ip_match.group(1)] = mac
    return entries


def get_neighbor_entries():
    """Read the OS neighbor cache without requiring administrator privileges."""
    if sys.platform == "win32":
        commands = [["arp", "-a"]]
    elif sys.platform == "darwin":
        commands = [["arp", "-an"]]
    else:
        commands = [["ip", "neigh", "show"], ["arp", "-an"]]

    for command in commands:
        if not shutil.which(command[0]):
            continue
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=10)
        except (OSError, subprocess.SubprocessError):
            continue
        entries = parse_neighbor_output(result.stdout)
        if entries:
            return entries
    return {}


def find_mac_prefix_database():
    """Locate nmap's bundled IEEE vendor-prefix database."""
    candidates = []
    nmap_path = find_nmap_executable()
    if nmap_path:
        resolved = Path(nmap_path).resolve()
        candidates.extend(
            [
                resolved.parent / "nmap-mac-prefixes",
                resolved.parent.parent / "share" / "nmap" / "nmap-mac-prefixes",
                Path(nmap_path).parent.parent / "share" / "nmap" / "nmap-mac-prefixes",
            ]
        )
    candidates.extend(
        [
            Path("/opt/homebrew/share/nmap/nmap-mac-prefixes"),
            Path("/usr/local/share/nmap/nmap-mac-prefixes"),
            Path("/usr/share/nmap/nmap-mac-prefixes"),
        ]
    )
    return next((path for path in candidates if path.is_file()), None)


@lru_cache(maxsize=1)
def load_vendor_prefixes():
    """Load OUI vendor names from nmap's local database once per process."""
    database = find_mac_prefix_database()
    if not database:
        return {}

    vendors = {}
    try:
        with database.open(encoding="utf-8", errors="replace") as prefix_file:
            for line in prefix_file:
                if not line or line.startswith("#"):
                    continue
                parts = line.strip().split(maxsplit=1)
                if len(parts) == 2 and re.fullmatch(r"[0-9A-Fa-f]{6}", parts[0]):
                    vendors[parts[0].upper()] = parts[1]
    except OSError:
        return {}
    return vendors


def vendor_for_mac(mac):
    """Resolve a normalized MAC using nmap's bundled OUI data."""
    normalized = normalize_mac(mac)
    if not normalized:
        return "N/A"
    first_octet = int(normalized[:2], 16)
    if first_octet & 0x02:
        return "Private / randomized"
    return load_vendor_prefixes().get(normalized.replace(":", "")[:6], "Unknown")


def enrich_hosts_from_neighbors(hosts, subnet=None, neighbors=None):
    """Merge passwordless OS neighbor-cache data into scan results."""
    neighbors = get_neighbor_entries() if neighbors is None else neighbors
    existing_ips = {host["ip"] for host in hosts}

    # An unprivileged nmap scan still contacts every address and therefore
    # populates the local neighbor cache, even when a device ignores nmap's
    # higher-level discovery probes. Include those layer-2 responses as hosts.
    network = None
    if subnet:
        try:
            network = ipaddress.ip_network(subnet, strict=False)
        except ValueError:
            pass
    if network and isinstance(network, ipaddress.IPv4Network):
        for ip, mac in neighbors.items():
            try:
                address = ipaddress.ip_address(ip)
            except ValueError:
                continue
            if address in network and address not in (network.network_address, network.broadcast_address) and ip not in existing_ips:
                hosts.append(
                    {
                        "ip": ip,
                        "hostname": "N/A",
                        "status": "Up",
                        "latency": "N/A",
                        "mac": mac,
                        "vendor": vendor_for_mac(mac),
                    }
                )
                existing_ips.add(ip)

    for host in hosts:
        mac = neighbors.get(host["ip"])
        if mac and host.get("mac") in (None, "N/A"):
            host["mac"] = mac
        if host.get("mac") not in (None, "N/A") and host.get("vendor") in (None, "N/A", "Unknown"):
            host["vendor"] = vendor_for_mac(host["mac"])
    hosts.sort(key=lambda host: int(ipaddress.ip_address(host["ip"])))
    return hosts


def scan_network(subnet=None, privileged=False, native_authorization=False):
    """Run a ping scan and return the subnet plus parsed hosts."""
    if not subnet:
        subnet = get_current_subnet()
        if not subnet:
            raise RuntimeError("Could not detect the current subnet.")

    nmap_executable = find_nmap_executable()
    if not nmap_executable:
        if sys.platform == "win32":
            raise RuntimeError(
                "Nmap is required but was not found. Install it from "
                "https://nmap.org/download.html, keep the default Npcap and "
                "'Register Nmap Path' options enabled, then restart IPHunter."
            )
        raise RuntimeError("nmap is not installed or not available on PATH.")

    command = build_nmap_command(subnet, nmap_executable, privileged=privileged)
    if native_authorization and privileged and sys.platform == "darwin" and os.geteuid() != 0:
        # A packaged/windowed app has no terminal in which sudo can prompt.
        # AppleScript provides the standard macOS administrator dialog instead.
        apple_script = (
            "on run argv\n"
            'set commandText to quoted form of (item 1 of argv) & " -sn " & quoted form of (item 2 of argv)\n'
            "do shell script commandText with administrator privileges\n"
            "end run"
        )
        command = ["osascript", "-e", apple_script, nmap_executable, subnet]
    try:
        # Leave sudo's prompt visible for the CLI. The GUI never requests this
        # path, so its worker cannot block on an invisible password prompt.
        uses_sudo = command[0] == "sudo"
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=None if uses_sudo else subprocess.PIPE, text=True, check=True)
    except FileNotFoundError as exc:
        raise RuntimeError("Unable to start nmap. Check your installation.") from exc
    except subprocess.CalledProcessError as exc:
        details = (exc.stderr or "").strip() or (exc.stdout or "").strip() or str(exc)
        raise RuntimeError(f"nmap scan failed: {details}") from exc

    hosts = parse_nmap_output(result.stdout)
    return subnet, enrich_hosts_from_neighbors(hosts, subnet=subnet)


def print_hosts_table(hosts):
    headers = ["IP Address", "Device Name", "Status", "Latency", "MAC Address", "Vendor/Device"]
    rows = [[host["ip"], host.get("hostname", "N/A"), host["status"], host["latency"], host["mac"], host["vendor"]] for host in hosts]
    print(tabulate(rows, headers=headers, tablefmt="pretty"))


def main():
    parser = argparse.ArgumentParser(description="Scan the local network with nmap.")
    parser.add_argument("--subnet", help="Override the auto-detected subnet, for example 192.168.1.0/24")
    args = parser.parse_args()

    try:
        subnet, hosts = scan_network(args.subnet, privileged=sys.platform == "darwin")
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    ssid = get_connected_ssid()
    print(f"Wi-Fi SSID: {ssid or 'Unavailable'}")
    if not ssid and sys.platform == "darwin":
        print("SSID access requires Location Services permission for Terminal (or IPHunter).")
    print(f"Scanning subnet: {subnet}\n")
    if hosts:
        print_hosts_table(hosts)
    else:
        print("No active hosts found.")


if __name__ == "__main__":
    main()
