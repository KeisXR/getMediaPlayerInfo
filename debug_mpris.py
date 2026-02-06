import dbus
from dbus.mainloop.glib import DBusGMainLoop

def check_mpris():
    try:
        DBusGMainLoop(set_as_default=True)
        bus = dbus.SessionBus()
        
        # List all names
        bus_obj = bus.get_object("org.freedesktop.DBus", "/org/freedesktop/DBus")
        names = dbus.Interface(bus_obj, "org.freedesktop.DBus").ListNames()
        
        mpris_names = [n for n in names if n.startswith("org.mpris.MediaPlayer2")]
        
        print(f"Found {len(mpris_names)} MPRIS services:")
        
        for name in mpris_names:
            print(f"\n--- {name} ---")
            try:
                player = bus.get_object(name, "/org/mpris/MediaPlayer2")
                props = dbus.Interface(player, "org.freedesktop.DBus.Properties")
                
                # Get Metadata
                metadata = props.Get("org.mpris.MediaPlayer2.Player", "Metadata")
                playback_status = props.Get("org.mpris.MediaPlayer2.Player", "PlaybackStatus")
                
                print(f"Status: {playback_status}")
                print("Metadata:")
                for key, val in metadata.items():
                    print(f"  {key}: {val}")
                    
            except Exception as e:
                print(f"  Error reading properties: {e}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_mpris()
