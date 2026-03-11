package com.mediaplayerapi.model

import com.google.gson.annotations.SerializedName

/**
 * Media information data class.
 * Field names match the Python version's API response format.
 */
data class MediaInfo(
    @SerializedName("source_app")
    val sourceApp: String = "",

    @SerializedName("title")
    val title: String = "",

    @SerializedName("artist")
    val artist: String = "",

    @SerializedName("album")
    val album: String = "",

    @SerializedName("status")
    val status: String = "unknown",

    @SerializedName("position_ms")
    val positionMs: Long? = null,

    @SerializedName("duration_ms")
    val durationMs: Long? = null,

    @SerializedName("thumbnail")
    val thumbnail: String? = null  // Always null (copyright reasons)
) {
    val isPlaying: Boolean get() = status == "playing"

    companion object {
        fun formatTime(ms: Long): String {
            val totalSeconds = ms / 1000
            val minutes = totalSeconds / 60
            val seconds = totalSeconds % 60
            return "$minutes:${seconds.toString().padStart(2, '0')}"
        }
    }
}
