package com.hypragent.service

import android.content.Context
import android.content.Intent
import android.util.Log
import java.io.File
import java.util.zip.ZipInputStream

/**
 * TermuxCoreManager — manages the Termux core process lifecycle.
 *
 * Two embedding mechanisms, tried in order:
 * 1. Termux:Plugin RUN_COMMAND intent — requires the Termux app installed.
 * 2. Bundled bootstrap — extracts assets/termux_bootstrap.zip (a Termux
 *    bootstrap with python3 + deps preinstalled) into our private dir
 *    and runs the MCP server from there.
 *
 * The core runs within the app's private data directory.
 */
class TermuxCoreManager(private val context: Context) {

    companion object {
        private const val TAG = "TermuxCore"
        private const val MAX_RESTART_ATTEMPTS = 3
        private const val TERMUX_PACKAGE = "com.termux"
        private const val ENV_DIR = "termux_env"
        // ponytail: bootstrap zip must be supplied in assets (100MB+, not in repo).
        // Source: https://github.com/termux/termux-packages/releases (bootstrap zips).
    }

    private var termuxProcess: Process? = null
    private var restartAttempts = 0
    private var isRunning = false

    var onHealthCheckFailed: (() -> Unit)? = null
    var onRestartFailed: (() -> Unit)? = null

    /**
     * Start the Termux core process.
     *
     * Uses Termux:Plugin API if available, otherwise falls back to
     * bundled bootstrap in the app's private data directory.
     */
    fun start(): Boolean {
        if (isRunning) return true

        return try {
            if (startViaPluginApi()) {
                isRunning = true
                restartAttempts = 0
                Log.i(TAG, "Termux core started via plugin API")
                true
            } else {
                startViaBootstrap()
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to start Termux core: ${e.message}")
            false
        }
    }

    /**
     * Stop the Termux core process.
     */
    fun stop() {
        isRunning = false
        termuxProcess?.destroy()
        termuxProcess = null
        Log.i(TAG, "Termux core stopped")
    }

    /**
     * Check if the Termux core is alive.
     */
    fun isAlive(): Boolean {
        // The plugin-API path has no local Process handle; assume alive
        // unless the WebSocket drops (which is monitored separately).
        return isRunning && (termuxProcess?.isAlive ?: true)
    }

    /**
     * Perform a health check. If the process is dead, attempt restart.
     */
    fun healthCheck() {
        if (!isRunning) return

        if (!isAlive()) {
            Log.w(TAG, "Termux core is dead, attempting restart")
            restartAttempts++
            if (restartAttempts >= MAX_RESTART_ATTEMPTS) {
                Log.e(TAG, "Max restart attempts reached, giving up")
                onRestartFailed?.invoke()
                return
            }
            stop()
            if (!start()) {
                onHealthCheckFailed?.invoke()
            }
        }
    }

    // ── Termux RUN_COMMAND intent ───────────────────────────────────────

    /**
     * Launch the MCP server inside the installed Termux app via the
     * documented RUN_COMMAND intent protocol.
     * Requires: termux_core deployed to Termux home (see README/setup).
     */
    private fun startViaPluginApi(): Boolean {
        if (!isTermuxInstalled()) return false

        return try {
            val intent = Intent("com.termux.service_execute").apply {
                setClassName(TERMUX_PACKAGE, "com.termux.app.TermuxService")
                putExtra("com.termux.execute", "/data/data/$TERMUX_PACKAGE/files/usr/bin/python3")
                putExtra(
                    "com.termux.execute.arguments",
                    arrayOf("-m", "termux_core.mcp_server"),
                )
                putExtra(
                    "com.termux.execute.cwd",
                    "/data/data/$TERMUX_PACKAGE/files/home/hypragent",
                )
                putExtra("com.termux.execute.background", true)
            }
            context.startService(intent)
            true
        } catch (e: Exception) {
            Log.w(TAG, "RUN_COMMAND intent failed: ${e.message}")
            false
        }
    }

    private fun isTermuxInstalled(): Boolean {
        return try {
            context.packageManager.getPackageInfo(TERMUX_PACKAGE, 0)
            true
        } catch (e: Exception) {
            false
        }
    }

    // ── Bundled bootstrap ───────────────────────────────────────────────

    private fun startViaBootstrap(): Boolean {
        return try {
            val envDir = File(context.filesDir, ENV_DIR)
            if (!envDir.exists()) {
                Log.i(TAG, "Extracting Termux environment...")
                extractBootstrap(envDir)
                extractCoreSources(File(envDir, "hypragent"))
            }

            val python = File(envDir, "usr/bin/python3")
            if (!python.exists()) {
                Log.e(TAG, "python3 not found in bootstrap (asset termux_bootstrap.zip missing?)")
                return false
            }

            val workDir = File(envDir, "hypragent")
            termuxProcess = ProcessBuilder()
                .command(python.absolutePath, "-m", "termux_core.mcp_server")
                .directory(workDir)
                .redirectErrorStream(true)
                .apply {
                    environment().apply {
                        put("HOME", workDir.absolutePath)
                        put("PREFIX", File(envDir, "usr").absolutePath)
                        put("LD_LIBRARY_PATH", File(envDir, "usr/lib").absolutePath)
                        put("PATH", "${File(envDir, "usr/bin").absolutePath}:${environment()["PATH"]}")
                    }
                }
                .start()

            isRunning = true
            Log.i(TAG, "Termux core started via bootstrap")
            true
        } catch (e: Exception) {
            Log.e(TAG, "Bootstrap start failed: ${e.message}")
            false
        }
    }

    /**
     * Extract assets/termux_bootstrap.zip into the target directory,
     * restoring executable bits from the zip entries' external attributes.
     */
    private fun extractBootstrap(targetDir: File) {
        targetDir.mkdirs()
        val stream = try {
            context.assets.open("termux_bootstrap.zip")
        } catch (e: Exception) {
            Log.w(TAG, "termux_bootstrap.zip not in assets")
            return
        }

        ZipInputStream(stream).use { zis ->
            var entry = zis.nextEntry
            while (entry != null) {
                val outFile = File(targetDir, entry.name)
                if (entry.isDirectory) {
                    outFile.mkdirs()
                } else {
                    outFile.parentFile?.mkdirs()
                    outFile.outputStream().use { zis.copyTo(it) }
                    // Termux bootstrap entries carry unix mode in external attributes
                    if (entry.extra != null || entry.name.contains("/bin/")) {
                        outFile.setExecutable(true, false)
                    }
                }
                zis.closeEntry()
                entry = zis.nextEntry
            }
        }
    }

    /**
     * Copy the bundled termux_core python sources from assets to disk.
     * Updated on every start so app upgrades refresh the core code.
     */
    private fun extractCoreSources(targetDir: File) {
        listOf("termux_core", "termux_core/backends").forEach { assetDir ->
            val names = context.assets.list(assetDir) ?: return@forEach
            names.filter { it.endsWith(".py") }.forEach { name ->
                val out = File(targetDir, "$assetDir/$name")
                out.parentFile?.mkdirs()
                context.assets.open("$assetDir/$name").use { input ->
                    out.outputStream().use { input.copyTo(it) }
                }
            }
        }
    }
}
