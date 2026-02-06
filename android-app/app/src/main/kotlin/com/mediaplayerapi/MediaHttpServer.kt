package com.mediaplayerapi

import android.util.Log
import com.google.gson.Gson
import fi.iki.elonen.NanoHTTPD

/**
 * Lightweight HTTP server using NanoHTTPD.
 * Provides REST API compatible with the Python version.
 */
class MediaHttpServer(port: Int = 8765) : NanoHTTPD(port) {
    
    companion object {
        private const val TAG = "MediaHttpServer"
    }
    
    private val gson = Gson()
    
    override fun serve(session: IHTTPSession): Response {
        val uri = session.uri
        val method = session.method
        
        Log.d(TAG, "Request: $method $uri")
        
        return when {
            uri == "/" || uri.isEmpty() -> handleRoot()
            uri == "/now-playing" -> handleNowPlaying()
            uri == "/status" -> handleRoot()
            else -> createJsonResponse(
                Response.Status.NOT_FOUND,
                mapOf("error" to "Not found", "path" to uri)
            )
        }
    }
    
    private fun handleRoot(): Response {
        val response = StatusResponse(
            status = "running",
            service = "Media Player API",
            version = "1.0.0",
            system = SystemInfo.create(),
            provider = "NotificationListener"
        )
        
        return createJsonResponse(Response.Status.OK, response)
    }
    
    private fun handleNowPlaying(): Response {
        val media = MediaNotificationListener.getCurrentMedia()
        
        val response = ApiResponse(
            system = SystemInfo.create(),
            media = media,
            lastUpdated = ApiResponse.now(),
            cached = false
        )
        
        return createJsonResponse(Response.Status.OK, response)
    }
    
    private fun createJsonResponse(status: Response.Status, data: Any): Response {
        val json = gson.toJson(data)
        return newFixedLengthResponse(
            status,
            "application/json; charset=utf-8",
            json
        ).apply {
            addHeader("Access-Control-Allow-Origin", "*")
            addHeader("Access-Control-Allow-Methods", "GET, OPTIONS")
            addHeader("Access-Control-Allow-Headers", "Content-Type")
        }
    }
}
