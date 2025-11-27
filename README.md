# CS FiveM Management Tool

A desktop tool by **Covex Studios** to manage multiple FiveM FXServer / txAdmin profiles.

## Features

- Manage multiple servers (dev, live, test, etc.)
- Auto-generate server `.bat` files
- Start / stop / restart servers
- CLI commands:
  - `csservers list`
  - `csservers start <name_or_key>`
  - `csservers stop <name_or_key>`
  - `csservers restart <name_or_key>`
- Auto-update check with one-click installer download

<img width="951" height="575" alt="image" src="https://github.com/user-attachments/assets/eb81ff5f-9dee-4974-bd20-76ecad0270f5" />

## Installation

1. Download the latest `CSFiveMToolSetup.exe` from the [Releases](https://github.com/Covex-Studios/CSFiveMTool/releases) page.
2. Run the installer.
3. (Recommended) Keep **"Add csservers to PATH"** checked.

After install, you can run:

```powershell
csservers
csservers list
csservers start dev-server
```

## Configuration

Inside the GUI:

Key – short name, e.g. dev or dev-server

Display name – friendly name for the server

FXServer folder – folder that contains FXServer.exe (e.g. D:\FiveM-Servers\FX-Servers\covex-dev\atifact)

TXAdmin profile – profile name without .base (e.g. covex-studios)

The tool will automatically generate <key>.bat in your FXServer folder.
