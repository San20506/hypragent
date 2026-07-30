package com.hypragent.consent

import android.content.Context
import android.content.Intent
import android.util.Log
import java.util.concurrent.ConcurrentHashMap

/**
 * ConsentManager — manages user consent with a session-grant model.
 *
 * Grants are per app + per permission type. Stored in memory only.
 * Prompts queue sequentially when multiple apps need consent.
 */
class ConsentManager(private val context: Context) {

    companion object {
        private const val TAG = "ConsentManager"
    }

    // Permission types
    enum class PermissionType { SCREEN_READ, GESTURE_CONTROL, FILE_ACCESS, TERMINAL_EXEC }

    // A single grant: app package -> set of permission types
    private val grants = ConcurrentHashMap<String, MutableSet<PermissionType>>()

    // Pending consent requests (queued when multiple apps need consent)
    private val pendingRequests = ArrayDeque<ConsentRequest>()

    // Whether the consent prompt is currently showing
    private var isPromptShowing = false

    var onConsentChanged: ((String, Set<PermissionType>) -> Unit)? = null
    var onConsentRevoked: (() -> Unit)? = null

    data class ConsentRequest(
        val appPackage: String,
        val permissionTypes: Set<PermissionType>,
        val callback: (Boolean) -> Unit,
    )

    /**
     * Check if consent is granted for the given app and permission type.
     */
    fun hasConsent(appPackage: String, permissionType: PermissionType): Boolean {
        return grants[appPackage]?.contains(permissionType) == true
    }

    /**
     * Check if consent is granted for the given app and any of the given permission types.
     */
    fun hasAnyConsent(appPackage: String, permissionTypes: Set<PermissionType>): Boolean {
        val appGrants = grants[appPackage] ?: return false
        return permissionTypes.any { it in appGrants }
    }

    /**
     * Request consent for the given app and permission types.
     * If consent is already granted, calls back immediately.
     * If not, queues the request and shows the prompt.
     */
    fun requestConsent(
        appPackage: String,
        permissionTypes: Set<PermissionType>,
        callback: (Boolean) -> Unit,
    ) {
        // Already granted?
        if (permissionTypes.all { hasConsent(appPackage, it) }) {
            callback(true)
            return
        }

        // Queue the request
        val request = ConsentRequest(appPackage, permissionTypes, callback)
        pendingRequests.addLast(request)

        // Show prompt if not already showing
        if (!isPromptShowing) {
            showNextPrompt()
        }
    }

    /**
     * Grant consent for the given app and permission types.
     */
    fun grantConsent(appPackage: String, permissionTypes: Set<PermissionType>) {
        val appGrants = grants.getOrPut(appPackage) { mutableSetOf() }
        appGrants.addAll(permissionTypes)
        Log.i(TAG, "Consent granted for $appPackage: $permissionTypes")
        onConsentChanged?.invoke(appPackage, appGrants)
    }

    /**
     * Deny consent for the given app.
     */
    fun denyConsent(appPackage: String) {
        Log.i(TAG, "Consent denied for $appPackage")
    }

    /**
     * Revoke all consent grants.
     */
    fun revokeAll() {
        Log.i(TAG, "All consent revoked")
        grants.clear()
        onConsentRevoked?.invoke()
    }

    /**
     * Revoke consent for a specific app.
     */
    fun revokeApp(appPackage: String) {
        Log.i(TAG, "Consent revoked for $appPackage")
        grants.remove(appPackage)
    }

    /**
     * Get all active grants.
     */
    fun getAllGrants(): Map<String, Set<PermissionType>> {
        return grants.mapValues { it.value.toSet() }
    }

    /**
     * Clear all grants (called on session end).
     */
    fun clearAll() {
        grants.clear()
        pendingRequests.clear()
        isPromptShowing = false
    }

    // ── Prompt queue ────────────────────────────────────────────────────

    private fun showNextPrompt() {
        val request = pendingRequests.firstOrNull() ?: run {
            isPromptShowing = false
            return
        }

        isPromptShowing = true

        val intent = Intent(context, ConsentPromptActivity::class.java).apply {
            putExtra(ConsentPromptActivity.EXTRA_APP_PACKAGE, request.appPackage)
            putExtra(
                ConsentPromptActivity.EXTRA_PERMISSION_TYPES,
                request.permissionTypes.map { it.name }.toTypedArray(),
            )
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        context.startActivity(intent)
    }

    /**
     * Called by ConsentPromptActivity when the user responds.
     */
    fun onPromptResult(appPackage: String, granted: Boolean, permissionTypes: Set<PermissionType>) {
        val request = pendingRequests.firstOrNull()
        if (request != null && request.appPackage == appPackage) {
            pendingRequests.removeFirst()
            if (granted) {
                grantConsent(appPackage, permissionTypes)
            } else {
                denyConsent(appPackage)
            }
            request.callback(granted)
        }

        isPromptShowing = false
        showNextPrompt()
    }
}
