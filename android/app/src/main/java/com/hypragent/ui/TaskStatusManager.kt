package com.hypragent.ui

import android.content.Context
import android.content.Intent
import com.hypragent.service.HyprForegroundService

/**
 * TaskStatusManager — manages the plain-language task status display.
 *
 * Maps tool calls to human-readable descriptions and maintains
 * a brief action history. Updates the persistent notification.
 */
class TaskStatusManager(private val context: Context) {

    companion object {
        private const val MAX_HISTORY = 5
    }

    private val actionHistory = ArrayDeque<String>()

    /**
     * Update the status display with the current action.
     *
     * Maps tool names to plain language.
     */
    fun updateStatus(toolName: String, step: Int = 0) {
        val plainLanguage = toolToPlainLanguage(toolName)
        val status = if (step > 0) "Step $step: $plainLanguage" else plainLanguage

        addToHistory(status)
        updateNotification(status)
    }

    /**
     * Set idle status.
     */
    fun setIdle() {
        actionHistory.clear()
        updateNotification("Idle")
    }

    /**
     * Set error status.
     */
    fun setError(message: String) {
        updateNotification("Error: $message")
    }

    /**
     * Get the action history.
     */
    fun getHistory(): List<String> = actionHistory.toList()

    // ── Private ─────────────────────────────────────────────────────────

    private fun toolToPlainLanguage(toolName: String): String {
        return when (toolName) {
            "screen_read" -> "Reading screen..."
            "screenshot" -> "Taking screenshot..."
            "tap" -> "Tapping..."
            "swipe" -> "Swiping..."
            "long_press" -> "Long pressing..."
            "pinch" -> "Pinching..."
            "read_screen_text" -> "Extracting text from screen..."
            "ocr" -> "Extracting text from screen..."
            "file_read" -> "Reading file..."
            "file_write" -> "Writing file..."
            "file_list" -> "Listing files..."
            "file_move" -> "Moving file..."
            "file_delete" -> "Deleting file..."
            "termux_exec" -> "Running command..."
            else -> "Processing..."
        }
    }

    private fun addToHistory(action: String) {
        actionHistory.addLast(action)
        while (actionHistory.size > MAX_HISTORY) {
            actionHistory.removeFirst()
        }
    }

    private fun updateNotification(status: String) {
        val intent = Intent(context, HyprForegroundService::class.java).apply {
            action = "com.hypragent.UPDATE_STATUS"
            putExtra("status", status)
        }
        context.startService(intent)
    }
}
