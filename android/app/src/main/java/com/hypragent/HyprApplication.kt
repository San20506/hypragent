package com.hypragent

import android.app.Application
import com.hypragent.consent.ConsentManager
import com.hypragent.consent.ConsentManagerHolder
import com.hypragent.emergency.EmergencyStopManager

/**
 * HyprApplication — process-level singletons.
 *
 * Consent grants live here (in-memory, session-scoped) so they survive
 * activity/foreground-service restarts within the process lifetime.
 */
class HyprApplication : Application() {

    lateinit var consentManager: ConsentManager
        private set
    lateinit var emergencyStop: EmergencyStopManager
        private set

    override fun onCreate() {
        super.onCreate()
        consentManager = ConsentManager(this)
        emergencyStop = EmergencyStopManager(this)
        ConsentManagerHolder.instance = consentManager
    }
}
