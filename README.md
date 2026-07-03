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
- `sudo` access on macOS/Linux when required by your local `nmap` setup

## Install

```bash
git clone https://github.com/01himanshugautam/IPHunter
cd IPHunter
python -m pip install -r requirements.txt
```

Install `nmap` separately:

- macOS: `brew install nmap`
- Windows: install from `https://nmap.org/download.html` and ensure `nmap` is on `PATH`

## Run the CLI

```bash
python main.py
python main.py --subnet 192.168.1.0/24
```

## Run the GUI

```bash
python gui.py
```

The GUI lets you detect the current subnet, start a scan, and review results in a desktop table.

## Build Desktop Binaries

Use PyInstaller on each target OS:

```bash
pyinstaller --noconfirm --windowed --name IPHunter gui.py
```

Output:

- macOS app bundle: `dist/IPHunter.app`
- Windows executable: `dist/IPHunter/IPHunter.exe`

Build macOS binaries on macOS and Windows binaries on Windows. PyInstaller does not cross-compile between them.
