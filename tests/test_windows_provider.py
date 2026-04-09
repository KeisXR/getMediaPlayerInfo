"""
Unit tests for providers/windows.py session selection and metadata coalescing.
"""
import pytest

from providers.base import PlaybackStatus
from providers.windows import WindowsMediaProvider


class _MockMediaProperties:
    def __init__(self, title: str = "", artist: str = "", album_title: str = ""):
        self.title = title
        self.artist = artist
        self.album_title = album_title


class _MockPlaybackInfo:
    def __init__(self, playback_status):
        self.playback_status = playback_status


class _MockSession:
    def __init__(self, status: PlaybackStatus, title: str, artist: str, album: str, app_id: str):
        self._status = status
        self._props = _MockMediaProperties(title=title, artist=artist, album_title=album)
        self.source_app_user_model_id = app_id

    async def try_get_media_properties_async(self):
        return self._props

    def get_playback_info(self):
        return _MockPlaybackInfo(self._status)


class _MockManager:
    def __init__(self, current_session, sessions):
        self._current = current_session
        self._sessions = sessions

    def get_current_session(self):
        return self._current

    def get_sessions(self):
        return self._sessions


class TestWindowsMediaProviderHelpers:
    def test_metadata_priority(self):
        assert WindowsMediaProvider._metadata_priority("title", "", "") == 3
        assert WindowsMediaProvider._metadata_priority("", "artist", "") == 2
        assert WindowsMediaProvider._metadata_priority("", "", "album") == 1
        assert WindowsMediaProvider._metadata_priority("", "", "") == 0

    def test_coalesce_title(self):
        assert WindowsMediaProvider._coalesce_title("Song", "Artist", "Album", "App") == "Song"
        assert WindowsMediaProvider._coalesce_title("", "Station", "", "App") == "Station"
        assert WindowsMediaProvider._coalesce_title("", "", "AlbumOnly", "App") == "AlbumOnly"
        assert WindowsMediaProvider._coalesce_title("", "", "", "AppOnly") == "AppOnly"


@pytest.mark.asyncio
async def test_select_best_session_prefers_playing_and_richer_metadata():
    provider = WindowsMediaProvider.__new__(WindowsMediaProvider)
    provider._convert_playback_status = lambda status: status

    paused_with_title = _MockSession(
        status=PlaybackStatus.PAUSED,
        title="Paused Song",
        artist="Artist",
        album="Album",
        app_id="PausedApp.exe",
    )
    playing_without_title = _MockSession(
        status=PlaybackStatus.PLAYING,
        title="",
        artist="Radio Station",
        album="",
        app_id="RadioApp.exe",
    )

    manager = _MockManager(current_session=paused_with_title, sessions=[paused_with_title, playing_without_title])
    selected = await provider._select_best_session_data(manager)

    assert selected is not None
    assert selected["session"] is playing_without_title
    assert selected["source_app"] == "RadioApp"
    assert selected["artist"] == "Radio Station"
