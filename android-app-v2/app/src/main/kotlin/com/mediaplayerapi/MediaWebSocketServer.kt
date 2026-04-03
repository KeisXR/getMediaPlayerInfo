package com.mediaplayerapi

import android.util.Log
import com.google.gson.Gson
import com.google.gson.GsonBuilder
import com.mediaplayerapi.model.ApiResponse
import com.mediaplayerapi.model.MediaInfo
import com.mediaplayerapi.model.SystemInfo
import fi.iki.elonen.NanoWSD
import fi.iki.elonen.NanoHTTPD
import java.io.IOException
import java.util.Collections

/**
 * WebSocket server that pushes real-time media updates to connected clients.
 *
 * The API is compatible with the Python version:
 *  - On connect: sends a {"type":"connected", ...} message with the current media state.
 *  - On media change: broadcasts {"type":"media_update", ...} to all clients.
 *  - Responds to "ping" text frames with "pong".
 */
class MediaWebSocketServer(port: Int = 8766) : NanoWSD(port) {

    companion object {
        private const val TAG = "MediaWebSocketServer"
    }

    private val gson: Gson = GsonBuilder().serializeNulls().create()

    /** Thread-safe set of currently connected WebSocket sessions. */
    private val clients: MutableSet<WebSocket> =
        Collections.synchronizedSet(mutableSetOf())

    override fun openWebSocket(handshake: IHTTPSession): WebSocket =
        MediaWebSocket(handshake)

    // ------------------------------------------------------------------
    // Public API
    // ------------------------------------------------------------------

    /** Broadcast a media-update message to all connected clients. */
    fun broadcastMediaUpdate(media: MediaInfo?) {
        val payload = buildMessage("media_update", media)
        val snapshot = synchronized(clients) { clients.toSet() }
        for (client in snapshot) {
            try {
                client.send(payload)
            } catch (e: IOException) {
                Log.w(TAG, "Failed to send to client, removing", e)
                clients.remove(client)
            }
        }
    }

    // ------------------------------------------------------------------
    // WebSocket session
    // ------------------------------------------------------------------

    private inner class MediaWebSocket(handshake: IHTTPSession) : WebSocket(handshake) {

        override fun onOpen() {
            clients.add(this)
            Log.d(TAG, "Client connected (total: ${clients.size})")

            // Send current media state immediately on connect
            try {
                send(buildMessage("connected", MediaSessionMonitor.getCurrentMedia()))
            } catch (e: IOException) {
                Log.w(TAG, "Failed to send initial state", e)
            }
        }

        override fun onClose(
            code: WebSocketFrame.CloseCode?,
            reason: String?,
            initiatedByRemote: Boolean,
        ) {
            clients.remove(this)
            Log.d(TAG, "Client disconnected (total: ${clients.size})")
        }

        override fun onMessage(message: WebSocketFrame) {
            if (message.textPayload?.trim() == "ping") {
                try {
                    send("pong")
                } catch (e: IOException) {
                    Log.w(TAG, "Failed to send pong", e)
                }
            }
        }

        override fun onPong(pong: WebSocketFrame?) = Unit

        override fun onException(exception: IOException) {
            Log.w(TAG, "WebSocket exception", exception)
            clients.remove(this)
        }
    }

    // ------------------------------------------------------------------
    // Helpers
    // ------------------------------------------------------------------

    private fun buildMessage(type: String, media: MediaInfo?): String {
        val response = ApiResponse(
            system = SystemInfo.create(),
            media = media,
            lastUpdated = ApiResponse.now(),
            cached = false,
        )
        val map = mapOf(
            "type" to type,
            "system" to response.system,
            "media" to response.media,
            "last_updated" to response.lastUpdated,
            "cached" to response.cached,
        )
        return gson.toJson(map)
    }
}
