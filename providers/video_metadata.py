"""
Video metadata fetching module.
Fetches video title, channel/author, and duration from URLs.
Uses yt-dlp for duration and oEmbed APIs for basic metadata.
"""
import re
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict, Any
from dataclasses import dataclass

# yt-dlp for duration extraction
try:
    import yt_dlp
    YT_DLP_AVAILABLE = True
except ImportError:
    YT_DLP_AVAILABLE = False


@dataclass
class VideoMetadata:
    """Video metadata."""
    title: str
    author: str
    url: str
    provider: str
    duration: Optional[int] = None  # Duration in seconds


# oEmbed endpoints for different video providers
OEMBED_ENDPOINTS = {
    "youtube": "https://www.youtube.com/oembed?url={url}&format=json",
    "twitch": "https://www.twitch.tv/oembed?url={url}",
}

# URL patterns for video providers
URL_PATTERNS = {
    "youtube": [
        r"(?:https?://)?(?:www\.)?youtube\.com/watch\?v=[\w-]+",
        r"(?:https?://)?youtu\.be/[\w-]+",
        r"(?:https?://)?(?:www\.)?youtube\.com/shorts/[\w-]+",
    ],
    "twitch": [
        r"(?:https?://)?(?:www\.)?twitch\.tv/videos/\d+",
        r"(?:https?://)?clips\.twitch\.tv/[\w-]+",
    ],
}

# Thread pool for yt-dlp (blocking calls)
_executor = ThreadPoolExecutor(max_workers=2)


def identify_provider(url: str) -> Optional[str]:
    """Identify the video provider from URL."""
    for provider, patterns in URL_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return provider
    return None


async def fetch_oembed(url: str, endpoint: str, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
    """Fetch oEmbed data from an endpoint."""
    try:
        oembed_url = endpoint.format(url=url)
        async with aiohttp.ClientSession() as session:
            async with session.get(oembed_url, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                if response.status == 200:
                    return await response.json()
    except Exception as e:
        print(f"Error fetching oEmbed data: {e}")
    return None


def _get_duration_sync(url: str) -> Optional[int]:
    """Synchronously get video duration using yt-dlp."""
    if not YT_DLP_AVAILABLE:
        return None
    
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'extract_flat': False,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info and 'duration' in info:
                return int(info['duration'])
    except Exception as e:
        print(f"Error getting duration with yt-dlp: {e}")
    return None


async def get_video_duration(url: str) -> Optional[int]:
    """Get video duration in seconds using yt-dlp."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _get_duration_sync, url)


async def get_video_metadata(url: str, include_duration: bool = True) -> Optional[VideoMetadata]:
    """
    Get video metadata (title, author, duration) from a video URL.
    
    Supports:
    - YouTube (youtube.com, youtu.be, shorts)
    - Twitch (videos, clips)
    
    Args:
        url: Video URL
        include_duration: Whether to fetch duration (slower, uses yt-dlp)
    
    Returns None if metadata cannot be fetched.
    """
    provider = identify_provider(url)
    if not provider:
        return None
    
    endpoint = OEMBED_ENDPOINTS.get(provider)
    if not endpoint:
        return None
    
    # Fetch oEmbed data and duration concurrently
    if include_duration:
        oembed_task = fetch_oembed(url, endpoint)
        duration_task = get_video_duration(url)
        data, duration = await asyncio.gather(oembed_task, duration_task)
    else:
        data = await fetch_oembed(url, endpoint)
        duration = None
    
    if not data:
        return None
    
    return VideoMetadata(
        title=data.get("title", ""),
        author=data.get("author_name", ""),
        url=url,
        provider=provider,
        duration=duration
    )


def extract_video_urls(text: str) -> list[str]:
    """Extract all video URLs from text."""
    urls = []
    for provider, patterns in URL_PATTERNS.items():
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            urls.extend(matches)
    return urls
