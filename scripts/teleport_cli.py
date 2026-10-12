#!/usr/bin/env python3
"""
Teleport CLI - Headless iOS Location Simulation Tool
Allows listing connected devices, simulating locations, and clearing simulation
without launching the Teleport GUI application.
"""

import argparse
import asyncio
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

SESSION_DIR = Path.home() / ".teleport" / "sessions"


def ensure_session_dir():
    SESSION_DIR.mkdir(parents=True, exist_ok=True)


def get_session_paths(udid: str) -> Tuple[Path, Path]:
    ensure_session_dir()
    clean_id = udid.replace(":", "_").replace("/", "_")
    return SESSION_DIR / f"{clean_id}.sock", SESSION_DIR / f"{clean_id}.json"


def dvt_provider_class():
    try:
        from pymobiledevice3.services.dvt.instruments.dvt_provider import DvtProvider
        return DvtProvider
    except ModuleNotFoundError as error:
        if error.name != "pymobiledevice3.services.dvt.instruments.dvt_provider":
            raise
        from pymobiledevice3.services.dvt.dvt_secure_socket_proxy import DvtSecureSocketProxyService
        return DvtSecureSocketProxyService


async def maybe_await(val):
    import inspect
    if inspect.isawaitable(val):
        return await val
    return val


async def get_service_provider(udid: str):
    """
    Connects to an iOS device without requiring root/sudo privileges:
    1. macOS native remoted tunnel (iOS 17+)
    2. pure-Python userspace PyTCP tunnel (iOS 17+)
    3. lockdown via usbmux (pre-iOS 17)
    """
    # 1. Native tunnel (macOS remoted piggyback, no root, fast)
    try:
        from pymobiledevice3.remote import native_tunnel
        rsd = await maybe_await(native_tunnel.establish_native_rsd(serial=udid))
        if rsd is not None:
            return rsd
    except Exception:
        pass

    # 2. Userspace tunnel (in-process pure-Python PyTCP, no root)
    try:
        from pymobiledevice3.remote import userspace_tunnel
        rsd = await maybe_await(userspace_tunnel.establish_userspace_rsd(serial=udid))
        if rsd is not None:
            return rsd
    except Exception:
        pass

    # 3. Standard lockdown for pre-iOS 17
    from pymobiledevice3.lockdown import create_using_usbmux
    lockdown = await maybe_await(create_using_usbmux(serial=udid, autopair=True))
    return lockdown


async def discover_physical_devices() -> List[Dict]:
    devices = []
    try:
        from pymobiledevice3.usbmux import list_devices
        from pymobiledevice3.lockdown import create_using_usbmux

        mux_devices = await maybe_await(list_devices())
        for dev in mux_devices:
            transport = "Wi-Fi" if dev.connection_type == "Network" else "USB"
            record = {
                "id": dev.serial,
                "name": dev.serial,
                "type": "physical",
                "transport": transport,
                "connection_type": dev.connection_type,
                "os_version": "iOS",
                "is_available": True
            }
            try:
                ld = await asyncio.wait_for(
                    maybe_await(create_using_usbmux(serial=dev.serial, connection_type=dev.connection_type, autopair=True)),
                    timeout=2.0
                )
                if ld:
                    record["name"] = ld.display_name or ld.all_values.get("DeviceName", dev.serial)
                    record["os_version"] = f"iOS {ld.product_version}"
                    if hasattr(ld, "close"):
                        await maybe_await(ld.close())
            except Exception:
                pass
            devices.append(record)
    except Exception as e:
        pass
    return devices


def discover_simulators() -> List[Dict]:
    sims = []
    try:
        proc = subprocess.run(
            ["xcrun", "simctl", "list", "devices", "available", "-j"],
            capture_args=True,
            text=True,
            timeout=3,
            check=False
        )
        if proc.returncode == 0:
            data = json.loads(proc.stdout)
            for runtime, device_list in data.get("devices", {}).items():
                os_name = runtime.split(".")[-1].replace("-", " ")
                for dev in device_list:
                    if dev.get("isAvailable"):
                        sims.append({
                            "id": dev.get("udid"),
                            "name": dev.get("name"),
                            "type": "simulator",
                            "transport": "Simulator",
                            "state": dev.get("state"),
                            "os_version": os_name,
                            "is_available": True
                        })
    except Exception:
        pass
    return sims


