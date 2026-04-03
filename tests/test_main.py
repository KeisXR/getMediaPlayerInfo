"""
Unit tests for main.py – FastAPI endpoints and helper functions.

The tests mock the media provider so they run on any platform (Windows, Linux, macOS)
without requiring platform-specific media APIs.
"""
import json
from datetime import datetime, timezone, timedelta
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from providers.base import MediaInfo, PlaybackStatus


# ---------------------------------------------------------------------------
# Helpers to build a mock provider
# ---------------------------------------------------------------------------

def _make_provider(media: Optional[MediaInfo] = None) -> MagicMock:
    """Return a mock MediaProvider whose get_current_media returns *media*."""
    provider = MagicMock()
    provider.__class__.__name__ = "MockProvider"
    provider.get_current_media = AsyncMock(return_value=media)
    provider.start_watching = AsyncMock()
    provider.stop_watching = AsyncMock()
    provider.set_on_change_callback = MagicMock()
    return provider


def _sample_media(**kwargs) -> MediaInfo:
    defaults = dict(
        source_app="Spotify",
        title="Test Song",
        artist="Test Artist",
        album="Test Album",
        status=PlaybackStatus.PLAYING,
        position_ms=30_000,
        duration_ms=180_000,
    )
    defaults.update(kwargs)
    return MediaInfo(**defaults)


# ---------------------------------------------------------------------------
# Fixture: FastAPI test client with mocked provider
# ---------------------------------------------------------------------------

@pytest.fixture()
def client_no_media():
    """TestClient with a provider that returns no current media."""
    mock_provider = _make_provider(media=None)
    with (
        patch("main.get_provider", return_value=mock_provider),
        patch("main.VRCHAT_AVAILABLE", False),
        patch("main.media_cache", None),
    ):
        from main import app
        with TestClient(app, raise_server_exceptions=True) as client:
            yield client


@pytest.fixture()
def client_with_media():
    """TestClient with a provider that returns a playing track."""
    mock_provider = _make_provider(media=_sample_media())
    with (
        patch("main.get_provider", return_value=mock_provider),
        patch("main.VRCHAT_AVAILABLE", False),
        patch("main.media_cache", None),
    ):
        from main import app
        with TestClient(app, raise_server_exceptions=True) as client:
            yield client


# ---------------------------------------------------------------------------
# GET /
# ---------------------------------------------------------------------------

class TestRootEndpoint:
    def test_status_ok(self, client_with_media):
        response = client_with_media.get("/")
        assert response.status_code == 200

    def test_response_shape(self, client_with_media):
        data = client_with_media.get("/").json()
        assert data["status"] == "running"
        assert "service" in data
        assert "version" in data
        assert "system" in data
        assert "provider" in data
        assert "cache_ttl_seconds" in data

    def test_provider_name_present(self, client_with_media):
        data = client_with_media.get("/").json()
        assert data["provider"] == "MockProvider"


# ---------------------------------------------------------------------------
# GET /now-playing
# ---------------------------------------------------------------------------

class TestNowPlayingEndpoint:
    def test_returns_200_with_media(self, client_with_media):
        response = client_with_media.get("/now-playing")
        assert response.status_code == 200

    def test_media_fields_present(self, client_with_media):
        data = client_with_media.get("/now-playing").json()
        assert "media" in data
        assert "system" in data
        assert "last_updated" in data
        assert "cached" in data

    def test_media_content(self, client_with_media):
        media = client_with_media.get("/now-playing").json()["media"]
        assert media["title"] == "Test Song"
        assert media["artist"] == "Test Artist"
        assert media["album"] == "Test Album"
        assert media["status"] == "playing"
        assert media["source_app"] == "Spotify"
        assert media["position_ms"] == 30_000
        assert media["duration_ms"] == 180_000

    def test_no_media_returns_null(self, client_no_media):
        data = client_no_media.get("/now-playing").json()
        assert data["media"] is None

    def test_not_cached_on_fresh_fetch(self, client_with_media):
        data = client_with_media.get("/now-playing").json()
        assert data["cached"] is False

    def test_provider_unavailable_returns_503(self):
        with (
            patch("main.get_provider", side_effect=RuntimeError("no provider")),
            patch("main.VRCHAT_AVAILABLE", False),
        ):
            from main import app
            with TestClient(app, raise_server_exceptions=False) as client:
                # provider initialisation failure → provider = None
                response = client.get("/now-playing")
                assert response.status_code == 503

    def test_provider_error_returns_500_without_cache(self):
        mock_provider = _make_provider()
        mock_provider.get_current_media = AsyncMock(side_effect=RuntimeError("boom"))
        with (
            patch("main.get_provider", return_value=mock_provider),
            patch("main.VRCHAT_AVAILABLE", False),
            patch("main.media_cache", None),
        ):
            from main import app
            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.get("/now-playing")
                assert response.status_code == 500
                assert "error" in response.json()


# ---------------------------------------------------------------------------
# GET /vrchat/now-playing
# ---------------------------------------------------------------------------

class TestVRChatNowPlayingEndpoint:
    def test_returns_200_no_vrchat(self, client_with_media):
        response = client_with_media.get("/vrchat/now-playing")
        assert response.status_code == 200

    def test_source_fallback_when_no_vrchat(self, client_with_media):
        data = client_with_media.get("/vrchat/now-playing").json()
        # VRChat provider is disabled; should fall back to main provider
        assert data["source"] in ("fallback", "fallback_cached")

    def test_no_media_source_none(self, client_no_media):
        data = client_no_media.get("/vrchat/now-playing").json()
        assert data["source"] in ("fallback", "fallback_cached", "none")


# ---------------------------------------------------------------------------
# MediaCache helper (tested via main module)
# ---------------------------------------------------------------------------

class TestMediaCache:
    def test_is_valid_fresh(self):
        from main import MediaCache
        cache = MediaCache(
            media=MediaInfo(),
            timestamp=datetime.now(timezone.utc),
        )
        assert cache.is_valid() is True

    def test_is_valid_expired(self):
        from main import MediaCache, CACHE_TTL_SECONDS
        old_time = datetime.now(timezone.utc) - timedelta(seconds=CACHE_TTL_SECONDS + 1)
        cache = MediaCache(media=MediaInfo(), timestamp=old_time)
        assert cache.is_valid() is False

    def test_get_age_seconds(self):
        from main import MediaCache
        past = datetime.now(timezone.utc) - timedelta(seconds=10)
        cache = MediaCache(media=MediaInfo(), timestamp=past)
        age = cache.get_age_seconds()
        assert 9 < age < 15  # Allow some tolerance
