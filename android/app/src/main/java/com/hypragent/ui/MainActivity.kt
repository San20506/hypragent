package com.hypragent.ui

import android.content.ComponentName
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import com.hypragent.R
import com.hypragent.service.HyprForegroundService

/**
 * MainActivity — the main entry point for the HYPR Agent app.
 *
 * Shows agent status and accessibility state, accepts task descriptions,
 * and provides controls to start/stop the service.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var statusText: TextView
    private lateinit var accessibilityStatus: TextView
    private lateinit var taskInput: EditText

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        statusText = findViewById(R.id.status_text)
        accessibilityStatus = findViewById(R.id.accessibility_status)
        taskInput = findViewById(R.id.task_input)

        findViewById<Button>(R.id.run_button).setOnClickListener { runTask() }
        findViewById<Button>(R.id.start_button).setOnClickListener { startAgent() }
        findViewById<Button>(R.id.stop_button).setOnClickListener { stopAgent() }
        findViewById<Button>(R.id.accessibility_button).setOnClickListener {
            startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))
        }

        requestNotificationPermission()
    }

    override fun onResume() {
        super.onResume()
        refreshAccessibilityStatus()
    }

    // ── Actions ─────────────────────────────────────────────────────────

    private fun runTask() {
        val task = taskInput.text.toString().trim()
        if (task.isEmpty()) return

        if (!isAccessibilityEnabled()) {
            refreshAccessibilityStatus()
            return
        }

        // Ensure the service (and WebSocket) is up, then submit the task
        startAgent()
        val intent = Intent(this, HyprForegroundService::class.java).apply {
            action = HyprForegroundService.ACTION_RUN_TASK
            putExtra(HyprForegroundService.EXTRA_TASK, task)
        }
        startService(intent)
        statusText.text = getString(R.string.notification_processing)
    }

    private fun startAgent() {
        val intent = Intent(this, HyprForegroundService::class.java).apply {
            action = HyprForegroundService.ACTION_START
        }
        startForegroundService(intent)
        statusText.text = "HYPR Agent — Starting..."
    }

    private fun stopAgent() {
        val intent = Intent(this, HyprForegroundService::class.java).apply {
            action = HyprForegroundService.ACTION_STOP
        }
        startService(intent)
        statusText.text = getString(R.string.status_idle)
    }

    // ── Permission checks ───────────────────────────────────────────────

    private fun refreshAccessibilityStatus() {
        val enabled = isAccessibilityEnabled()
        accessibilityStatus.text = getString(
            if (enabled) R.string.accessibility_enabled else R.string.accessibility_disabled,
        )
    }

    private fun isAccessibilityEnabled(): Boolean {
        val expected = ComponentName(this, com.hypragent.accessibility.HyprAccessibilityService::class.java)
        val enabledServices = Settings.Secure.getString(
            contentResolver,
            Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES,
        ) ?: return false
        return enabledServices.contains(expected.flattenToString())
    }

    private fun requestNotificationPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this, android.Manifest.permission.POST_NOTIFICATIONS)
                != PackageManager.PERMISSION_GRANTED
            ) {
                ActivityCompat.requestPermissions(
                    this,
                    arrayOf(android.Manifest.permission.POST_NOTIFICATIONS),
                    1,
                )
            }
        }
    }
}
