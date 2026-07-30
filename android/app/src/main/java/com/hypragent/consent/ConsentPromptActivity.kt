package com.hypragent.consent

import android.content.pm.PackageManager
import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import com.hypragent.R

/**
 * ConsentPromptActivity — dialog shown when the agent needs consent
 * to act on a specific app.
 *
 * Shows the app name, requested permissions, and Allow/Deny buttons.
 */
class ConsentPromptActivity : AppCompatActivity() {

    companion object {
        const val EXTRA_APP_PACKAGE = "app_package"
        const val EXTRA_PERMISSION_TYPES = "permission_types"
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_consent_prompt)

        val appPackage = intent.getStringExtra(EXTRA_APP_PACKAGE) ?: "Unknown app"
        val permissionTypes = intent.getStringArrayExtra(EXTRA_PERMISSION_TYPES)
            ?.map { ConsentManager.PermissionType.valueOf(it) }
            ?.toSet() ?: emptySet()

        findViewById<TextView>(R.id.consent_message).text =
            getString(
                R.string.consent_message,
                resolveAppName(appPackage),
                permissionTypes.joinToString(", ") { it.name.lowercase().replace('_', ' ') },
            )

        findViewById<Button>(R.id.allow_button).setOnClickListener {
            onResult(true, appPackage, permissionTypes)
        }
        findViewById<Button>(R.id.deny_button).setOnClickListener {
            onResult(false, appPackage, permissionTypes)
        }
    }

    private fun resolveAppName(packageName: String): String {
        return try {
            val info = packageManager.getApplicationInfo(packageName, 0)
            packageManager.getApplicationLabel(info).toString()
        } catch (e: PackageManager.NameNotFoundException) {
            packageName
        }
    }

    private fun onResult(
        granted: Boolean,
        appPackage: String,
        permissionTypes: Set<ConsentManager.PermissionType>,
    ) {
        ConsentManagerHolder.instance?.onPromptResult(appPackage, granted, permissionTypes)
        finish()
    }
}

/**
 * Holder for the ConsentManager singleton.
 * In production, use dependency injection (Hilt/Koin) instead.
 */
object ConsentManagerHolder {
    var instance: ConsentManager? = null
}
