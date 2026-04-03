package com.mediaplayerapi

import android.content.ComponentName
import android.content.Context
import android.media.MediaMetadata
import android.media.session.MediaController
import android.media.session.MediaSessionManager
import android.media.session.PlaybackState
import android.os.SystemClock
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import android.util.Log
import com.mediaplayerapi.model.MediaInfo

/**
 * MediaSession monitor using NotificationListenerService.
 *
 * This service exclusively uses the MediaSession API to retrieve media information,
 * avoiding the data inconsistencies caused by dual notification + session monitoring
 * in the previous implementation.
 *
 * The NotificationListenerService is required only for the system to grant us access
 * to MediaSessionManager.getActiveSessions().
 */
class MediaSessionMonitor : NotificationListenerService() {

    companion object {
        private const val TAG = "MediaSessionMonitor"
        private const val CACHE_TTL_MS = 30_000L  // 30 seconds

        @Volatile
        private var currentMedia: MediaInfo? = null

        @Volatile
        private var lastUpdatedMs: Long = 0L

        // For real-time position calculation
        @Volatile
        private var lastPositionMs: Long = 0L

        @Volatile
        private var lastPositionUpdateElapsed: Long = 0L

        @Volatile
        private var playbackSpeed: Float = 1.0f

        @Volatile
        private var isCurrentlyPlaying: Boolean = false

        @Volatile
        private var instance: MediaSessionMonitor? = null

        /**
         * Callback invoked on the calling thread whenever media info changes.
         * Register from MediaApiService to push WebSocket updates.
         */
        @Volatile
        var onMediaChanged: ((MediaInfo?) -> Unit)? = null

        /**
         * Get current media info with real-time position calculation.
         * For playing media, the position is extrapolated based on elapsed time
         * since the last PlaybackState update.
         */
        fun getCurrentMedia(): MediaInfo? {
            val media = currentMedia ?: return null

            // Calculate real-time position if playing
            if (isCurrentlyPlaying && lastPositionUpdateElapsed > 0) {
                val elapsedSinceUpdate = SystemClock.elapsedRealtime() - lastPositionUpdateElapsed
                val estimatedPosition = lastPositionMs + (elapsedSinceUpdate * playbackSpeed).toLong()

                // Clamp to duration if available
                val clampedPosition = if (media.durationMs != null && media.durationMs > 0) {
                    estimatedPosition.coerceIn(0, media.durationMs)
                } else {
                    estimatedPosition.coerceAtLeast(0)
                }

                return media.copy(positionMs = clampedPosition)
            }

            return media
        }

        /**
         * Get cached media info if cache is still valid, null otherwise.
         */
        fun getCachedMedia(): Pair<MediaInfo?, Boolean> {
            val media = currentMedia ?: return Pair(null, false)
            val age = System.currentTimeMillis() - lastUpdatedMs
            return if (age < CACHE_TTL_MS) {
                Pair(media, age > 0)
            } else {
                Pair(null, false)
            }
        }

        /**
         * Check if notification listener access is enabled for this app.
         */
        fun isEnabled(context: Context): Boolean {
            val componentName = ComponentName(context, MediaSessionMonitor::class.java)
            val enabledListeners = android.provider.Settings.Secure.getString(
                context.contentResolver,
                "enabled_notification_listeners"
            )
            return enabledListeners?.contains(componentName.flattenToString()) == true
        }
    }

    private var mediaSessionManager: MediaSessionManager? = null
    private val activeControllers = mutableMapOf<String, MediaController>()

    private val sessionListener = MediaSessionManager.OnActiveSessionsChangedListener { controllers ->
        Log.d(TAG, "Active sessions changed: ${controllers?.size ?: 0} sessions")
        updateActiveControllers(controllers ?: emptyList())
    }

    private val mediaControllerCallback = object : MediaController.Callback() {
        override fun onPlaybackStateChanged(state: PlaybackState?) {
            Log.d(TAG, "Playback state changed: ${state?.state}")
            updateMediaFromSessions()
        }

        override fun onMetadataChanged(metadata: MediaMetadata?) {
            Log.d(TAG, "Metadata changed: ${metadata?.getString(MediaMetadata.METADATA_KEY_TITLE)}")
            updateMediaFromSessions()
        }
    }

    override fun onCreate() {
        super.onCreate()
        instance = this
        Log.i(TAG, "MediaSessionMonitor created")

        try {
            mediaSessionManager = getSystemService(Context.MEDIA_SESSION_SERVICE) as MediaSessionManager
            val componentName = ComponentName(this, MediaSessionMonitor::class.java)

            // Get initial active sessions
            val controllers = mediaSessionManager?.getActiveSessions(componentName)
            if (controllers != null) {
                Log.d(TAG, "Initial sessions: ${controllers.size}")
                updateActiveControllers(controllers)
            }

            // Listen for session changes
            mediaSessionManager?.addOnActiveSessionsChangedListener(sessionListener, componentName)
        } catch (e: SecurityException) {
            Log.e(TAG, "SecurityException accessing MediaSessionManager - notification access not granted?", e)
        } catch (e: Exception) {
            Log.e(TAG, "Error initializing MediaSessionMonitor", e)
        }
    }

