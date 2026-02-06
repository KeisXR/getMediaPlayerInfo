package com.mediaplayerapi

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import android.util.Log
import java.net.InetAddress
import java.net.NetworkInterface

/**
 * Foreground service that runs the HTTP server.
 */
class MediaApiService : Service() {
    
    companion object {
        private const val TAG = "MediaApiService"
        private const val NOTIFICATION_ID = 1
        private const val CHANNEL_ID = "media_api_server"
        private const val DEFAULT_PORT = 8765
        
        const val ACTION_START = "com.mediaplayerapi.action.START"
        const val ACTION_STOP = "com.mediaplayerapi.action.STOP"
        const val EXTRA_PORT = "port"
        
        @Volatile
        private var isRunning = false
        
        fun isRunning(): Boolean = isRunning
        
        fun start(context: Context, port: Int = DEFAULT_PORT) {
            val intent = Intent(context, MediaApiService::class.java).apply {
                action = ACTION_START
                putExtra(EXTRA_PORT, port)
            }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent)
            } else {
                context.startService(intent)
            }
        }
        
        fun stop(context: Context) {
            context.stopService(Intent(context, MediaApiService::class.java))
        }
    }
    
    private var httpServer: MediaHttpServer? = null
    private var serverPort = DEFAULT_PORT
    
    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
    }
    
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        // CRITICAL: Call startForeground IMMEDIATELY to prevent ANR/crash
        // Must be called within 5 seconds of startForegroundService()
        startForeground(NOTIFICATION_ID, createNotification("Starting..."))
        
        when (intent?.action) {
            ACTION_STOP -> {
                stopServer()
                stopForeground(STOP_FOREGROUND_REMOVE)
                stopSelf()
                return START_NOT_STICKY
            }
            ACTION_START, null -> {
                serverPort = intent?.getIntExtra(EXTRA_PORT, DEFAULT_PORT) ?: DEFAULT_PORT
                startServer()
            }
        }
        return START_STICKY
    }
    
    override fun onBind(intent: Intent?): IBinder? = null
    
    override fun onDestroy() {
        stopServer()
        super.onDestroy()
    }
    
    private fun startServer() {
        if (httpServer != null) return
        
        try {
            httpServer = MediaHttpServer(serverPort).apply {
                start()
            }
            isRunning = true
            
            val ipAddress = getDeviceIpAddress()
            Log.i(TAG, "HTTP server started on http://$ipAddress:$serverPort")
            
            // Update notification with actual IP
            val notificationManager = getSystemService(NotificationManager::class.java)
            notificationManager.notify(NOTIFICATION_ID, createNotification("http://$ipAddress:$serverPort"))
            
        } catch (e: Exception) {
            Log.e(TAG, "Failed to start HTTP server", e)
            isRunning = false
            stopSelf()
        }
    }
    
    private fun stopServer() {
        httpServer?.stop()
        httpServer = null
        isRunning = false
        Log.i(TAG, "HTTP server stopped")
    }
    
    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                getString(R.string.notification_channel_name),
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = getString(R.string.notification_channel_description)
                setShowBadge(false)
            }
            
            val notificationManager = getSystemService(NotificationManager::class.java)
            notificationManager.createNotificationChannel(channel)
        }
    }
    
    private fun createNotification(contentText: String): Notification {
        val stopIntent = Intent(this, MediaApiService::class.java).apply {
            action = ACTION_STOP
        }
        val stopPendingIntent = PendingIntent.getService(
            this, 0, stopIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        
        val openIntent = Intent(this, MainActivity::class.java)
        val openPendingIntent = PendingIntent.getActivity(
            this, 0, openIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        
        return Notification.Builder(this, CHANNEL_ID)
            .setContentTitle("Media Player API")
            .setContentText(contentText)
            .setSmallIcon(android.R.drawable.ic_media_play)
            .setContentIntent(openPendingIntent)
            .addAction(
                Notification.Action.Builder(
                    null,
                    getString(R.string.stop_server),
                    stopPendingIntent
                ).build()
            )
            .setOngoing(true)
            .build()
    }
    
    private fun getDeviceIpAddress(): String {
        try {
            NetworkInterface.getNetworkInterfaces()?.toList()?.forEach { intf ->
                intf.inetAddresses?.toList()?.forEach { addr ->
                    if (!addr.isLoopbackAddress && addr is InetAddress) {
                        val hostAddress = addr.hostAddress
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
