"""
Windows notification listener for capturing Amazon Music track info.
Falls back to notification data when SMTC doesn't provide complete info.
"""
import asyncio
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

# Check for winrt notification support
try:
    import winrt.windows.ui.notifications.management as notifications_mgmt
    import winrt.windows.ui.notifications as notifications
    NOTIFICATIONS_AVAILABLE = True
except ImportError:
    NOTIFICATIONS_AVAILABLE = False


@dataclass
class NotificationMediaInfo:
    """Media info extracted from a notification."""
    title: str
    artist: str
    album: str
    timestamp: datetime
    
    def is_fresh(self, max_age_seconds: float = 300) -> bool:
        """Check if this info is still fresh (default 5 minutes)."""
        age = (datetime.now(timezone.utc) - self.timestamp).total_seconds()
        return age < max_age_seconds


class AmazonMusicNotificationListener:
    """Listens for Amazon Music notifications and extracts track info."""
    
    AMAZON_MUSIC_APP_IDS = [
        "AmazonMobileLLC.AmazonMusic",
        "Amazon.Music",
    ]
    
    def __init__(self):
        self._cached_info: Optional[NotificationMediaInfo] = None
        self._listener = None
        self._watching = False
    
    def is_amazon_music_running(self) -> bool:
        """Check if Amazon Music process is running."""
        try:
            # Use tasklist to check for Amazon Music process
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq Amazon Music.exe", "/NH"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return "Amazon Music.exe" in result.stdout
        except Exception:
            return False
    
    async def get_cached_info(self) -> Optional[NotificationMediaInfo]:
        """Get cached notification info if available and fresh."""
        if self._cached_info and self._cached_info.is_fresh():
            return self._cached_info
        return None
    
    async def check_notifications(self) -> Optional[NotificationMediaInfo]:
        """Check recent notifications for Amazon Music track info."""
        if not NOTIFICATIONS_AVAILABLE:
            return None
        
        try:
            # Get notification listener
            listener = notifications_mgmt.UserNotificationListener.current
            
            # Check access
            access = await listener.request_access_async()
            if access != notifications_mgmt.UserNotificationListenerAccessStatus.ALLOWED:
                print("Notification access not granted")
                return None
            
            # Get notifications
            notifs = await listener.get_notifications_async(
                notifications.NotificationKinds.TOAST
            )
            
            for notif in notifs:
                try:
                    app_info = notif.app_info
                    if app_info is None:
                        continue
                    
                    try:
                        app_id = app_info.app_user_model_id or ""
                    except (OSError, AttributeError):
                        # Some notifications don't have app info accessible
                        continue
                    
                    # Check if this is from Amazon Music
                    is_amazon = any(amid in app_id for amid in self.AMAZON_MUSIC_APP_IDS)
                    if not is_amazon:
                        continue
                    
                    # Extract notification content
                    toast = notif.notification
                    if toast is None:
                        continue
                    
                    # Get visual elements
                    visual = toast.visual
                    if visual is None:
                        continue
                    
                    binding = visual.get_binding(
                        notifications.KnownNotificationBindings.toast_generic
                    )
                    if binding is None:
                        continue
                    
                    # Extract text elements
                    texts = binding.get_text_elements()
                    text_list = [t.text for t in texts if t and t.text]
                    
                    if len(text_list) >= 3:
                        # Typically: [Title, Artist, Album]
                        info = NotificationMediaInfo(
                            title=text_list[0],
                            artist=text_list[1],
                            album=text_list[2] if len(text_list) > 2 else "",
                            timestamp=datetime.now(timezone.utc)
                        )
                        self._cached_info = info
                        return info
                    elif len(text_list) >= 2:
                        info = NotificationMediaInfo(
                            title=text_list[0],
                            artist=text_list[1],
                            album="",
                            timestamp=datetime.now(timezone.utc)
                        )
                        self._cached_info = info
                        return info
                        
                except (OSError, AttributeError):
                    # Skip notifications that can't be parsed (e.g., system notifications)
                    continue
                except Exception:
                    # Silently skip any other parsing errors
                    continue
            
            return None
            
        except Exception as e:
            print(f"Error checking notifications: {e}")
            return None
    
    async def poll_notifications(self) -> Optional[NotificationMediaInfo]:
        """Poll for new notification info, returns cached if no new found."""
        # Only check if Amazon Music is running
        if not self.is_amazon_music_running():
            return None
        
        # Try to get new notification info
        new_info = await self.check_notifications()
        if new_info:
            return new_info
        
        # Return cached info if still fresh
        return await self.get_cached_info()


# Global instance
_notification_listener: Optional[AmazonMusicNotificationListener] = None


def get_notification_listener() -> AmazonMusicNotificationListener:
    """Get or create the notification listener instance."""
    global _notification_listener
    if _notification_listener is None:
        _notification_listener = AmazonMusicNotificationListener()
    return _notification_listener