    override fun onDestroy() {
        instance = null

        // Unregister all callbacks
        activeControllers.values.forEach { controller ->
            try {
                controller.unregisterCallback(mediaControllerCallback)
            } catch (e: Exception) {
                Log.w(TAG, "Error unregistering callback", e)
            }
        }
        activeControllers.clear()

        try {
            mediaSessionManager?.removeOnActiveSessionsChangedListener(sessionListener)
        } catch (e: Exception) {
            Log.w(TAG, "Error removing session listener", e)
        }

        Log.i(TAG, "MediaSessionMonitor destroyed")
        super.onDestroy()
    }

    // We override these but don't process notifications directly.
    // The NotificationListenerService binding is required for MediaSession access.
    override fun onNotificationPosted(sbn: StatusBarNotification?) {
        // No-op: we only use MediaSession API
    }

    override fun onNotificationRemoved(sbn: StatusBarNotification?) {
        // No-op
    }

    /**
     * Update tracked controllers when active sessions change.
     */
    private fun updateActiveControllers(controllers: List<MediaController>) {
        // Unregister old callbacks
        activeControllers.values.forEach { controller ->
            try {
                controller.unregisterCallback(mediaControllerCallback)
            } catch (e: Exception) {
                // Ignore
            }
        }
        activeControllers.clear()

        // Register new callbacks
        controllers.forEach { controller ->
            val packageName = controller.packageName
            activeControllers[packageName] = controller
            try {
                controller.registerCallback(mediaControllerCallback)
                Log.d(TAG, "Registered callback for: $packageName")
            } catch (e: Exception) {
                Log.e(TAG, "Error registering callback for $packageName", e)
            }
        }

        // Immediately update media info
        updateMediaFromSessions()
    }

    /**
     * Update current media info from active MediaSessions.
     * Priority: playing > paused > first available
     */
    private fun updateMediaFromSessions() {
        // Find the best controller (prefer playing, then paused)
        val playingController = activeControllers.values.find { controller ->
            controller.playbackState?.state == PlaybackState.STATE_PLAYING
        } ?: activeControllers.values.find { controller ->
            controller.playbackState?.state == PlaybackState.STATE_PAUSED
        }

        if (playingController != null) {
            val metadata = playingController.metadata
            val playbackState = playingController.playbackState

            val status = when (playbackState?.state) {
                PlaybackState.STATE_PLAYING -> "playing"
                PlaybackState.STATE_PAUSED -> "paused"
                PlaybackState.STATE_STOPPED -> "stopped"
                PlaybackState.STATE_BUFFERING -> "playing"
                else -> "unknown"
            }

            val title = metadata?.getString(MediaMetadata.METADATA_KEY_TITLE) ?: ""
            val artist = metadata?.getString(MediaMetadata.METADATA_KEY_ARTIST)
                ?: metadata?.getString(MediaMetadata.METADATA_KEY_ALBUM_ARTIST) ?: ""
            val album = metadata?.getString(MediaMetadata.METADATA_KEY_ALBUM) ?: ""
            val duration = metadata?.getLong(MediaMetadata.METADATA_KEY_DURATION)?.takeIf { it > 0 }
            val position = playbackState?.position?.takeIf { it >= 0 }

            // Store position tracking data for real-time calculation
            lastPositionMs = position ?: 0L
            lastPositionUpdateElapsed = playbackState?.lastPositionUpdateTime ?: SystemClock.elapsedRealtime()
            playbackSpeed = playbackState?.playbackSpeed ?: 1.0f
            isCurrentlyPlaying = (status == "playing")

            currentMedia = MediaInfo(
                sourceApp = playingController.packageName,
                title = title,
                artist = artist,
                album = album,
                status = status,
                positionMs = position,
                durationMs = duration,
                thumbnail = null
            )
            lastUpdatedMs = System.currentTimeMillis()

            Log.d(TAG, "Media updated: $title by $artist [$status] pos=${position}ms dur=${duration}ms from ${playingController.packageName}")
            onMediaChanged?.invoke(currentMedia)
        } else if (activeControllers.isEmpty()) {
            // No active sessions at all — clear media
            currentMedia = null
            lastUpdatedMs = System.currentTimeMillis()
            Log.d(TAG, "No active media sessions")
            onMediaChanged?.invoke(null)
        }
        // If controllers exist but none are playing/paused, keep the last known state
    }
}
