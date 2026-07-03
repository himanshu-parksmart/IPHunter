#!/usr/bin/env python3
import argparse
import ipaddress
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


def build_nmap_command(subnet):
    """Build the nmap command for the current platform."""
    command = ["nmap", "-sn", subnet]
    if sys.platform != "win32" and shutil.which("sudo"):
        command.insert(0, "sudo")
    return command


def parse_nmap_output(output):
    """Parse nmap ping-scan output into structured host rows."""
    hosts = []
    current_ip, latency, mac, vendor = None, None, None, None

    for line in output.splitlines():
        if line.startswith("Nmap scan report for"):
            if current_ip:
                hosts.append(
                    {
                        "ip": current_ip,
                        "status": "Up",
                        "latency": latency or "N/A",
                        "mac": mac or "N/A",
                        "vendor": vendor or "N/A",
                    }
                )
            current_ip = line.split()[-1]
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
                "status": "Up",
                "latency": latency or "N/A",
                "mac": mac or "N/A",
                "vendor": vendor or "N/A",
            }
        )

    return hosts


def scan_network(subnet=None):
    """Run a ping scan and return the subnet plus parsed hosts."""
    if not subnet:
        subnet = get_current_subnet()
        if not subnet:
            raise RuntimeError("Could not detect the current subnet.")

    if not shutil.which("nmap"):
        raise RuntimeError("nmap is not installed or not available on PATH.")

    command = build_nmap_command(subnet)
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("Unable to start nmap. Check your installation.") from exc
    except subprocess.CalledProcessError as exc:
        details = exc.stderr.strip() or exc.stdout.strip() or str(exc)
        raise RuntimeError(f"nmap scan failed: {details}") from exc

    return subnet, parse_nmap_output(result.stdout)


def print_hosts_table(hosts):
    headers = ["IP Address", "Status", "Latency", "MAC Address", "Vendor/Device"]
    rows = [[host["ip"], host["status"], host["latency"], host["mac"], host["vendor"]] for host in hosts]
    print(tabulate(rows, headers=headers, tablefmt="pretty"))


def main():
    parser = argparse.ArgumentParser(description="Scan the local network with nmap.")
    parser.add_argument("--subnet", help="Override the auto-detected subnet, for example 192.168.1.0/24")
    args = parser.parse_args()

    try:
        subnet, hosts = scan_network(args.subnet)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    print(f"Scanning subnet: {subnet}\n")
    if hosts:
        print_hosts_table(hosts)
    else:
        print("No active hosts found.")


if __name__ == "__main__":
    main()
