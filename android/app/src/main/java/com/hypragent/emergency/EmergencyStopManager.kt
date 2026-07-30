package com.hypragent.emergency

import android.content.Context
import android.content.Intent
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.os.VibrationEffect
import android.os.Vibrator
import android.util.Log
import android.widget.Toast
import com.hypragent.service.HyprForegroundService

/**
 * EmergencyStopManager — always-reachable kill control.
 *
 * Works independently of the WebSocket. Triggers via:
 * - Notification action (primary)
 * - Hardware button combination (configurable)
 * - Shake gesture (optional, battery-intensive)
 *
 * On stop: terminates all agent activity, revokes consent, provides feedback.
 */
class EmergencyStopManager(private val context: Context) {

    companion object {
        private const val TAG = "EmergencyStop"
        private const val SHAKE_THRESHOLD_MS = 500L
        private const val SHAKE_ACCELERATION_THRESHOLD = 15.0f
    }

    var isStopped = false
        private set

    var onStopTriggered: (() -> Unit)? = null
    var onReset: (() -> Unit)? = null

    // Shake detection (optional)
    private var shakeEnabled = false
    private var sensorManager: SensorManager? = null
    private var lastShakeTime = 0L

    /**
     * Trigger the emergency stop.
     *
     * Terminates all agent activity, revokes consent, provides feedback.
     * Works even if Layer B is unresponsive.
     */
    fun triggerStop() {
        if (isStopped) return
        isStopped = true

        Log.i(TAG, "Emergency stop triggered")

        // Stop WebSocket client
        val intent = Intent(context, HyprForegroundService::class.java).apply {
            action = HyprForegroundService.ACTION_EMERGENCY_STOP
        }
        context.startService(intent)

        // Provide feedback
        vibrate()
        showToast("Agent stopped")

        onStopTriggered?.invoke()
    }

    /**
     * Reset after emergency stop.
     */
    fun reset() {
        if (!isStopped) return
        isStopped = false

        val intent = Intent(context, HyprForegroundService::class.java).apply {
            action = HyprForegroundService.ACTION_RESTART
        }
        context.startService(intent)

        showToast("Agent reset")
        onReset?.invoke()
    }

    // ── Shake detection (optional) ──────────────────────────────────────

    /**
     * Enable shake-to-stop. Requires accelerometer polling.
     * Consumes battery — use only when explicitly enabled.
     */
    fun enableShakeDetection() {
        if (shakeEnabled) return
        shakeEnabled = true

        sensorManager = context.getSystemService(Context.SENSOR_SERVICE) as SensorManager
        val accelerometer = sensorManager?.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)
        sensorManager?.registerListener(shakeListener, accelerometer, SensorManager.SENSOR_DELAY_NORMAL)
    }

    /**
     * Disable shake detection.
     */
    fun disableShakeDetection() {
        shakeEnabled = false
        sensorManager?.unregisterListener(shakeListener)
    }

    private val shakeListener = object : SensorEventListener {
        override fun onSensorChanged(event: SensorEvent?) {
            if (!shakeEnabled || isStopped) return
            event ?: return

            val x = event.values[0]
            val y = event.values[1]
            val z = event.values[2]

            val acceleration = kotlin.math.sqrt(x * x + y * y + z * z)
            if (acceleration > SHAKE_ACCELERATION_THRESHOLD) {
                val now = System.currentTimeMillis()
                if (now - lastShakeTime > SHAKE_THRESHOLD_MS) {
                    lastShakeTime = now
                    triggerStop()
                }
            }
        }

        override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {}
    }

    // ── Feedback ────────────────────────────────────────────────────────

    private fun vibrate() {
        try {
            val vibrator = context.getSystemService(Context.VIBRATOR_SERVICE) as Vibrator
            if (vibrator.hasVibrator()) {
                vibrator.vibrate(
                    VibrationEffect.createOneShot(200, VibrationEffect.DEFAULT_AMPLITUDE)
                )
            }
        } catch (e: Exception) {
            Log.w(TAG, "Vibration failed: ${e.message}")
        }
    }

    private fun showToast(message: String) {
        Toast.makeText(context, message, Toast.LENGTH_SHORT).show()
    }
}
