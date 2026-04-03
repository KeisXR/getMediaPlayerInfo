"""
macOS media provider using MediaRemote.framework (private API).

Reads Now Playing information from the system-level Now Playing session,
which aggregates data from all media apps (Music, Spotify, browsers, etc.).
"""
import asyncio
import ctypes
import platform
import threading
from typing import Optional

from .base import MediaProvider, MediaInfo, PlaybackStatus

# ---------------------------------------------------------------------------
# MediaRemote key constants (string keys used in the NowPlaying info dict)
# ---------------------------------------------------------------------------
_KEY_TITLE = "kMRMediaRemoteNowPlayingInfoTitle"
_KEY_ARTIST = "kMRMediaRemoteNowPlayingInfoArtist"
_KEY_ALBUM = "kMRMediaRemoteNowPlayingInfoAlbum"
_KEY_PLAYBACK_RATE = "kMRMediaRemoteNowPlayingInfoPlaybackRate"
_KEY_ELAPSED_TIME = "kMRMediaRemoteNowPlayingInfoElapsedTime"
_KEY_DURATION = "kMRMediaRemoteNowPlayingInfoDuration"

# ---------------------------------------------------------------------------
# Objective-C block ABI helpers
# ---------------------------------------------------------------------------

# BLOCK_IS_GLOBAL flag (no stack / heap copy needed)
_BLOCK_IS_GLOBAL = 1 << 28

# Block descriptor (required by the ABI)
class _BlockDescriptor(ctypes.Structure):
    _fields_ = [
        ("reserved", ctypes.c_ulong),
        ("size", ctypes.c_ulong),
    ]


# Block literal (the in-memory representation of an ObjC block)
class _BlockLiteral(ctypes.Structure):
    _fields_ = [
        ("isa", ctypes.c_void_p),
        ("flags", ctypes.c_int),
        ("reserved", ctypes.c_int),
        ("invoke", ctypes.c_void_p),
        ("descriptor", ctypes.POINTER(_BlockDescriptor)),
    ]


# The C-level invoke function for a block taking (NSDictionary *):
#   void invoke(void *block, void *dict)
_BlockInvokeFn = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p)

# CoreFoundation string encoding constant
_kCFStringEncodingUTF8 = 0x08000100
# CFNumberType: Float64 (double)
_kCFNumberFloat64Type = 13


def _load_libraries():
    """Load MediaRemote, CoreFoundation and libdispatch. Returns None on failure."""
    try:
        mr = ctypes.CDLL(
            "/System/Library/PrivateFrameworks/MediaRemote.framework/MediaRemote"
        )
        cf = ctypes.CDLL(
            "/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation"
        )
        libdispatch = ctypes.CDLL("/usr/lib/system/libdispatch.dylib")
        libobjc = ctypes.CDLL("/usr/lib/libobjc.A.dylib")
        return mr, cf, libdispatch, libobjc
    except OSError:
        return None, None, None, None


def _configure_cf(cf, libdispatch):
    """Set ctypes function signatures for the CF/dispatch functions we use."""
    # CFStringCreateWithCString
    cf.CFStringCreateWithCString.restype = ctypes.c_void_p
    cf.CFStringCreateWithCString.argtypes = [
        ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32
    ]
    # CFStringGetLength
    cf.CFStringGetLength.restype = ctypes.c_long
    cf.CFStringGetLength.argtypes = [ctypes.c_void_p]
    # CFStringGetCString
    cf.CFStringGetCString.restype = ctypes.c_bool
    cf.CFStringGetCString.argtypes = [
        ctypes.c_void_p, ctypes.c_char_p, ctypes.c_long, ctypes.c_uint32
    ]
    # CFDictionaryGetValue
    cf.CFDictionaryGetValue.restype = ctypes.c_void_p
    cf.CFDictionaryGetValue.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    # CFNumberGetValue
    cf.CFNumberGetValue.restype = ctypes.c_bool
    cf.CFNumberGetValue.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
    # CFRelease
    cf.CFRelease.restype = None
    cf.CFRelease.argtypes = [ctypes.c_void_p]
    # dispatch_get_global_queue
    libdispatch.dispatch_get_global_queue.restype = ctypes.c_void_p
    libdispatch.dispatch_get_global_queue.argtypes = [ctypes.c_long, ctypes.c_ulong]


def _cf_str(cf, python_str: str) -> ctypes.c_void_p:
    """Create a CFStringRef from a Python string (caller must CFRelease)."""
    return cf.CFStringCreateWithCString(
        None, python_str.encode("utf-8"), _kCFStringEncodingUTF8
    )


def _cf_dict_get_str(cf, info_dict: int, key: str) -> Optional[str]:
    """Get a string value from a CFDictionary. Returns None if missing."""
    cf_key = _cf_str(cf, key)
    if not cf_key:
        return None
    try:
        value = cf.CFDictionaryGetValue(info_dict, cf_key)
        if not value:
            return None
        length = cf.CFStringGetLength(value)
        if length < 0:
            return None
        # Buffer: length * 4 bytes (max UTF-8) + null terminator
        buf_size = length * 4 + 1
        buf = ctypes.create_string_buffer(buf_size)
        if cf.CFStringGetCString(value, buf, buf_size, _kCFStringEncodingUTF8):
            return buf.value.decode("utf-8", errors="replace")
        return None
    finally:
        cf.CFRelease(cf_key)


def _cf_dict_get_float(cf, info_dict: int, key: str) -> Optional[float]:
    """Get a float64 value from a CFDictionary. Returns None if missing."""
    cf_key = _cf_str(cf, key)
    if not cf_key:
        return None
    try:
        value = cf.CFDictionaryGetValue(info_dict, cf_key)
        if not value:
            return None
        result = ctypes.c_double()
        if cf.CFNumberGetValue(value, _kCFNumberFloat64Type, ctypes.byref(result)):
            return result.value
        return None
    finally:
        cf.CFRelease(cf_key)


