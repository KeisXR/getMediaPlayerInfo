"""
debug_mpris.py – MPRIS player debug utility for Linux.

Lists all active MPRIS media players found on the D-Bus session bus and
prints their metadata and playback status.

Usage:
    python debug_mpris.py
    python debug_mpris.py --player spotify
    python debug_mpris.py --json
"""
import argparse
import json
import sys

try:
    import dbus
    from dbus.mainloop.glib import DBusGMainLoop
except ImportError:
    print("Error: dbus-python is not installed. Install it with: pip install dbus-python")
    sys.exit(1)


def list_mpris_players(bus: "dbus.SessionBus") -> list[str]:
    """Return a list of MPRIS service names on the session bus."""
    bus_obj = bus.get_object("org.freedesktop.DBus", "/org/freedesktop/DBus")
    names = dbus.Interface(bus_obj, "org.freedesktop.DBus").ListNames()
    return sorted(n for n in names if n.startswith("org.mpris.MediaPlayer2"))


def get_player_info(bus: "dbus.SessionBus", name: str) -> dict:
    """Retrieve metadata and playback status for a single MPRIS player."""
    player = bus.get_object(name, "/org/mpris/MediaPlayer2")
    props = dbus.Interface(player, "org.freedesktop.DBus.Properties")

    metadata = props.Get("org.mpris.MediaPlayer2.Player", "Metadata")
    playback_status = props.Get("org.mpris.MediaPlayer2.Player", "PlaybackStatus")

    meta_dict = {str(k): str(v) for k, v in metadata.items()}
    return {
        "name": name,
        "status": str(playback_status),
        "metadata": meta_dict,
    }


def print_player_info(info: dict) -> None:
    """Pretty-print player info to stdout."""
    print(f"\n--- {info['name']} ---")
    print(f"  Status: {info['status']}")
    print("  Metadata:")
    for key, val in info["metadata"].items():
        print(f"    {key}: {val}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="List and inspect active MPRIS media players on D-Bus.",
    )
    parser.add_argument(
        "--player", "-p",
        metavar="NAME",
        help=(
            "Filter output to a single player. "
            "Accepts a partial name match (e.g. 'spotify' matches "
            "'org.mpris.MediaPlayer2.spotify')."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Output results as JSON instead of human-readable text.",
    )
    args = parser.parse_args()

    try:
        DBusGMainLoop(set_as_default=True)
        bus = dbus.SessionBus()
    except Exception as exc:
        print(f"Error: could not connect to D-Bus session bus: {exc}")
        sys.exit(1)

    service_names = list_mpris_players(bus)

    if args.player:
        service_names = [n for n in service_names if args.player.lower() in n.lower()]

    if not service_names:
        msg = "No MPRIS players found"
        if args.player:
            msg += f" matching '{args.player}'"
        print(msg)
        sys.exit(0)

    results = []
    for name in service_names:
        try:
            info = get_player_info(bus, name)
            results.append(info)
        except Exception as exc:
            results.append({"name": name, "error": str(exc)})

    if args.as_json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print(f"Found {len(results)} MPRIS player(s):")
        for info in results:
            if "error" in info:
                print(f"\n--- {info['name']} ---")
                print(f"  Error: {info['error']}")
            else:
                print_player_info(info)


if __name__ == "__main__":
    main()
