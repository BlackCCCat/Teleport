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
> - **Xcode Environment Toggle**: Added a toggle switch in the left sidebar to enable/disable Xcode environment dependency. When turned off, physical devices (USB & Wi-Fi) are discovered and connected purely via `pymobiledevice3`, allowing location simulation **without needing Xcode or `xcrun devicectl` installed**.
> - **Passwordless / Rootless Simulation**: Added a toggle to run location simulation rootless. Using native/userspace tunnels, device location can be simulated immediately without prompting for administrator password or Touch ID every time.
> - **Headless CLI Tool (`teleport`)**: Standalone command-line tool that operates without opening the GUI application, perfect for scripts, terminal lovers, and automation pipelines.
> - **Zero-Config Auto Connection & Health Checks**: Running `teleport set` automatically discovers connected devices and establishes the DVT tunnel in the background. An explicit `teleport connect` command is also available for connectivity and latency diagnostics.
> - **Direct GUI Favorites Synchronization**: CLI directly reads user favorite places saved in the macOS app (`teleport locations`) and allows simulating location by name (`teleport set "工作打卡"` or `teleport set "Office"`), supporting fuzzy search.
> - **AI Agent Integration**: Preconfigured AI Skill (`teleport-location`) enabling conversational AI to check status, pick favorites, and teleport devices hands-free.
> - **Persistent Preferences**: Toggle states are remembered across application restarts (`UserDefaults`).
> - **Automated Release**: GitHub Actions workflow automatically packages and attaches notarized/clean macOS `.dmg` and `.zip` bundles on GitHub Release.

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

Teleport includes a powerful, headless CLI tool (`teleport`) that allows full location simulation control without opening the GUI application. It runs in user space without requiring administrator passwords, automatically connects devices, and can be driven by terminal commands or AI agents.

### Setup

Symlink the CLI tool to your `PATH`:

```sh
ln -sf $(pwd)/bin/teleport ~/.local/bin/teleport
```

### Quick Start & Common Workflows

#### 1. Device Discovery & Health Check
```sh
# List all connected physical devices and iOS Simulators
teleport devices
teleport devices --json

# Test handshake connectivity and tunnel latency
teleport connect
```
*Note: If only one device is connected, `teleport` automatically selects it for all operations.*

#### 2. Saved Favorites & Named Simulation
The CLI directly synchronizes with favorites configured in the Teleport macOS app:

```sh
# View all saved favorite locations
teleport locations
teleport locations --json

# Simulate location by favorite place name (supports exact & fuzzy matching)
teleport set "工作打卡"
teleport set "Apple Park"
teleport set "公司"
```

#### 3. Coordinate-Based Simulation
```sh
# Teleport to Beijing Palace Museum (Forbidden City)
teleport set 39.9163 116.3972 --name "Forbidden City"

# Teleport to Shanghai The Bund
teleport set 31.2400 121.4900 --name "The Bund"

# Target a specific device (if multiple are connected)
teleport set 37.3349 -122.0090 --device 00008140-001E0C291E33001C --name "Apple Park"
```
*Behind the scenes: The first `set` command launches an invisible background daemon. Subsequent location updates switch instantly in `< 0.1s` without reconnecting.*

#### 4. Session Monitoring & Reset
```sh
# Check current active simulation session and coordinates
teleport status

# Stop simulation and restore genuine GPS
teleport clear
```

### CLI Command Summary

| Command | Description |
| :--- | :--- |
| `teleport devices` | List connected physical devices and active simulators |
| `teleport connect` | Test and verify connection health and tunnel latency (`--json`) |
| `teleport locations` | List saved favorite places from Teleport GUI (`--json`) |
| `teleport set <name>` | **Simulate location directly by favorite place name** |
| `teleport set <lat> <lng>` | Simulate location by latitude and longitude |
| `teleport status` | Display active background simulation sessions |
| `teleport clear` | Clear simulated location and restore real GPS positioning |

### AI Agent Skill Integration

Teleport provides an AI skill (`teleport-location`) for agentic assistants. An AI agent can inspect your favorites, check connected devices, and change your iPhone's location through natural conversation (e.g., *"Change my location to my saved office bookmark"*).

## Development

- `make format` runs `swift format -r -p -i .`
- `make lint` runs `swift format lint -r -p .`

## Notes

Teleport was originally called iOSAnywhere.

If you're in mainland China, Apple Maps search tends to only return locations inside China. Searching for overseas places usually needs a VPN. You can still pan the map to anywhere and pick a spot manually.
