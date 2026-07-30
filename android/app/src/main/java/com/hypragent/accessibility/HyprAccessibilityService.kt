package com.hypragent.accessibility

import android.accessibilityservice.AccessibilityService
import android.graphics.Bitmap
import android.util.Base64
import android.util.Log
import android.view.Display
import android.view.accessibility.AccessibilityEvent
import com.hypragent.consent.ConsentManager
import com.hypragent.consent.ConsentManagerHolder
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

/**
 * HyprAccessibilityService — the main Accessibility Service.
 *
 * Composes TreeReader, GestureDispatcher, OcrFallbackTrigger, and
 * OcrProcessor. Routes WebSocket commands from Layer B to the right
 * component and returns structured results.
 *
 * Lifecycle:
 * - onServiceConnected: service is bound, initialize components
 * - onAccessibilityEvent: screen content changed (not used for commands)
 * - onInterrupt: system interrupted the service
 */
class HyprAccessibilityService : AccessibilityService() {

    companion object {
        private const val TAG = "HyprAccessibility"
        private const val CONSENT_WAIT_S = 25L
        private const val CAPTURE_WAIT_S = 10L
        var instance: HyprAccessibilityService? = null
            private set
    }

    lateinit var treeReader: TreeReader
        private set
    lateinit var gestureDispatcher: GestureDispatcher
        private set
    lateinit var ocrFallback: OcrFallbackTrigger
        private set
    private var ocrProcessor: OcrProcessor? = null

    /** Set false on emergency stop — all commands rejected until reset. */
    @Volatile
    var commandEnabled: Boolean = true

    override fun onServiceConnected() {
        super.onServiceConnected()
        instance = this
        treeReader = TreeReader(this)
        gestureDispatcher = GestureDispatcher(this)
        ocrFallback = OcrFallbackTrigger()
        Log.i(TAG, "Accessibility service connected")
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        // Screen content changed — not required for the command/result flow
    }

    override fun onInterrupt() {
        Log.w(TAG, "Accessibility service interrupted")
    }

    override fun onDestroy() {
        instance = null
        ocrProcessor?.close()
        ocrProcessor = null
        super.onDestroy()
        Log.i(TAG, "Accessibility service destroyed")
    }

    // ── Command router ──────────────────────────────────────────────────

