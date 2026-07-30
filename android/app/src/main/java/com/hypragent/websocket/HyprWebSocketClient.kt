package com.hypragent.websocket

import android.util.Log
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import org.json.JSONObject
import java.util.UUID
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.TimeUnit

/**
 * HyprWebSocketClient — Layer A's WebSocket client.
 *
 * Connects to Layer B (Termux core) WebSocket server on 127.0.0.1.
 * Handles command/result/event protocol with request-id correlation.
 *
 * Layer B = WebSocket server (listens)
 * Layer A = WebSocket client (connects)
 */
class HyprWebSocketClient(
    private val port: Int = 12345,
    var onEvent: ((JSONObject) -> Unit)? = null,
    var onConnectionStateChanged: ((Boolean) -> Unit)? = null,
    private val scope: CoroutineScope = CoroutineScope(Dispatchers.IO),
) {

    companion object {
        private const val TAG = "HyprWebSocket"
        private const val MAX_RECONNECT_ATTEMPTS = 30
        private const val RECONNECT_DELAY_MS = 2000L
        private const val HEARTBEAT_INTERVAL_MS = 30000L
        private const val HEARTBEAT_TIMEOUT_MS = 10000L
        private const val MAX_MESSAGE_SIZE = 1_000_000 // 1MB
        
        // Read-only commands safe to re-issue on reconnect (per websocket-bridge spec)
        private val READ_ONLY_COMMANDS = setOf("screen_read", "screenshot", "ocr", "read_screen_text")
    }

    private val client = OkHttpClient.Builder()
        .pingInterval(HEARTBEAT_INTERVAL_MS, TimeUnit.MILLISECONDS)
        .build()

    private var webSocket: WebSocket? = null
    private var isConnected = false
    private var isStopped = false // Set true when emergency stop is triggered

    // Pending commands awaiting results, keyed by request_id
    // Stores: action, message JSON, and callback
    private data class PendingCommand(
        val action: String,
        val message: JSONObject,
        val callback: (JSONObject) -> Unit,
    )
    private val pendingCommands = ConcurrentHashMap<String, PendingCommand>()

    /**
     * Handler for commands arriving from Layer B (tap, screen_read, ...).
     * Runs on the IO scope; blocking is acceptable. The returned payload
     * is sent back as a result with the command's request_id.
     */
    var commandHandler: ((action: String, params: JSONObject) -> JSONObject)? = null

    // ── Connection lifecycle ────────────────────────────────────────────

    fun connect() {
        if (isConnected) return
        isStopped = false

        val request = Request.Builder()
            .url("ws://127.0.0.1:$port")
            .build()

        webSocket = client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                isConnected = true
                Log.i(TAG, "WebSocket connected to 127.0.0.1:$port")
                onConnectionStateChanged?.invoke(true)
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                handleMessage(text)
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                isConnected = false
                Log.e(TAG, "WebSocket failure: ${t.message}")
                onConnectionStateChanged?.invoke(false)
                scheduleReconnect()
            }

            override fun onClosing(webSocket: WebSocket, code: Int, reason: String) {
                isConnected = false
                Log.i(TAG, "WebSocket closing: $reason")
                onConnectionStateChanged?.invoke(false)
            }
        })
    }

    fun disconnect() {
        isConnected = false
        webSocket?.close(1000, "Client disconnecting")
        webSocket = null
    }

    private fun scheduleReconnect() {
        // Filter pending commands: keep read-only, discard non-idempotent
        val toReissue = mutableMapOf<String, PendingCommand>()
        val toDiscard = mutableListOf<String>()
        
        pendingCommands.forEach { (requestId, pending) ->
            if (pending.action in READ_ONLY_COMMANDS) {
                toReissue[requestId] = pending
            } else {
                toDiscard.add(requestId)
                Log.w(TAG, "Discarding non-idempotent command on disconnect: ${pending.action} ($requestId)")
            }
        }
        
        // Discard non-idempotent commands with error callback
        toDiscard.forEach { requestId ->
            val pending = pendingCommands.remove(requestId)
            pending?.callback(JSONObject().apply {
                put("request_id", requestId)
                put("status", "error")
                put("error", "Discarded on disconnect (non-idempotent)")
            })
        }
        
        scope.launch {
            var attempts = 0
            while (!isConnected && attempts < MAX_RECONNECT_ATTEMPTS) {
                delay(RECONNECT_DELAY_MS)
                if (!isStopped) {
                    Log.i(TAG, "Reconnect attempt ${attempts + 1}/$MAX_RECONNECT_ATTEMPTS")
                    connect()
                    // Wait a bit for connection to establish
                    delay(500)
                    if (isConnected) {
                        Log.i(TAG, "Reconnected. Re-issuing ${toReissue.size} read-only commands")
                        toReissue.forEach { (requestId, pending) ->
                            webSocket?.send(pending.message.toString())
                        }
                        break
                    }
                }
                attempts++
            }
            if (!isConnected) {
                Log.e(TAG, "Failed to reconnect after $MAX_RECONNECT_ATTEMPTS attempts")
                // Reject all remaining pending commands
                pendingCommands.forEach { (requestId, pending) ->
                    pending.callback(JSONObject().apply {
                        put("request_id", requestId)
                        put("status", "error")
                        put("error", "Reconnect failed")
                    })
                }
                pendingCommands.clear()
            }
        }
    }

    // ── Message handling ────────────────────────────────────────────────

    private fun handleMessage(text: String) {
        if (text.length > MAX_MESSAGE_SIZE) {
            Log.w(TAG, "Message exceeds size limit, ignoring")
            return
        }

        try {
            val json = JSONObject(text)
            val type = json.optString("type")

            when (type) {
                "command" -> handleIncomingCommand(json)
                "result" -> handleResult(json)
                "event" -> handleEvent(json)
                else -> Log.w(TAG, "Unknown message type: $type")
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to parse message: ${e.message}")
        }
    }

    private fun handleResult(json: JSONObject) {
        val requestId = json.optString("request_id")
        val pending = pendingCommands.remove(requestId)
        if (pending != null) {
            pending.callback(json)
        } else {
            Log.w(TAG, "Received result with unknown request_id: $requestId")
        }
    }

    private fun handleEvent(json: JSONObject) {
        onEvent?.invoke(json)
    }

    /**
     * Execute a command from Layer B and send the result back.
     * Dispatches on the IO scope so blocking handlers (gestures,
     * screenshots, consent waits) don't stall the reader thread.
     */
    private fun handleIncomingCommand(json: JSONObject) {
        val requestId = json.optString("request_id")
        val action = json.optString("action")
        val params = json.optJSONObject("params") ?: JSONObject()

        scope.launch {
            val payload = when {
                isStopped -> JSONObject().apply {
                    put("status", "stopped")
                    put("error", "Emergency stop is active")
                }
                commandHandler == null -> JSONObject().apply {
                    put("status", "error")
                    put("error", "No command handler registered")
                }
                else -> try {
                    commandHandler!!.invoke(action, params)
                } catch (e: Exception) {
                    JSONObject().apply {
                        put("status", "error")
                        put("error", "Handler exception: ${e.message}")
                    }
                }
            }

            val result = JSONObject().apply {
                put("type", "result")
                put("request_id", requestId)
                payload.keys().forEach { key -> put(key, payload.get(key)) }
            }
            webSocket?.send(result.toString())
        }
    }

    // ── Sending commands ────────────────────────────────────────────────

    /**
     * Send a command to Layer B and wait for the result.
     *
     * Only read-only commands are re-issued on reconnect.
     * Non-idempotent commands (tap, swipe, keyboard_type) are discarded.
     */
    fun sendCommand(
        action: String,
        params: JSONObject = JSONObject(),
        onResult: (JSONObject) -> Unit,
    ): String {
        if (isStopped) {
            onResult(JSONObject().apply {
                put("request_id", "")
                put("status", "stopped")
                put("error", "Agent is stopped")
            })
            return ""
        }

        if (!isConnected) {
            onResult(JSONObject().apply {
                put("request_id", "")
                put("status", "error")
                put("error", "WebSocket not connected")
            })
            return ""
        }

        val requestId = UUID.randomUUID().toString()
        val message = JSONObject().apply {
            put("type", "command")
            put("request_id", requestId)
            put("action", action)
            put("params", params)
        }

        pendingCommands[requestId] = PendingCommand(action, message, onResult)

        val sent = webSocket?.send(message.toString()) ?: false
        if (!sent) {
            pendingCommands.remove(requestId)
            onResult(JSONObject().apply {
                put("request_id", requestId)
                put("status", "error")
                put("error", "Failed to send message")
            })
        }

        return requestId
    }

    /**
     * Send an event to Layer B.
     */
    fun sendEvent(eventType: String, data: JSONObject = JSONObject()) {
        if (!isConnected) return

        val message = JSONObject().apply {
            put("type", "event")
            put("event_type", eventType)
            put("data", data)
        }
        webSocket?.send(message.toString())
    }

    // ── Emergency stop integration ──────────────────────────────────────

    /**
     * Mark the client as stopped. All pending commands are rejected
     * and no new commands are accepted.
     */
    fun markStopped() {
        isStopped = true
        // Reject all pending commands
        pendingCommands.forEach { (requestId, pending) ->
            pending.callback(JSONObject().apply {
                put("request_id", requestId)
                put("status", "stopped")
                put("error", "Emergency stop triggered")
            })
        }
        pendingCommands.clear()
    }

    /**
     * Reset the stopped state to allow new commands.
     */
    fun resetStopped() {
        isStopped = false
    }
}
