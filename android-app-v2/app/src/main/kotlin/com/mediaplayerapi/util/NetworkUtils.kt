package com.mediaplayerapi.util

import android.util.Log
import java.net.InetAddress
import java.net.NetworkInterface

/**
 * Network utility functions.
 */
object NetworkUtils {

    private const val TAG = "NetworkUtils"

    /**
     * Get the device's local IP address (IPv4, non-loopback).
     */
    fun getDeviceIpAddress(): String {
        try {
            NetworkInterface.getNetworkInterfaces()?.toList()?.forEach { intf ->
                intf.inetAddresses?.toList()?.forEach { addr ->
                    if (!addr.isLoopbackAddress && addr is InetAddress) {
                        val hostAddress = addr.hostAddress
                        // Return IPv4 address only (exclude IPv6 which contains ':')
                        if (hostAddress != null && !hostAddress.contains(":")) {
                            return hostAddress
                        }
                    }
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error getting IP address", e)
        }
        return "localhost"
    }
}