def load_saved_locations() -> List[Dict]:
    """
    Reads saved locations from Teleport's macOS UserDefaults (com.samuelhe.Teleport).
    Returns a list of dicts with keys: 'name', 'latitude', 'longitude', 'id', 'created_at'.
    """
    import plistlib
    raw_list = None

    # 1. Try 'defaults export' for real-time cfprefsd synchronization
    try:
        proc = subprocess.run(
            ["defaults", "export", "com.samuelhe.Teleport", "-"],
            capture_output=True,
            check=True
        )
        data = plistlib.loads(proc.stdout)
        if "savedLocations" in data:
            raw_val = data["savedLocations"]
            if isinstance(raw_val, (bytes, bytearray)):
                raw_list = json.loads(raw_val)
            elif isinstance(raw_list, list):
                raw_list = raw_val
    except Exception:
        pass

    # 2. Fallback to direct plist file reading
    if raw_list is None:
        pref_path = Path.home() / "Library" / "Preferences" / "com.samuelhe.Teleport.plist"
        if pref_path.exists():
            try:
                with open(pref_path, "rb") as f:
                    data = plistlib.load(f)
                if "savedLocations" in data:
                    raw_val = data["savedLocations"]
                    if isinstance(raw_val, (bytes, bytearray)):
                        raw_list = json.loads(raw_val)
                    elif isinstance(raw_val, list):
                        raw_list = raw_val
            except Exception:
                pass

    if not raw_list:
        return []

    results = []
    for item in raw_list:
        if not isinstance(item, dict):
            continue
        coord = item.get("coordinate", {})
        lat = coord.get("latitude") if isinstance(coord, dict) else item.get("latitude")
        lng = coord.get("longitude") if isinstance(coord, dict) else item.get("longitude")
        if lat is None or lng is None:
            continue
        results.append({
            "id": str(item.get("id", "")),
            "name": str(item.get("name", "Unnamed")),
            "latitude": float(lat),
            "longitude": float(lng),
            "created_at": item.get("createdAt")
        })
    return results


def find_saved_location(query: str) -> Tuple[Optional[Dict], List[Dict]]:
    """
    Finds a saved location matching the query.
    Matches in order:
      1. Exact name match
      2. Case-insensitive exact match
      3. Case-insensitive substring match
    Returns (best_match_or_none, all_candidates)
    """
    locations = load_saved_locations()
    if not locations:
        return None, []

    # 1. Exact match
    for loc in locations:
        if loc["name"] == query:
            return loc, [loc]

    # 2. Case-insensitive exact match
    q_lower = query.strip().lower()
    exact_ci = [loc for loc in locations if loc["name"].lower() == q_lower]
    if len(exact_ci) == 1:
        return exact_ci[0], exact_ci

    # 3. Substring match
    substr_matches = [loc for loc in locations if q_lower in loc["name"].lower()]
    if len(substr_matches) == 1:
        return substr_matches[0], substr_matches
    elif len(substr_matches) > 1:
        return None, substr_matches

    return None, []


def send_daemon_command(sock_path: Path, command: str) -> Optional[str]:
    import socket
    if not sock_path.exists():
        return None
    try:
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client.settimeout(3.0)
        client.connect(str(sock_path))
        client.sendall((command.strip() + "\n").encode("utf-8"))
        response = client.recv(1024).decode("utf-8").strip()
        client.close()
        return response
    except Exception:
        return None


