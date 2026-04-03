"""
Unit tests for providers/base.py – MediaInfo, PlaybackStatus, MediaProvider.
"""
import pytest
from providers.base import MediaInfo, PlaybackStatus, MediaProvider
from typing import Optional


# ---------------------------------------------------------------------------
# PlaybackStatus
# ---------------------------------------------------------------------------

class TestPlaybackStatus:
    def test_values(self):
        assert PlaybackStatus.PLAYING.value == "playing"
        assert PlaybackStatus.PAUSED.value == "paused"
        assert PlaybackStatus.STOPPED.value == "stopped"
        assert PlaybackStatus.UNKNOWN.value == "unknown"

    def test_is_str_enum(self):
        # PlaybackStatus inherits from str, so it compares equal to its string value
        assert PlaybackStatus.PLAYING == "playing"
        assert PlaybackStatus.PAUSED == "paused"

    def test_all_members(self):
        members = {s.value for s in PlaybackStatus}
        assert members == {"playing", "paused", "stopped", "unknown"}


# ---------------------------------------------------------------------------
# MediaInfo – defaults
# ---------------------------------------------------------------------------

class TestMediaInfoDefaults:
    def test_default_values(self):
        info = MediaInfo()
        assert info.source_app == ""
        assert info.title == ""
        assert info.artist == ""
        assert info.album == ""
        assert info.status == PlaybackStatus.UNKNOWN
        assert info.position_ms is None
        assert info.duration_ms is None

    def test_custom_values(self):
        info = MediaInfo(
            source_app="Spotify",
            title="Test Song",
            artist="Test Artist",
            album="Test Album",
            status=PlaybackStatus.PLAYING,
            position_ms=30000,
            duration_ms=180000,
        )
        assert info.source_app == "Spotify"
        assert info.title == "Test Song"
        assert info.artist == "Test Artist"
        assert info.album == "Test Album"
        assert info.status == PlaybackStatus.PLAYING
        assert info.position_ms == 30000
        assert info.duration_ms == 180000


# ---------------------------------------------------------------------------
# MediaInfo.to_dict()
# ---------------------------------------------------------------------------

class TestMediaInfoToDict:
    def test_keys_present(self):
        info = MediaInfo()
        d = info.to_dict()
        expected_keys = {"source_app", "title", "artist", "album", "status", "position_ms", "duration_ms", "thumbnail"}
        assert expected_keys == set(d.keys())

    def test_status_is_string(self):
        info = MediaInfo(status=PlaybackStatus.PLAYING)
        d = info.to_dict()
        assert d["status"] == "playing"
        assert isinstance(d["status"], str)

    def test_thumbnail_always_none(self):
        info = MediaInfo()
        assert info.to_dict()["thumbnail"] is None

    def test_optional_fields_none(self):
        info = MediaInfo()
        d = info.to_dict()
        assert d["position_ms"] is None
        assert d["duration_ms"] is None

    def test_optional_fields_values(self):
        info = MediaInfo(position_ms=5000, duration_ms=200000)
        d = info.to_dict()
        assert d["position_ms"] == 5000
        assert d["duration_ms"] == 200000

    def test_full_roundtrip(self):
        info = MediaInfo(
            source_app="VLC",
            title="My Song",
            artist="My Artist",
            album="My Album",
            status=PlaybackStatus.PAUSED,
            position_ms=10000,
            duration_ms=300000,
        )
        d = info.to_dict()
        assert d["source_app"] == "VLC"
        assert d["title"] == "My Song"
        assert d["artist"] == "My Artist"
        assert d["album"] == "My Album"
        assert d["status"] == "paused"
        assert d["position_ms"] == 10000
        assert d["duration_ms"] == 300000


# ---------------------------------------------------------------------------
# MediaInfo.is_playing()
# ---------------------------------------------------------------------------

class TestMediaInfoIsPlaying:
    def test_playing(self):
        assert MediaInfo(status=PlaybackStatus.PLAYING).is_playing() is True

    def test_paused(self):
        assert MediaInfo(status=PlaybackStatus.PAUSED).is_playing() is False

    def test_stopped(self):
        assert MediaInfo(status=PlaybackStatus.STOPPED).is_playing() is False

    def test_unknown(self):
        assert MediaInfo(status=PlaybackStatus.UNKNOWN).is_playing() is False


# ---------------------------------------------------------------------------
# MediaInfo.format_time()
# ---------------------------------------------------------------------------

class TestFormatTime:
    def test_zero(self):
        assert MediaInfo.format_time(0) == "0:00"

    def test_one_minute(self):
        assert MediaInfo.format_time(60_000) == "1:00"

    def test_one_second(self):
        assert MediaInfo.format_time(1_000) == "0:01"

    def test_one_hour(self):
        assert MediaInfo.format_time(3_600_000) == "60:00"

    def test_sub_second_truncated(self):
        # Milliseconds that don't add a full second
        assert MediaInfo.format_time(999) == "0:00"
        assert MediaInfo.format_time(1_999) == "0:01"

    def test_padding(self):
        # Seconds < 10 should be zero-padded
        assert MediaInfo.format_time(5_000) == "0:05"
        assert MediaInfo.format_time(65_000) == "1:05"

    def test_realistic_song(self):
        # 3 minutes 45 seconds
        assert MediaInfo.format_time(225_000) == "3:45"


# ---------------------------------------------------------------------------
# MediaProvider abstract interface
# ---------------------------------------------------------------------------

class TestMediaProviderAbstract:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            MediaProvider()  # type: ignore[abstract]

    def test_concrete_subclass_works(self):
        class ConcreteProvider(MediaProvider):
            async def get_current_media(self) -> Optional[MediaInfo]:
                return None

            async def start_watching(self) -> None:
                pass

            async def stop_watching(self) -> None:
                pass

        provider = ConcreteProvider()
        assert provider is not None

    def test_set_on_change_callback(self):
        class ConcreteProvider(MediaProvider):
            async def get_current_media(self) -> Optional[MediaInfo]:
                return None

            async def start_watching(self) -> None:
                pass

            async def stop_watching(self) -> None:
                pass

        provider = ConcreteProvider()
        received = []

        def cb(info):
            received.append(info)

        provider.set_on_change_callback(cb)
        media = MediaInfo(title="Test")
        provider._notify_change(media)
        assert received == [media]

    def test_notify_change_no_callback(self):
        class ConcreteProvider(MediaProvider):
            async def get_current_media(self) -> Optional[MediaInfo]:
                return None

            async def start_watching(self) -> None:
                pass

            async def stop_watching(self) -> None:
                pass

        provider = ConcreteProvider()
        # Should not raise even without a callback registered
        provider._notify_change(MediaInfo())
