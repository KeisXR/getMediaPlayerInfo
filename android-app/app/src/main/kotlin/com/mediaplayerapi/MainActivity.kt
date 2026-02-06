package com.mediaplayerapi

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import java.net.NetworkInterface

/**
 * Simple MainActivity for managing permissions and server state.
 * Uses programmatic views (no XML layout needed).
 */
class MainActivity : Activity() {
    
    private lateinit var statusText: TextView
    private lateinit var urlText: TextView
    private lateinit var permissionButton: Button
    private lateinit var serverButton: Button
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // Create simple UI programmatically
        val layout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(48, 48, 48, 48)
        }
        
        val titleText = TextView(this).apply {
            text = "Media Player API"
            textSize = 24f
            setPadding(0, 0, 0, 32)
        }
        layout.addView(titleText)
        
        statusText = TextView(this).apply {
            text = "Checking status..."
            textSize = 16f
            setPadding(0, 0, 0, 16)
        }
        layout.addView(statusText)
        
        urlText = TextView(this).apply {
            text = ""
            textSize = 14f
            setPadding(0, 0, 0, 32)
        }
        layout.addView(urlText)
        
        permissionButton = Button(this).apply {
            text = getString(R.string.grant_permission)
            setOnClickListener { requestNotificationAccess() }
        }
        layout.addView(permissionButton)
        
        serverButton = Button(this).apply {
            text = getString(R.string.start_server)
            setOnClickListener { toggleServer() }
        }
        layout.addView(serverButton)
        
        setContentView(layout)
        
        // Request notification permission for Android 13+
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
                requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 1)
            }
        }
    }
    
    override fun onResume() {
        super.onResume()
        updateUI()
    }
    
    private fun updateUI() {
        val hasNotificationAccess = MediaNotificationListener.isEnabled(this)
        val isServerRunning = MediaApiService.isRunning()
        
        permissionButton.isEnabled = !hasNotificationAccess
        permissionButton.text = if (hasNotificationAccess) "✓ Permission Granted" else getString(R.string.grant_permission)
        
        serverButton.isEnabled = hasNotificationAccess
        serverButton.text = if (isServerRunning) getString(R.string.stop_server) else getString(R.string.start_server)
        
        if (!hasNotificationAccess) {
            statusText.text = "Notification access required"
            urlText.text = "Please grant permission to read media notifications"
        } else if (isServerRunning) {
            statusText.text = "Server running"
            val ip = getDeviceIpAddress()
            urlText.text = "http://$ip:8765/now-playing"
        } else {
            statusText.text = "Server stopped"
            urlText.text = "Tap 'Start Server' to begin"
        }
    }
    
    private fun requestNotificationAccess() {
        val intent = Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS)
        startActivity(intent)
        Toast.makeText(this, "Please enable Media Player API", Toast.LENGTH_LONG).show()
    }
    
    private fun toggleServer() {
        if (MediaApiService.isRunning()) {
            MediaApiService.stop(this)
        } else {
            MediaApiService.start(this)
        }
        // Delay UI update to allow service state to change
        window.decorView.postDelayed({ updateUI() }, 500)
    }
    
    private fun getDeviceIpAddress(): String {
        try {
            NetworkInterface.getNetworkInterfaces()?.toList()?.forEach { intf ->
                intf.inetAddresses?.toList()?.forEach { addr ->
                    if (!addr.isLoopbackAddress) {
                        val hostAddress = addr.hostAddress
                        if (hostAddress != null && !hostAddress.contains(":")) {
                            return hostAddress
                        }
                    }
                }
            }
        } catch (e: Exception) {
            // Ignore
        }
        return "localhost"
    }
}