def get_active_session_info(udid: str) -> Optional[Dict]:
    sock_path, info_path = get_session_paths(udid)
    if not info_path.exists():
        return None
    try:
        with open(info_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        pid = data.get("pid")
        if pid and is_pid_alive(pid):
            return data
        else:
            # Stale session file cleanup
            info_path.unlink(missing_ok=True)
            sock_path.unlink(missing_ok=True)
    except Exception:
        pass
    return None


def is_pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


# ---------------- Daemon Implementation ----------------

async def run_daemon(udid: str, device_name: str, initial_lat: float, initial_lng: float, loc_name: Optional[str]):
    sock_path, info_path = get_session_paths(udid)
    sock_path.unlink(missing_ok=True)

    from pymobiledevice3.services.dvt.instruments.location_simulation import LocationSimulation

    DvtProvider = dvt_provider_class()
    provider = await get_service_provider(udid)

    current_lat = initial_lat
    current_lng = initial_lng
    current_name = loc_name or ""
    running = True

    def save_state(status="simulating"):
        with open(info_path, "w", encoding="utf-8") as f:
            json.dump({
                "udid": udid,
                "device_name": device_name,
                "latitude": current_lat,
                "longitude": current_lng,
                "name": current_name,
                "status": status,
                "pid": os.getpid(),
                "started_at": time.time()
            }, f, indent=2)

    async with DvtProvider(provider) as dvt:
        sim = LocationSimulation(dvt)
        if hasattr(sim, "connect"):
            await maybe_await(sim.connect())

        await maybe_await(sim.clear())
        await maybe_await(sim.set(current_lat, current_lng))
        save_state("simulating")

        async def handle_client(reader, writer):
            nonlocal current_lat, current_lng, current_name, running
            data = await reader.readline()
            if not data:
                writer.close()
                return
            cmd = data.decode("utf-8").strip()
            parts = cmd.split(maxsplit=3)
            action = parts[0].upper() if parts else ""

            if action == "SET" and len(parts) >= 3:
                try:
                    current_lat = float(parts[1])
                    current_lng = float(parts[2])
                    current_name = parts[3] if len(parts) > 3 else ""
                    await maybe_await(sim.set(current_lat, current_lng))
                    save_state("simulating")
                    writer.write(b"OK\n")
                except Exception as ex:
                    writer.write(f"ERR {ex}\n".encode("utf-8"))
            elif action == "CLEAR":
                try:
                    await maybe_await(sim.clear())
                    save_state("cleared")
                    writer.write(b"OK\n")
                except Exception as ex:
                    writer.write(f"ERR {ex}\n".encode("utf-8"))
            elif action == "STOP":
                try:
                    await maybe_await(sim.clear())
                    writer.write(b"OK\n")
                finally:
                    running = False
            elif action == "STATUS":
                writer.write(f"{current_lat},{current_lng},{current_name}\n".encode("utf-8"))
            else:
                writer.write(b"ERR Unknown command\n")

            await writer.drain()
            writer.close()

        server = await asyncio.start_unix_server(handle_client, path=str(sock_path))

        loop = asyncio.get_running_loop()
        stop_event = asyncio.Event()

        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, stop_event.set)
            except NotImplementedError:
                pass

        while running and not stop_event.is_set():
            await asyncio.sleep(0.5)

        server.close()
        await server.wait_closed()
        try:
            await maybe_await(sim.clear())
        except Exception:
            pass

    if hasattr(provider, "close"):
        try:
            await maybe_await(provider.close())
        except Exception:
            pass

    sock_path.unlink(missing_ok=True)
    info_path.unlink(missing_ok=True)


# ---------------- CLI Command Handlers ----------------

def cmd_devices(args):
    physical = asyncio.run(discover_physical_devices())
    simulators = discover_simulators()
    all_devs = physical + simulators

    if args.json:
        print(json.dumps(all_devs, indent=2, ensure_ascii=False))
        return

    if not all_devs:
        print("No iOS devices or simulators found.")
        print("Tip: Connect your iPhone via USB/Wi-Fi or launch an iOS Simulator.")
        return

    print("=== Connected iOS Devices & Simulators ===")
    for dev in all_devs:
        dev_type = "Physical" if dev["type"] == "physical" else "Simulator"
        info = f"{dev['name']} ({dev['os_version']}, {dev['transport']})"
        active_sess = get_active_session_info(dev["id"])
        status_suffix = ""
        if active_sess:
            status_suffix = f" [Mocking: {active_sess['latitude']:.4f}, {active_sess['longitude']:.4f}]"
        print(f" • [{dev_type}] {dev['id']} - {info}{status_suffix}")


def resolve_target_device(device_arg: Optional[str]) -> Tuple[Dict, bool]:
    physical = asyncio.run(discover_physical_devices())
    simulators = discover_simulators()
    all_devs = physical + simulators

    if not all_devs:
        print("Error: No iOS devices or simulators connected.", file=sys.stderr)
        sys.exit(1)

    if device_arg:
        # Match by UDID or name substring
        for dev in all_devs:
            if dev["id"].lower() == device_arg.lower() or device_arg.lower() in dev["name"].lower():
                return dev, (dev["type"] == "simulator")
        print(f"Error: Device '{device_arg}' not found among connected devices.", file=sys.stderr)
        sys.exit(1)

    # If no target specified and exactly one physical device is connected, pick it
    if len(physical) == 1:
        return physical[0], False
    elif len(physical) > 1:
        # Pick USB over Wi-Fi if same device is listed twice
        usb_devices = [d for d in physical if d.get("transport") == "USB"]
        if len(usb_devices) == 1:
            return usb_devices[0], False
        print("Error: Multiple devices connected. Please specify one with --device <udid>:", file=sys.stderr)
        for d in physical:
            print(f"  • {d['id']} ({d['name']}, {d['transport']})", file=sys.stderr)
        sys.exit(1)
    elif len(simulators) == 1:
        return simulators[0], True
    else:
        print("Error: Multiple devices available. Please specify --device <udid>.", file=sys.stderr)
        sys.exit(1)


