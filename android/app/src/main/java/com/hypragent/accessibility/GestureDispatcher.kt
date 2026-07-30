package com.hypragent.accessibility

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.GestureDescription
import android.graphics.Path
import android.graphics.Point
import android.os.Build
import android.util.DisplayMetrics

/**
 * GestureDispatcher — takes a validated command (tap, swipe, long-press,
 * pinch) and issues the corresponding dispatchGesture call.
 *
 * Pure execution module: does not decide what to tap, only executes.
 */
class GestureDispatcher(private val service: AccessibilityService) {

    private val screenWidth: Int
    private val screenHeight: Int

    init {
        val metrics: DisplayMetrics = service.resources.displayMetrics
        screenWidth = metrics.widthPixels
        screenHeight = metrics.heightPixels
    }

    sealed class GestureResult {
        data object Success : GestureResult()
        data class Failure(val reason: String) : GestureResult()
    }

    /**
     * Validate coordinates are within screen bounds.
     */
    private fun validateCoordinates(x: Int, y: Int): GestureResult? {
        if (x < 0 || x >= screenWidth || y < 0 || y >= screenHeight) {
            return GestureResult.Failure(
                "Coordinates ($x, $y) out of screen bounds (${screenWidth}x$screenHeight)"
            )
        }
        return null
    }

    /**
     * Tap at (x, y).
     */
    fun tap(x: Int, y: Int): GestureResult {
        validateCoordinates(x, y)?.let { return it }

        val path = Path().apply { moveTo(x.toFloat(), y.toFloat()) }
        val stroke = GestureDescription.StrokeDescription(path, 0, 100)
        val gesture = GestureDescription.Builder().addStroke(stroke).build()

        return dispatchGesture(gesture, "tap")
    }

    /**
     * Swipe from (x1, y1) to (x2, y2).
     */
    fun swipe(x1: Int, y1: Int, x2: Int, y2: Int, durationMs: Long = 300): GestureResult {
        validateCoordinates(x1, y1)?.let { return it }
        validateCoordinates(x2, y2)?.let { return it }

        val path = Path().apply {
            moveTo(x1.toFloat(), y1.toFloat())
            lineTo(x2.toFloat(), y2.toFloat())
        }
        val stroke = GestureDescription.StrokeDescription(path, 0, durationMs)
        val gesture = GestureDescription.Builder().addStroke(stroke).build()

        return dispatchGesture(gesture, "swipe")
    }

    /**
     * Long-press at (x, y). Hold duration defaults to 600ms.
     */
    fun longPress(x: Int, y: Int, holdMs: Long = 600): GestureResult {
        validateCoordinates(x, y)?.let { return it }

        val path = Path().apply { moveTo(x.toFloat(), y.toFloat()) }
        val stroke = GestureDescription.StrokeDescription(path, 0, holdMs)
        val gesture = GestureDescription.Builder().addStroke(stroke).build()

        return dispatchGesture(gesture, "long_press")
    }

    /**
     * Pinch gesture centered at (x, y) with a scale factor.
     * scaleFactor > 1.0 = pinch out (zoom in), < 1.0 = pinch in (zoom out).
     */
    fun pinch(x: Int, y: Int, scaleFactor: Float): GestureResult {
        validateCoordinates(x, y)?.let { return it }

        val spread = 100f * scaleFactor
        val halfSpread = spread / 2

        val path1 = Path().apply {
            moveTo(x - 10f, y.toFloat())
            lineTo(x - halfSpread, y.toFloat())
        }
        val path2 = Path().apply {
            moveTo(x + 10f, y.toFloat())
            lineTo(x + halfSpread, y.toFloat())
        }

        val stroke1 = GestureDescription.StrokeDescription(path1, 0, 200)
        val stroke2 = GestureDescription.StrokeDescription(path2, 0, 200)

        val gesture = GestureDescription.Builder()
            .addStroke(stroke1)
            .addStroke(stroke2)
            .build()

        return dispatchGesture(gesture, "pinch")
    }

    /**
     * Dispatch the gesture to the system and wait for the real result.
     *
     * dispatchGesture is async; the command/result protocol needs the
     * actual outcome, so block on a latch until the callback fires.
     * Safe to call from the WebSocket IO thread — never the main thread.
     */
    private fun dispatchGesture(
        gesture: GestureDescription,
        gestureType: String,
    ): GestureResult {
        val latch = java.util.concurrent.CountDownLatch(1)
        var result: GestureResult = GestureResult.Failure("$gestureType timed out")

        val callback = object : AccessibilityService.GestureResultCallback() {
            override fun onCompleted(gestureDescription: GestureDescription?) {
                result = GestureResult.Success
                latch.countDown()
            }

            override fun onCancelled(gestureDescription: GestureDescription?) {
                result = GestureResult.Failure("$gestureType was cancelled by the system")
                latch.countDown()
            }
        }

        val dispatched = service.dispatchGesture(gesture, callback, null)
        if (!dispatched) {
            return GestureResult.Failure("dispatchGesture failed to initiate $gestureType")
        }

        // ponytail: 5s ceiling covers the longest supported gesture (swipe ~1s)
        latch.await(5, java.util.concurrent.TimeUnit.SECONDS)
        return result
    }
}
