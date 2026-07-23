# IPHunter

IPHunter scans your local subnet with `nmap`, detects active hosts, and shows IP, latency, MAC, and vendor details.

## Features

- Auto-detects the current Wi-Fi/LAN subnet
- CLI scanner for scripting and terminal use
- Desktop GUI for macOS and Windows using Tkinter
- Parses and displays IP, MAC, latency, and vendor/device data

## Requirements

- Python 3.9+
- `nmap` installed and available on `PATH`

IPHunter runs `nmap` without `sudo`, so neither the GUI nor CLI asks for an
administrator password. It enriches scan results from the operating system's
ARP/neighbor cache and resolves vendors with nmap's local MAC-prefix database.
Devices using private/randomized MAC addresses are identified as such.

## Install

```bash
git clone https://github.com/01himanshugautam/IPHunter
cd IPHunter
python -m pip install -r requirements.txt
```

Install `nmap` separately:

- macOS with Homebrew Python 3.13: `brew install nmap python-tk@3.13`
- Windows: install from `https://nmap.org/download.html` and ensure `nmap` is on `PATH`

Use the `python-tk` formula matching your Homebrew Python version (for example,
`python-tk@3.12` for Python 3.12). Tkinter is part of Python's standard library,
but Homebrew ships its native Tk runtime as a separate formula.

## Run the CLI

```bash
python main.py
python main.py --subnet 192.168.1.0/24
```

## Run the GUI

```bash
python gui.py
```

The desktop dashboard lets you:

- Detect or enter a subnet and follow the scan state in real time
- Review active-host and identified-vendor totals at a glance
- Search devices by IP, MAC address, status, latency, or vendor
- Sort results by any column and export the full scan to CSV

## Build Desktop Binaries

Use PyInstaller on each target OS:

```bash
pyinstaller --noconfirm --windowed --name IPHunter gui.py
```

Output:

- macOS app bundle: `dist/IPHunter.app`
- Windows executable: `dist/IPHunter/IPHunter.exe`

Build macOS binaries on macOS and Windows binaries on Windows. PyInstaller does not cross-compile between them.

### macOS installer

On an Apple Silicon Mac, build the application and drag-to-install disk image:

```bash
./scripts/build_macos_dmg.sh
```

The installer is created at `dist/IPHunter-macOS-arm64.dmg`. Open it and drag
IPHunter into the Applications folder. This local build is ad-hoc signed; public
distribution additionally requires an Apple Developer ID signature and notarization.

### Windows installer with GitHub Actions

The included `Build Windows installer` workflow creates an installer on a
Windows runner:

1. Push this repository to GitHub.
2. Open **Actions → Build Windows installer → Run workflow**.
3. When the run finishes, download the **IPHunter-Windows-Installer** artifact.

The installation file is `IPHunter-Setup.exe`. Windows machines still need nmap
installed when running IPHunter.
