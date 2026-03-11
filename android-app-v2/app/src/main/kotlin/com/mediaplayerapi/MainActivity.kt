package com.mediaplayerapi

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.drawable.GradientDrawable
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.provider.Settings
import android.view.View
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.google.android.material.button.MaterialButton
import com.google.android.material.card.MaterialCardView
import com.mediaplayerapi.model.MediaInfo
import com.mediaplayerapi.util.NetworkUtils

/**
 * Main activity for managing permissions and server state.
 * Uses XML layout with Material Design components.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var statusText: TextView
    private lateinit var statusDot: View
    private lateinit var urlText: TextView
    private lateinit var permissionButton: MaterialButton
    private lateinit var serverButton: MaterialButton
    private lateinit var nowPlayingCard: MaterialCardView
    private lateinit var mediaTitle: TextView
    private lateinit var mediaArtist: TextView
    private lateinit var mediaSource: TextView

    private val handler = Handler(Looper.getMainLooper())
    private val uiUpdateRunnable = object : Runnable {
        override fun run() {
            updateUI()
            handler.postDelayed(this, 2000)  // Update every 2 seconds
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        // Bind views
        statusText = findViewById(R.id.statusText)
        statusDot = findViewById(R.id.statusDot)
        urlText = findViewById(R.id.urlText)
        permissionButton = findViewById(R.id.permissionButton)
        serverButton = findViewById(R.id.serverButton)
        nowPlayingCard = findViewById(R.id.nowPlayingCard)
        mediaTitle = findViewById(R.id.mediaTitle)
        mediaArtist = findViewById(R.id.mediaArtist)
        mediaSource = findViewById(R.id.mediaSource)

        // Make status dot circular
        val dotDrawable = GradientDrawable().apply {
            shape = GradientDrawable.OVAL
            setColor(getColor(R.color.status_stopped))
        }
        statusDot.background = dotDrawable

        // Set up button listeners
        permissionButton.setOnClickListener { requestNotificationAccess() }
        serverButton.setOnClickListener { toggleServer() }

        // Request POST_NOTIFICATIONS permission for Android 13+
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
                requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 1)
            }
        }
    }

    override fun onResume() {
        super.onResume()
        updateUI()
        handler.postDelayed(uiUpdateRunnable, 2000)
    }

    override fun onPause() {
        super.onPause()
        handler.removeCallbacks(uiUpdateRunnable)
    }

    private fun updateUI() {
        val hasNotificationAccess = MediaSessionMonitor.isEnabled(this)
        val isServerRunning = MediaApiService.isRunning()

        // Permission button
        permissionButton.isEnabled = !hasNotificationAccess
        permissionButton.text = if (hasNotificationAccess) {
            getString(R.string.permission_granted)
        } else {
            getString(R.string.grant_permission)
        }

        // Server button
        serverButton.isEnabled = hasNotificationAccess
        serverButton.text = if (isServerRunning) {
            getString(R.string.stop_server)
        } else {
            getString(R.string.start_server)
        }

        // Status indicator
        val dotDrawable = statusDot.background as? GradientDrawable
        if (!hasNotificationAccess) {
            statusText.text = getString(R.string.status_need_permission)
            urlText.text = getString(R.string.hint_grant_permission)
            dotDrawable?.setColor(getColor(R.color.status_stopped))
        } else if (isServerRunning) {
            statusText.text = getString(R.string.status_server_running)
            val ip = NetworkUtils.getDeviceIpAddress()
            urlText.text = "http://$ip:8765/now-playing"
            dotDrawable?.setColor(getColor(R.color.status_running))
        } else {
            statusText.text = getString(R.string.status_server_stopped)
            urlText.text = getString(R.string.hint_start_server)
            dotDrawable?.setColor(getColor(R.color.status_stopped))
        }

        // Now Playing card
        updateNowPlayingCard()
    }

    private fun updateNowPlayingCard() {
        val media = MediaSessionMonitor.getCurrentMedia()
        if (media != null && media.title.isNotEmpty()) {
            nowPlayingCard.visibility = View.VISIBLE
            mediaTitle.text = media.title
            mediaArtist.text = buildString {
                append(media.artist)
                if (media.album.isNotEmpty()) {
                    if (media.artist.isNotEmpty()) append(" — ")
                    append(media.album)
                }
            }

            // Show source app package name (could be prettified)
            val statusIcon = when (media.status) {
                "playing" -> "▶"
                "paused" -> "⏸"
                else -> "⏹"
            }
            mediaSource.text = "$statusIcon ${formatPackageName(media.sourceApp)}"

        } else {
            nowPlayingCard.visibility = View.GONE
        }
    }

    private fun formatPackageName(packageName: String): String {
        // Extract a readable name from package name
        return packageName.split(".").lastOrNull() ?: packageName
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
        handler.postDelayed({ updateUI() }, 500)
    }
}