class MacOSMediaProvider(MediaProvider):
    """
    Media provider for macOS that reads the system Now Playing session
    via the private MediaRemote.framework.

    No external dependencies are required; the framework is pre-installed
    on every macOS system (10.14+).
    """

    def __init__(self):
        super().__init__()
        if platform.system() != "Darwin":
            raise RuntimeError("MacOSMediaProvider is only available on macOS")

        self._mr, self._cf, self._dispatch, self._libobjc = _load_libraries()
        if self._mr is None:
            raise RuntimeError(
                "Failed to load MediaRemote.framework – "
                "only supported on macOS 10.14 or later"
            )

        _configure_cf(self._cf, self._dispatch)

        # Set up MRMediaRemoteGetNowPlayingInfo signature
        self._mr.MRMediaRemoteGetNowPlayingInfo.restype = None
        self._mr.MRMediaRemoteGetNowPlayingInfo.argtypes = [
            ctypes.c_void_p,  # dispatch_queue_t
            ctypes.c_void_p,  # void (^handler)(NSDictionary *)
        ]

        # Resolve the global-block isa pointer
        try:
            self._global_block_isa = ctypes.c_void_p.in_dll(
                self._libobjc, "_NSConcreteGlobalBlock"
            ).value
        except Exception:
            self._global_block_isa = None

        self._watching = False
        self._watch_task: Optional[asyncio.Task] = None
        self._last_media: Optional[MediaInfo] = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _query_now_playing_sync(self) -> Optional[MediaInfo]:
        """
        Blocking call to MRMediaRemoteGetNowPlayingInfo.
        Uses a threading.Event to wait for the async callback.
        """
        result: list[Optional[MediaInfo]] = [None]
        event = threading.Event()

        def _invoke(_block_ptr: int, info_dict: int) -> None:
            """Block invocation function called by MediaRemote on a dispatch queue."""
            try:
                if not info_dict:
                    return

                title = _cf_dict_get_str(self._cf, info_dict, _KEY_TITLE)
                if not title:
                    # No title means nothing is playing
                    return

                artist = _cf_dict_get_str(self._cf, info_dict, _KEY_ARTIST) or ""
                album = _cf_dict_get_str(self._cf, info_dict, _KEY_ALBUM) or ""
                playback_rate = _cf_dict_get_float(self._cf, info_dict, _KEY_PLAYBACK_RATE)
                elapsed = _cf_dict_get_float(self._cf, info_dict, _KEY_ELAPSED_TIME)
                duration = _cf_dict_get_float(self._cf, info_dict, _KEY_DURATION)

                if playback_rate is None:
                    status = PlaybackStatus.UNKNOWN
                elif playback_rate > 0:
                    status = PlaybackStatus.PLAYING
                elif playback_rate == 0:
                    status = PlaybackStatus.PAUSED
                else:
                    status = PlaybackStatus.STOPPED

                result[0] = MediaInfo(
                    source_app="NowPlaying",
                    title=title,
                    artist=artist,
                    album=album,
                    status=status,
                    position_ms=int(elapsed * 1000) if elapsed is not None else None,
                    duration_ms=int(duration * 1000) if duration is not None else None,
                )
            except Exception as exc:
                print(f"MacOSMediaProvider callback error: {exc}")
            finally:
                event.set()

        # Keep Python callback alive until the event fires
        invoke_fn = _BlockInvokeFn(_invoke)

        descriptor = _BlockDescriptor(
            reserved=0,
            size=ctypes.sizeof(_BlockLiteral),
        )
        block = _BlockLiteral(
            isa=self._global_block_isa,
            flags=_BLOCK_IS_GLOBAL,
            reserved=0,
            invoke=ctypes.cast(invoke_fn, ctypes.c_void_p).value,
            descriptor=ctypes.pointer(descriptor),
        )

        queue = self._dispatch.dispatch_get_global_queue(0, 0)
        self._mr.MRMediaRemoteGetNowPlayingInfo(
            queue,
            ctypes.cast(ctypes.pointer(block), ctypes.c_void_p),
        )

        # Wait up to 3 seconds for the callback
        event.wait(timeout=3.0)
        return result[0]

    # ------------------------------------------------------------------
    # MediaProvider interface
    # ------------------------------------------------------------------

    async def get_current_media(self) -> Optional[MediaInfo]:
        """Get currently playing media from the system Now Playing session."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._query_now_playing_sync)

    async def start_watching(self) -> None:
        """Start polling for media changes."""
        if self._watching:
            return
        self._watching = True
        self._watch_task = asyncio.create_task(self._watch_loop())

    async def stop_watching(self) -> None:
        """Stop polling."""
        self._watching = False
        if self._watch_task:
            self._watch_task.cancel()
            try:
                await self._watch_task
            except asyncio.CancelledError:
                pass
            self._watch_task = None

    async def _watch_loop(self) -> None:
        """Polling loop that notifies on media changes (1-second interval)."""
        while self._watching:
            try:
                current = await self.get_current_media()
                if self._has_changed(current):
                    self._last_media = current
                    if current:
                        self._notify_change(current)
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                print(f"MacOSMediaProvider watch error: {exc}")
                await asyncio.sleep(2)

    def _has_changed(self, current: Optional[MediaInfo]) -> bool:
        """Return True if the media info has meaningfully changed."""
        if self._last_media is None and current is None:
            return False
        if self._last_media is None or current is None:
            return True
        return (
            self._last_media.title != current.title
            or self._last_media.artist != current.artist
            or self._last_media.status != current.status
            or self._last_media.source_app != current.source_app
        )