def cmd_locations(args):
    locations = load_saved_locations()
    if args.json:
        print(json.dumps(locations, indent=2, ensure_ascii=False))
        return

    if not locations:
        print("No saved locations found.")
        print("Tip: Add favorite locations in the Teleport GUI app.")
        return

    print("=== Teleport Saved Locations ===")
    for idx, loc in enumerate(locations, 1):
        print(f" {idx}. {loc['name']}: {loc['latitude']}, {loc['longitude']}")


def cmd_connect(args):
    device, is_simulator = resolve_target_device(args.device)
    udid = device["id"]
    name = device["name"]
    dev_type = "Physical" if device["type"] == "physical" else "Simulator"

    if not args.json:
        print(f"Testing connection to [{dev_type}] '{name}' ({udid})...")

    if is_simulator:
        status_info = {
            "id": udid,
            "name": name,
            "type": "simulator",
            "state": device.get("state", "Unknown"),
            "connected": True
        }
        if args.json:
            print(json.dumps(status_info, indent=2, ensure_ascii=False))
        else:
            print(f"✓ Simulator is ready: {name} ({device.get('state', 'Unknown')})")
            print("  Note: Location simulation connects automatically when running 'teleport set'.")
        return

    async def do_connect():
        t0 = time.time()
        provider = await get_service_provider(udid)
        tunnel_type = type(provider).__name__
        DvtProvider = dvt_provider_class()
        async with DvtProvider(provider) as dvt:
            from pymobiledevice3.services.dvt.instruments.location_simulation import LocationSimulation
            sim = LocationSimulation(dvt)
            if hasattr(sim, "connect"):
                await maybe_await(sim.connect())
            elapsed = time.time() - t0
            return {
                "id": udid,
                "name": name,
                "type": "physical",
                "transport": device.get("transport", "USB"),
                "os_version": device.get("os_version", "iOS"),
                "tunnel_provider": tunnel_type,
                "latency_seconds": round(elapsed, 2),
                "connected": True
            }

    try:
        res = asyncio.run(do_connect())
        if args.json:
            print(json.dumps(res, indent=2, ensure_ascii=False))
        else:
            print(f"✓ Connected successfully to '{name}'!")
            print(f"  • UDID: {udid}")
            print(f"  • OS: {res['os_version']}")
            print(f"  • Transport: {res['transport']}")
            print(f"  • Tunnel Provider: {res['tunnel_provider']}")
            print(f"  • Handshake Latency: {res['latency_seconds']}s")
            print("  Note: Normal 'teleport set' commands connect automatically without needing this step.")
    except Exception as ex:
        if args.json:
            print(json.dumps({"id": udid, "name": name, "connected": False, "error": str(ex)}, indent=2))
        else:
            print(f"✗ Connection failed to '{name}': {ex}", file=sys.stderr)
        sys.exit(1)


