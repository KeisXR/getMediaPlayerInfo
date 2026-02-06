package com.mediaplayerapi

import android.app.Notification
import android.content.ComponentName
import android.content.Context
import android.media.MediaMetadata
import android.media.session.MediaController
import android.media.session.MediaSessionManager
import android.media.session.PlaybackState
import android.os.Bundle
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import android.util.Log

/**
 * NotificationListenerService that captures media information from notifications
 * and active MediaSessions.
 */
class MediaNotificationListener : NotificationListenerService() {

    companion object {
        private const val TAG = "MediaNotificationListener"
        
        @Volatile
        private var currentMedia: MediaInfo? = null
        
        @Volatile
        private var instance: MediaNotificationListener? = null
        
        fun getCurrentMedia(): MediaInfo? = currentMedia
        
        fun isEnabled(context: Context): Boolean {
            val componentName = ComponentName(context, MediaNotificationListener::class.java)
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
        updateActiveControllers(controllers ?: emptyList())
    }
    
    private val mediaControllerCallback = object : MediaController.Callback() {
        override fun onPlaybackStateChanged(state: PlaybackState?) {
            updateMediaFromSessions()
        }
        
        override fun onMetadataChanged(metadata: MediaMetadata?) {
            updateMediaFromSessions()
        }
    }
    
    override fun onCreate() {
        super.onCreate()
        instance = this
        Log.d(TAG, "MediaNotificationListener created")
        
        try {
            mediaSessionManager = getSystemService(Context.MEDIA_SESSION_SERVICE) as MediaSessionManager
            val componentName = ComponentName(this, MediaNotificationListener::class.java)
            
            val controllers = mediaSessionManager?.getActiveSessions(componentName)
            if (controllers != null) {
                updateActiveControllers(controllers)
            }
            
            mediaSessionManager?.addOnActiveSessionsChangedListener(sessionListener, componentName)
        } catch (e: SecurityException) {
            Log.e(TAG, "SecurityException accessing MediaSessionManager", e)
        }
    }
    
    override fun onDestroy() {
        super.onDestroy()
        instance = null
        
        activeControllers.values.forEach { it.unregisterCallback(mediaControllerCallback) }
        activeControllers.clear()
        
        try {
            mediaSessionManager?.removeOnActiveSessionsChangedListener(sessionListener)
        } catch (e: Exception) {
            Log.e(TAG, "Error removing session listener", e)
        }
        
        Log.d(TAG, "MediaNotificationListener destroyed")
    }
    
    override fun onNotificationPosted(sbn: StatusBarNotification?) {
        sbn?.let { processNotification(it) }
    }
    
    override fun onNotificationRemoved(sbn: StatusBarNotification?) {
        // Could clear media info if the notification is from the active player
    }
    
    private fun updateActiveControllers(controllers: List<MediaController>) {
        // Unregister old callbacks
        activeControllers.values.forEach { 
            try {
                it.unregisterCallback(mediaControllerCallback) 
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
            } catch (e: Exception) {
                Log.e(TAG, "Error registering callback for $packageName", e)
            }
        }
        
        updateMediaFromSessions()
    }
    
    private fun updateMediaFromSessions() {
        // Find the active/playing session
        val playingController = activeControllers.values.find { controller ->
            controller.playbackState?.state == PlaybackState.STATE_PLAYING
        } ?: activeControllers.values.firstOrNull { controller ->
            controller.playbackState?.state == PlaybackState.STATE_PAUSED
        }
        
        if (playingController != null) {
            val metadata = playingController.metadata
            val playbackState = playingController.playbackState
            
            val status = when (playbackState?.state) {
                PlaybackState.STATE_PLAYING -> "playing"
                PlaybackState.STATE_PAUSED -> "paused"
                PlaybackState.STATE_STOPPED -> "stopped"
                else -> "unknown"
            }
            
            currentMedia = MediaInfo(
                title = metadata?.getString(MediaMetadata.METADATA_KEY_TITLE) ?: "",
                artist = metadata?.getString(MediaMetadata.METADATA_KEY_ARTIST) 
                    ?: metadata?.getString(MediaMetadata.METADATA_KEY_ALBUM_ARTIST) ?: "",
                album = metadata?.getString(MediaMetadata.METADATA_KEY_ALBUM) ?: "",
                duration = metadata?.getLong(MediaMetadata.METADATA_KEY_DURATION)?.takeIf { it > 0 },
                position = playbackState?.position?.takeIf { it >= 0 },
                status = status,
                source = playingController.packageName,
                artworkUrl = metadata?.getString(MediaMetadata.METADATA_KEY_ART_URI)
            )
            
            Log.d(TAG, "Media updated from session: ${currentMedia?.title}")
        }
    }
    
    private fun processNotification(sbn: StatusBarNotification) {
        val notification = sbn.notification ?: return
        
        // Check if this is a media notification
        if (!isMediaNotification(notification)) return
        
        // Try to extract media info from notification extras
        val extras = notification.extras ?: return
        
        val title = extras.getCharSequence(Notification.EXTRA_TITLE)?.toString()
        val text = extras.getCharSequence(Notification.EXTRA_TEXT)?.toString()
        val subText = extras.getCharSequence(Notification.EXTRA_SUB_TEXT)?.toString()
        
        if (title != null && currentMedia?.title != title) {
            // Only update if we don't have better info from MediaSession
            if (currentMedia == null || currentMedia?.status == "unknown") {
                currentMedia = MediaInfo(
                    title = title,
                    artist = text ?: "",
                    album = subText ?: "",
                    status = "playing",
                    source = sbn.packageName
                )
                Log.d(TAG, "Media updated from notification: $title")
            }
        }
    }
    
    private fun isMediaNotification(notification: Notification): Boolean {
        // Check for media style notification
        val extras = notification.extras
        val template = extras?.getString(Notification.EXTRA_TEMPLATE)
        
        return template?.contains("MediaStyle") == true ||
               notification.category == Notification.CATEGORY_TRANSPORT
    }
}
