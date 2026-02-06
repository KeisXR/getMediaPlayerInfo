package com.mediaplayerapi

import com.google.gson.annotations.SerializedName
import java.text.SimpleDateFormat
import java.util.*

/**
 * Media information data class.
 * Matches the JSON structure of the Python version.
 */
data class MediaInfo(
    @SerializedName("title")
    val title: String = "",
    
    @SerializedName("artist")
    val artist: String = "",
    
    @SerializedName("album")
    val album: String = "",
    
    @SerializedName("duration")
    val duration: Long? = null,
    
    @SerializedName("position")
    val position: Long? = null,
    
    @SerializedName("status")
    val status: String = "unknown",
    
    @SerializedName("source")
    val source: String = "",
    
    @SerializedName("artwork_url")
    val artworkUrl: String? = null
) {
    fun toMap(): Map<String, Any?> = mapOf(
        "title" to title,
        "artist" to artist,
        "album" to album,
        "duration" to duration,
        "position" to position,
        "status" to status,
        "source" to source,
        "artwork_url" to artworkUrl
    )
}

/**
 * System information data class.
 */
data class SystemInfo(
    @SerializedName("hostname")
    val hostname: String,
    
    @SerializedName("platform")
    val platform: String = "android",
    
    @SerializedName("platform_version")
    val platformVersion: String = android.os.Build.VERSION.RELEASE
) {
    companion object {
        fun create(): SystemInfo {
            return SystemInfo(
                hostname = android.os.Build.MODEL,
                platform = "android",
                platformVersion = android.os.Build.VERSION.RELEASE
            )
        }
    }
}

/**
 * API Response wrapper.
 */
data class ApiResponse(
    @SerializedName("system")
    val system: SystemInfo,
    
    @SerializedName("media")
    val media: MediaInfo?,
    
    @SerializedName("last_updated")
    val lastUpdated: String,
    
    @SerializedName("cached")
    val cached: Boolean = false,
    
    @SerializedName("error")
    val error: String? = null
) {
    companion object {
        private val dateFormat = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSSXXX", Locale.US)
        
        fun now(): String = dateFormat.format(Date())
    }
}

/**
 * Status response for root endpoint.
 */
data class StatusResponse(
    @SerializedName("status")
    val status: String = "running",
    
    @SerializedName("service")
    val service: String = "Media Player API",
    
    @SerializedName("version")
    val version: String = "1.0.0",
    
    @SerializedName("system")
    val system: SystemInfo,
    
    @SerializedName("provider")
    val provider: String = "NotificationListener"
)