def cmd_set(args):
    device, is_simulator = resolve_target_device(args.device)
    udid = device["id"]
    name = device["name"]

    target = args.target.strip()
    target_is_lat = False
    lat_val = None

    try:
        lat_val = float(target)
        target_is_lat = True
    except ValueError:
        target_is_lat = False

    if target_is_lat and args.longitude is not None:
        lat = lat_val
        lng = float(args.longitude)
        loc_name = args.name or ""
    elif not target_is_lat:
        # User passed a location name or keyword (e.g. "工作打卡")
        matched_loc, candidates = find_saved_location(target)
        if matched_loc:
            lat = matched_loc["latitude"]
            lng = matched_loc["longitude"]
            loc_name = args.name or matched_loc["name"]
        else:
            if candidates:
                print(f"Error: Ambiguous location query '{target}'. Multiple saved locations matched:", file=sys.stderr)
                for c in candidates:
                    print(f"  • {c['name']} ({c['latitude']}, {c['longitude']})", file=sys.stderr)
            else:
                saved = load_saved_locations()
                print(f"Error: Location '{target}' not found in saved favorites.", file=sys.stderr)
                if saved:
                    print("Available saved locations in Teleport:", file=sys.stderr)
                    for s in saved:
                        print(f"  • {s['name']} ({s['latitude']}, {s['longitude']})", file=sys.stderr)
                else:
                    print("Tip: No saved locations found in Teleport yet. You can add favorites in Teleport app or pass coordinates directly.", file=sys.stderr)
            sys.exit(1)
    else:
        # target is float, but longitude is missing
        print(f"Error: Longitude is required when latitude ({lat_val}) is provided.", file=sys.stderr)
        print("Usage:", file=sys.stderr)
        print("  teleport set <latitude> <longitude> [-n <name>]", file=sys.stderr)
        print("  teleport set <location_name_from_favorites>", file=sys.stderr)
        sys.exit(1)

    if is_simulator:
        # Simulate via simctl
        cmd = ["xcrun", "simctl", "location", udid, "set", f"{lat},{lng}"]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            print(f"Error setting simulator location: {proc.stderr.strip()}", file=sys.stderr)
            sys.exit(1)
        print(f"✓ Location set on Simulator '{name}': {lat}, {lng}" + (f" ({loc_name})" if loc_name else ""))
        return

    sock_path, info_path = get_session_paths(udid)

    # 1. If foreground hold requested
    if args.hold:
        # Stop existing background daemon if running
        send_daemon_command(sock_path, "STOP")
        print(f"Simulating location on '{name}' ({udid}): {lat}, {lng}" + (f" ({loc_name})" if loc_name else ""))
        print("Holding simulation session. Press Ctrl+C to stop...")
        try:
            asyncio.run(run_daemon(udid, name, lat, lng, loc_name))
        except KeyboardInterrupt:
            print("\nSimulation stopped.")
        return

    # 2. Check if a background daemon is already running for this device
    active = get_active_session_info(udid)
    if active and sock_path.exists():
        resp = send_daemon_command(sock_path, f"SET {lat} {lng} {loc_name}")
        if resp == "OK":
            print(f"✓ Updated simulated location for '{name}':")
            print(f"  Coordinates: {lat}, {lng}" + (f" ({loc_name})" if loc_name else ""))
            print(f"  Session PID: {active.get('pid')} (Running in background)")
            return

    # 3. Spawn background daemon
    sock_path.unlink(missing_ok=True)
    info_path.unlink(missing_ok=True)

    cmd = [
        sys.executable,
        os.path.abspath(__file__),
        "_daemon",
        udid,
        name,
        str(lat),
        str(lng),
        loc_name
    ]

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True
    )

    # Wait for daemon to initialize and create socket
    ready = False
    for _ in range(50):
        time.sleep(0.1)
        if sock_path.exists() and info_path.exists():
            ready = True
            break
        if not is_pid_alive(proc.pid):
            break

    if ready:
        print(f"✓ Successfully simulated location for '{name}':")
        print(f"  Device UDID: {udid}")
        print(f"  Coordinates: {lat}, {lng}" + (f" ({loc_name})" if loc_name else ""))
        print(f"  Background PID: {proc.pid}")
        print("  To restore original location: teleport clear")
    else:
        print(f"Error: Failed to start background simulation session for {name}.", file=sys.stderr)
        sys.exit(1)


def cmd_clear(args):
    device, is_simulator = resolve_target_device(args.device)
    udid = device["id"]
    name = device["name"]

    if is_simulator:
        cmd = ["xcrun", "simctl", "location", udid, "clear"]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            print(f"Error clearing simulator location: {proc.stderr.strip()}", file=sys.stderr)
            sys.exit(1)
        print(f"✓ Location simulation cleared for Simulator '{name}'.")
        return

    sock_path, info_path = get_session_paths(udid)
    active = get_active_session_info(udid)

    # Stop active daemon if present
    if active or sock_path.exists():
        send_daemon_command(sock_path, "STOP")
        time.sleep(0.3)
        if active and is_pid_alive(active.get("pid")):
            try:
                os.kill(active["pid"], signal.SIGTERM)
            except Exception:
                pass
        sock_path.unlink(missing_ok=True)
        info_path.unlink(missing_ok=True)

    # Also perform a one-shot DVT clear to guarantee device location reset
    async def oneshot_clear():
        from pymobiledevice3.services.dvt.instruments.location_simulation import LocationSimulation
        DvtProvider = dvt_provider_class()
        provider = await get_service_provider(udid)
        async with DvtProvider(provider) as dvt:
            sim = LocationSimulation(dvt)
            if hasattr(sim, "connect"):
                await maybe_await(sim.connect())
            await maybe_await(sim.clear())
        if hasattr(provider, "close"):
            try:
                await maybe_await(provider.close())
            except Exception:
                pass

    try:
        asyncio.run(oneshot_clear())
    except Exception:
        pass

    print(f"✓ Location simulation stopped for '{name}'. Real GPS location restored.")


