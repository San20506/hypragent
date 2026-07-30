package com.hypragent.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import androidx.core.app.NotificationCompat
import com.hypragent.R
import com.hypragent.accessibility.HyprAccessibilityService
import com.hypragent.ui.TaskStatusManager
import com.hypragent.websocket.HyprWebSocketClient

/**
 * HyprForegroundService — keeps the Termux core alive in the background.
 *
 * Distinct from the Accessibility Service so failures are diagnosable:
 * if this service dies, it's the process-killer issue; if the accessibility
 * service dies, it's the gesture/tree-read issue.
 *
 * Lifecycle:
 * - onCreate: initialize Termux core manager + status manager
 * - onStartCommand: start foreground with notification, connect WebSocket
 * - onDestroy: stop Termux core, disconnect WebSocket, cancel health checks
 */
class HyprForegroundService : Service() {

    companion object {
        private const val TAG = "HyprForeground"
        private const val NOTIFICATION_ID = 1
        private const val HEALTH_CHECK_INTERVAL_MS = 30_000L
        const val ACTION_START = "com.hypragent.START"
        const val ACTION_STOP = "com.hypragent.STOP"
        const val ACTION_EMERGENCY_STOP = "com.hypragent.EMERGENCY_STOP"
        const val ACTION_REVOKE_CONSENT = "com.hypragent.REVOKE_CONSENT"
        const val ACTION_RESTART = "com.hypragent.RESTART"
        const val ACTION_RUN_TASK = "com.hypragent.RUN_TASK"
        const val ACTION_UPDATE_STATUS = "com.hypragent.UPDATE_STATUS"
        const val EXTRA_TASK = "task"
        const val EXTRA_STATUS = "status"
    }

    private lateinit var termuxCore: TermuxCoreManager
    private lateinit var statusManager: TaskStatusManager
    private val healthHandler = Handler(Looper.getMainLooper())
    var webSocketClient: HyprWebSocketClient? = null
    private var currentStatus: String = "Idle"

    private val healthCheckRunnable = object : Runnable {
        override fun run() {
            termuxCore.healthCheck()
            healthHandler.postDelayed(this, HEALTH_CHECK_INTERVAL_MS)
        }
    }

    override fun onCreate() {
        super.onCreate()
        termuxCore = TermuxCoreManager(this)
        statusManager = TaskStatusManager(this)
        createNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_START -> startForeground()
            ACTION_STOP -> stopSelf()
            ACTION_EMERGENCY_STOP -> handleEmergencyStop()
            ACTION_REVOKE_CONSENT -> handleRevokeConsent()
            ACTION_RESTART -> handleRestart()
            ACTION_RUN_TASK -> handleRunTask(intent?.getStringExtra(EXTRA_TASK))
            ACTION_UPDATE_STATUS -> updateStatus(
                intent?.getStringExtra(EXTRA_STATUS) ?: currentStatus,
            )
            else -> startForeground()
        }
        return START_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        healthHandler.removeCallbacks(healthCheckRunnable)
        termuxCore.stop()
        webSocketClient?.disconnect()
        super.onDestroy()
    }

    // ── Foreground management ───────────────────────────────────────────

    private fun startForeground() {
        val notification = buildNotification(currentStatus)
        startForeground(NOTIFICATION_ID, notification)

        // Start Termux core
        if (termuxCore.start()) {
            updateStatus("Termux core running")
        } else {
            updateStatus("Failed to start Termux core")
        }

        // Periodic health check for the Termux core process
        healthHandler.removeCallbacks(healthCheckRunnable)
        healthHandler.postDelayed(healthCheckRunnable, HEALTH_CHECK_INTERVAL_MS)

        // Connect WebSocket
        connectWebSocket()
    }

    private fun connectWebSocket() {
        webSocketClient = HyprWebSocketClient(
            onEvent = { event -> handleEvent(event) },
            onConnectionStateChanged = { connected ->
                updateStatus(if (connected) "Connected" else "Disconnected")
            },
        ).apply {
            // Route Layer B commands to the accessibility service
            commandHandler = handler@{ action, params ->
                val service = HyprAccessibilityService.instance
                    ?: return@handler org.json.JSONObject().apply {
                        put("status", "error")
                        put("error", "Accessibility service not connected")
                    }
                service.handleCommand(action, params)
            }
            connect()
        }
    }

    // ── Notification ────────────────────────────────────────────────────

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                getString(R.string.notification_channel_id),
                getString(R.string.notification_channel_name),
                NotificationManager.IMPORTANCE_LOW,
            ).apply {
                description = "HYPR Agent status and controls"
                setShowBadge(false)
            }
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(channel)
        }
    }

    private fun buildNotification(status: String): Notification {
        val stopIntent = PendingIntent.getService(
            this, 0,
            Intent(this, HyprForegroundService::class.java).setAction(ACTION_EMERGENCY_STOP),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        val revokeIntent = PendingIntent.getService(
            this, 1,
            Intent(this, HyprForegroundService::class.java).setAction(ACTION_REVOKE_CONSENT),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )

        return NotificationCompat.Builder(this, getString(R.string.notification_channel_id))
            .setContentTitle(getString(R.string.notification_title))
            .setContentText(status)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setOngoing(true) // Not dismissible
            .addAction(android.R.drawable.ic_media_pause, getString(R.string.action_stop), stopIntent)
            .addAction(android.R.drawable.ic_delete, getString(R.string.action_revoke_consent), revokeIntent)
            .build()
    }

    fun updateStatus(status: String) {
        currentStatus = status
        val manager = getSystemService(NotificationManager::class.java)
        manager.notify(NOTIFICATION_ID, buildNotification(status))
    }

    // ── Action handlers ─────────────────────────────────────────────────

    private fun handleEmergencyStop() {
        HyprAccessibilityService.instance?.commandEnabled = false
        webSocketClient?.markStopped()
        webSocketClient?.sendEvent("emergency_stop")
        updateStatus(getString(R.string.notification_stopped))
    }

    private fun handleRevokeConsent() {
        webSocketClient?.sendEvent("consent_revoked")
        updateStatus("Consent revoked")
    }

    private fun handleRestart() {
        HyprAccessibilityService.instance?.commandEnabled = true
        webSocketClient?.resetStopped()
        webSocketClient?.sendEvent("agent_reset")
        statusManager.setIdle()
    }

    private fun handleRunTask(task: String?) {
        if (task.isNullOrBlank()) return
        webSocketClient?.sendEvent(
            "task_submitted",
            org.json.JSONObject().put("task", task),
        )
        updateStatus("Task submitted")
    }

    private fun handleEvent(event: org.json.JSONObject) {
        val eventType = event.optString("event_type")
        when (eventType) {
            "task_started" -> statusManager.updateStatus("task_started")
            "task_completed" -> statusManager.setIdle()
            "task_failed" -> statusManager.setError(
                event.optJSONObject("data")?.optString("error") ?: "unknown",
            )
            "tool_call" -> statusManager.updateStatus(
                event.optJSONObject("data")?.optString("tool") ?: "processing",
                event.optJSONObject("data")?.optInt("step") ?: 0,
            )
        }
    }
}