    /**
     * Route a command from Layer B to the right component.
     * Called from the WebSocket IO thread — blocking is acceptable here.
     *
     * Returns a result payload: {status, result?, error?}. The WebSocket
     * client wraps it with the request_id.
     */
    fun handleCommand(action: String, params: JSONObject): JSONObject {
        if (!commandEnabled) {
            return JSONObject().apply {
                put("status", "stopped")
                put("error", "Emergency stop is active")
            }
        }

        return try {
            when (action) {
                "screen_read" -> ok(readScreen())
                "screenshot" -> ok(captureScreenshotJson())
                "read_screen_text" -> ok(readScreenText())
                "tap" -> gestureResult(
                    "tap",
                    { gestureDispatcher.tap(params.getInt("x"), params.getInt("y")) },
                    params.getInt("x"), params.getInt("y"),
                )
                "long_press" -> gestureResult(
                    "long_press",
                    {
                        gestureDispatcher.longPress(
                            params.getInt("x"), params.getInt("y"),
                            params.optLong("hold_ms", 600),
                        )
                    },
                    params.getInt("x"), params.getInt("y"),
                )
                "swipe" -> gestureResult(
                    "swipe",
                    {
                        gestureDispatcher.swipe(
                            params.getInt("x1"), params.getInt("y1"),
                            params.getInt("x2"), params.getInt("y2"),
                            params.optLong("duration_ms", 300),
                        )
                    },
                    params.getInt("x1"), params.getInt("y1"),
                )
                "pinch" -> gestureResult(
                    "pinch",
                    {
                        gestureDispatcher.pinch(
                            params.getInt("x"), params.getInt("y"),
                            params.getDouble("scale_factor").toFloat(),
                        )
                    },
                    params.getInt("x"), params.getInt("y"),
                )
                else -> JSONObject().apply {
                    put("status", "error")
                    put("error", "Unknown action: $action")
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Command $action failed: ${e.message}")
            JSONObject().apply {
                put("status", "error")
                put("error", "$action failed: ${e.message}")
            }
        }
    }

    private fun ok(payload: JSONObject): JSONObject =
        JSONObject().apply {
            put("status", "ok")
            put("result", payload)
        }

    // ── Gestures with consent gate ──────────────────────────────────────

    private fun gestureResult(
        gestureType: String,
        execute: () -> GestureDispatcher.GestureResult,
        x: Int,
        y: Int,
    ): JSONObject {
        val appPackage = resolveAppAtCoordinates(x, y) ?: "unknown"
        if (!ensureConsent(appPackage, ConsentManager.PermissionType.GESTURE_CONTROL)) {
            return JSONObject().apply {
                put("status", "consent_denied")
                put("error", "Consent not granted for $appPackage")
            }
        }

        return when (val result = execute()) {
            is GestureDispatcher.GestureResult.Success -> ok(
                JSONObject().apply {
                    put("gesture", gestureType)
                    put("target_app", appPackage)
                },
            )
            is GestureDispatcher.GestureResult.Failure -> JSONObject().apply {
                put("status", "error")
                put("error", result.reason)
            }
        }
    }

    /**
     * Check consent for the app; if missing, prompt the user and block
     * (up to CONSENT_WAIT_S) until they respond. Returns true if granted.
     */
    private fun ensureConsent(
        appPackage: String,
        type: ConsentManager.PermissionType,
    ): Boolean {
        val consent = ConsentManagerHolder.instance ?: return false
        if (consent.hasConsent(appPackage, type)) return true

        val latch = CountDownLatch(1)
        var granted = false
        consent.requestConsent(appPackage, setOf(type)) { result ->
            granted = result
            latch.countDown()
        }
        latch.await(CONSENT_WAIT_S, TimeUnit.SECONDS)
        return granted
    }

    // ── Screen reading ──────────────────────────────────────────────────

    /**
     * Read the current UI tree and return it in MCP format.
     * Falls back to OCR metadata if the tree is insufficient.
     */
    fun readScreen(): JSONObject {
        val treeResult = treeReader.readTree()
        val shouldFallback = ocrFallback.shouldFallback(treeResult)

        return if (shouldFallback) {
            val reason = ocrFallback.fallbackReason(treeResult)
            JSONObject().apply {
                put("type", "ocr_fallback")
                put("fallback_reason", reason)
                put("requires_screenshot", true)
                put("tree", treeReader.toMcpFormat(treeResult))
            }
        } else {
            treeReader.toMcpFormat(treeResult)
        }
    }

    /**
     * Extract text from the screen via screenshot + OCR.
     */
    private fun readScreenText(): JSONObject {
        val bitmap = captureBitmap()
            ?: return JSONObject().put("error", "screenshot capture failed")
        val ocr = ocrProcessor ?: OcrProcessor().also { ocrProcessor = it }
        val result = ocr.extractText(bitmap)
        bitmap.recycle()
        return result
    }

    /**
     * Take a screenshot and return it as base64 PNG JSON.
     */
    private fun captureScreenshotJson(): JSONObject {
        val bitmap = captureBitmap()
            ?: return JSONObject().put("error", "screenshot capture failed")

        val stream = ByteArrayOutputStream()
        bitmap.compress(Bitmap.CompressFormat.PNG, 100, stream)
        val result = JSONObject().apply {
            put("type", "screenshot")
            put("format", "png_base64")
            put("width", bitmap.width)
            put("height", bitmap.height)
            put("data", Base64.encodeToString(stream.toByteArray(), Base64.NO_WRAP))
        }
        bitmap.recycle()
        return result
    }

    /**
     * Capture the screen as a software Bitmap via the accessibility
     * screenshot API (API 30+; minSdk is 30). Blocks up to CAPTURE_WAIT_S.
     */
    private fun captureBitmap(): Bitmap? {
        val latch = CountDownLatch(1)
        var bitmap: Bitmap? = null

        takeScreenshot(
            Display.DEFAULT_DISPLAY,
            mainExecutor,
            object : TakeScreenshotCallback {
                override fun onSuccess(screenshot: ScreenshotResult) {
                    val hardware = Bitmap.wrapHardwareBuffer(
                        screenshot.hardwareBuffer, screenshot.colorSpace,
                    )
                    screenshot.hardwareBuffer.close()
                    bitmap = hardware?.copy(Bitmap.Config.ARGB_8888, false)
                    hardware?.recycle()
                    latch.countDown()
                }

                override fun onFailure(errorCode: Int) {
                    Log.e(TAG, "Screenshot failed with code $errorCode")
                    latch.countDown()
                }
            },
        )

        latch.await(CAPTURE_WAIT_S, TimeUnit.SECONDS)
        return bitmap
    }

    /**
     * Resolve the target app package at given screen coordinates.
     * Used by the consent manager before executing a gesture.
     */
    fun resolveAppAtCoordinates(x: Int, y: Int): String? {
        return treeReader.resolveAppAtCoordinates(x, y)
    }
}
