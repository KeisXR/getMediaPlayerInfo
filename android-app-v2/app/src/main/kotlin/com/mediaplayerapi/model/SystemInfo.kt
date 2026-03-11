package com.mediaplayerapi.model

import com.google.gson.annotations.SerializedName

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
