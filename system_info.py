"""
System information utilities.
"""
import platform
import socket


def get_system_info() -> dict:
    """Get system information including OS and hostname."""
    system = platform.system()
    
    if system == "Windows":
        os_name = f"Windows {platform.release()}"
        try:
            # Try to get more detailed Windows version
            version = platform.version()
            if version:
                os_name = f"Windows {platform.release()} ({version})"
        except Exception:
            pass
    elif system == "Linux":
        try:
            # Try to get distribution info
            import distro
            os_name = f"{distro.name()} {distro.version()}"
        except ImportError:
            os_name = f"Linux {platform.release()}"
    elif system == "Darwin":
        os_name = f"macOS {platform.mac_ver()[0]}"
    else:
        os_name = f"{system} {platform.release()}"
    
    return {
        "os": os_name,
        "hostname": socket.gethostname(),
        "platform": system.lower()
    }
