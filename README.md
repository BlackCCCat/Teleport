<div align="center">
  <img src="Resources/teleport-icon.webp" alt="Teleport app icon" width="200"/>

  <h1>Teleport</h1>

  <p>Simulate iOS device locations from your Mac, on simulators and physical devices over USB or Wi-Fi.</p>

  <p>
    <img src="https://img.shields.io/badge/platform-macOS-34C759" alt="macOS app" />
    <img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT License" />
    <a href="https://github.com/BlackCCCat/Teleport/releases/latest"><img src="https://img.shields.io/badge/Download-Latest%20release-007AFF?logo=apple&logoColor=white" alt="Download the latest Teleport release" /></a>
  </p>

  <p><a href="README.zh-CN.md">简体中文</a> · <a href="#install">Install</a></p>
</div>

---

> [!NOTE]
> **Fork Differences / Improvements:**
> This fork is based on [samuelhe52/Teleport](https://github.com/samuelhe52/Teleport).
> - **Xcode Environment Toggle**: Added a toggle switch in the left sidebar to enable/disable Xcode environment dependency. When turned off, physical devices (USB & Wi-Fi) are discovered and connected purely via `pymobiledevice3`, allowing location simulation **without needing Xcode or `xcrun devicectl` installed**.
> - **Passwordless Simulation (No Sudo/Touch ID Prompt)**: Added a toggle to run location simulation rootless. Using native/userspace tunnels, device location can be simulated immediately without prompting for administrator password or Touch ID every time.
> - **Headless CLI & AI Skill (`teleport`)**: Standalone command-line tool (`teleport devices`, `teleport locations`, `teleport set <name|lat lng>`, `teleport connect`, `teleport clear`) that works without opening the GUI app, reading favorite places directly and supporting automated control by scripts and AI agents.
> - **Persistent State**: Toggle states are remembered across application restarts (`UserDefaults`).
> - **Automated Release**: Added GitHub Actions workflow to automatically package and attach macOS `.dmg` and `.zip` bundles on GitHub Release.

Teleport is built with SwiftUI and MapKit. Click somewhere on the map, hit Simulate, and your device thinks it's there.

![Teleport – location simulation](Resources/screenshot-main.jpg)

![Teleport – route builder](Resources/screenshot-route.jpg)

## Install

### Direct download

Download the latest `.dmg` from [Releases](https://github.com/BlackCCCat/Teleport/releases), drag `Teleport.app` to Applications, and launch it.

## What It Does

**Full device support** — works with iOS Simulators and real iPhones over USB or Wi-Fi, all from the same app.

**Virtual joystick** — move the simulated location around in real time without picking a new point every time. Good for testing location-aware interactions on the fly.

**Custom routes** — draw a straight-line path between any stops, or use Apple Maps navigation to snap the route to real roads. Both can be played back at fixed intervals, or a target travel speed. Save/load/edit routes are fully supported.

**GPX import and export** — bring in existing routes or save yours out for use elsewhere.

A few other things:

- Click anywhere on the map, search by name, or type in coordinates to set a location
- Save routes inside the app and reload, rename, edit, or duplicate them later
- Session controls show clear status and let you stop or reset at any point

## Disclaimer

Teleport is meant for developer testing and debugging. Using it for anything else is on you — the app and its developer aren't responsible for whatever happens.

## Requirements

- macOS
- Xcode installed and opened at least once (so `xcrun`, `simctl`, and `devicectl` are on your path)
- For physical devices: Developer Mode enabled on the iPhone, plus `python3` and `pymobiledevice3 >= 5.0`
- For Wi-Fi: pair over USB first, then keep the device unlocked on the same network

If macOS says developer tools are missing:

```sh
xcode-select --install
```

If `xcrun` is pointing at the wrong Xcode install:

```sh
sudo xcode-select -s /Applications/Xcode.app/Contents/Developer
```

Then open Xcode once to let it finish setup.

Install or upgrade the Python dependency with whichever `python3` your shell resolves:

```sh
python3 -m pip install --upgrade pymobiledevice3
```

Teleport requires `pymobiledevice3` 5.0 or newer for physical-device simulation.

## Build from Source

### Xcode

1. Open `Teleport.xcodeproj`.
2. Select the `Teleport` scheme.
3. Build and run.

### Command line

```sh
xcodebuild -project Teleport.xcodeproj -scheme Teleport -destination 'platform=macOS' build
```

## Basic Usage

1. Launch Teleport and select a device.
2. Connect to it.
3. Pick a location — click the map, search, or enter coordinates.
4. Hit `Simulate`. That's it.
5. Build a route if you need to simulate movement.
6. Save routes for later, or import/export GPX files.
7. Hit `Stop` when you're done.

For physical devices, Teleport might ask for admin approval on first run, walk you through a missing Python dependency, or need a USB connection before Wi-Fi discovery kicks in.

## Command Line Interface (CLI)

Teleport provides a headless CLI tool to control location simulation without opening the GUI application:

```sh
# Symlink CLI to your PATH (if not already done)
ln -sf $(pwd)/bin/teleport ~/.local/bin/teleport

# 1. List connected iOS devices & simulators
teleport devices

# 2. Test device connection & tunnel health
teleport connect

# 3. List saved favorite locations (from Teleport app)
teleport locations

# 4. Simulate location (auto-connects device, no sudo required)
teleport set "工作打卡"                     # by favorite name
teleport set 39.9042 116.4074 --name "北京" # by coordinates

# 5. Check active simulation status
teleport status

# 6. Clear simulation and restore real GPS
teleport clear
```

## Development

- `make format` runs `swift format -r -p -i .`
- `make lint` runs `swift format lint -r -p .`

## Notes

Teleport was originally called iOSAnywhere.

If you're in mainland China, Apple Maps search tends to only return locations inside China. Searching for overseas places usually needs a VPN. You can still pan the map to anywhere and pick a spot manually.
