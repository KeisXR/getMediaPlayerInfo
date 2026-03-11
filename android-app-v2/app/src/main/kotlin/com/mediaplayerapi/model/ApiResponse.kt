package com.mediaplayerapi.model

import com.google.gson.annotations.SerializedName
import java.text.SimpleDateFormat
import java.util.*

/**
 * API Response wrappers matching the Python version's format.
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
    val version: String = "2.0.0",

    @SerializedName("system")
    val system: SystemInfo,

    @SerializedName("provider")
    val provider: String = "MediaSession",

    @SerializedName("cache_ttl_seconds")
    val cacheTtlSeconds: Int = 30
)