def cmd_status(args):
    active_sessions = []
    ensure_session_dir()
    for json_file in SESSION_DIR.glob("*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            pid = data.get("pid")
            if pid and is_pid_alive(pid):
                active_sessions.append(data)
            else:
                json_file.unlink(missing_ok=True)
                sock = json_file.with_suffix(".sock")
                sock.unlink(missing_ok=True)
        except Exception:
            pass

    if args.json:
        print(json.dumps(active_sessions, indent=2, ensure_ascii=False))
        return

    if not active_sessions:
        print("No active location simulation sessions.")
        return

    print("=== Active Simulation Sessions ===")
    for s in active_sessions:
        started = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(s.get("started_at", time.time())))
        loc_str = f"{s['latitude']}, {s['longitude']}"
        if s.get("name"):
            loc_str += f" ({s['name']})"
        print(f" • Device: {s['device_name']} ({s['udid']})")
        print(f"   Location: {loc_str}")
        print(f"   Status: {s['status']} | PID: {s['pid']} | Started: {started}")


def main():
    parser = argparse.ArgumentParser(
        prog="teleport",
        description="Teleport CLI: Command-line iOS location simulation tool"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # devices
    p_dev = subparsers.add_parser("devices", aliases=["list"], help="List connected iOS devices and simulators")
    p_dev.add_argument("--json", action="store_true", help="Output in JSON format")

    # locations
    p_loc = subparsers.add_parser("locations", aliases=["favorites", "saved"], help="List saved favorite locations from Teleport")
    p_loc.add_argument("--json", action="store_true", help="Output in JSON format")

    # connect
    p_conn = subparsers.add_parser("connect", aliases=["test"], help="Test and verify connection to an iOS device or simulator")
    p_conn.add_argument("-d", "--device", type=str, help="Device UDID or name (auto-selected if only 1 device)")
    p_conn.add_argument("--json", action="store_true", help="Output in JSON format")

    # set
    p_set = subparsers.add_parser("set", help="Simulate location by coordinates or favorite name")
    p_set.add_argument("target", help="Location name (from favorites, e.g. '工作打卡') or latitude (e.g. 34.7856)")
    p_set.add_argument("longitude", nargs="?", type=float, default=None, help="Longitude (required if target is latitude)")
    p_set.add_argument("-d", "--device", type=str, help="Device UDID or name (auto-selected if only 1 device)")
    p_set.add_argument("-n", "--name", type=str, help="Human-readable location name (e.g. 'Beijing')")
    p_set.add_argument("--hold", action="store_true", help="Hold simulation in foreground (stop with Ctrl+C)")

    # clear
    p_clear = subparsers.add_parser("clear", help="Clear simulated location and restore real GPS")
    p_clear.add_argument("-d", "--device", type=str, help="Device UDID or name")

    # status
    p_status = subparsers.add_parser("status", help="Show active simulation sessions")
    p_status.add_argument("--json", action="store_true", help="Output in JSON format")

    # internal daemon
    p_daemon = subparsers.add_parser("_daemon", help=argparse.SUPPRESS)
    p_daemon.add_argument("udid")
    p_daemon.add_argument("name")
    p_daemon.add_argument("lat", type=float)
    p_daemon.add_argument("lng", type=float)
    p_daemon.add_argument("loc_name", nargs="?", default="")

    args = parser.parse_args()

    if args.command == "_daemon":
        asyncio.run(run_daemon(args.udid, args.name, args.lat, args.lng, args.loc_name))
        return

    if args.command in ("devices", "list"):
        cmd_devices(args)
    elif args.command in ("locations", "favorites", "saved"):
        cmd_locations(args)
    elif args.command in ("connect", "test"):
        cmd_connect(args)
    elif args.command == "set":
        cmd_set(args)
    elif args.command == "clear":
        cmd_clear(args)
    elif args.command == "status":
        cmd_status(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
