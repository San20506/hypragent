package com.hypragent.accessibility

import android.accessibilityservice.AccessibilityService
import android.graphics.Rect
import android.view.accessibility.AccessibilityNodeInfo
import org.json.JSONArray
import org.json.JSONObject

/**
 * TreeReader — walks the Android accessibility node tree and serializes
 * it to the MCP screen_read tool format.
 *
 * Pure I/O module: reads screen state, holds no reasoning logic.
 */
class TreeReader(private val service: AccessibilityService) {

    companion object {
        private const val DEFAULT_SPARSE_THRESHOLD = 3
    }

    var sparseThreshold: Int = DEFAULT_SPARSE_THRESHOLD

    data class TreeResult(
        val nodes: JSONArray,
        val nodeCount: Int,
        val interactiveCount: Int,
        val rootPackage: String?,
        val isWebView: Boolean,
    )

    /**
     * Read the current UI tree and serialize to JSON.
     *
     * Returns a TreeResult with the serialized nodes and metadata
     * used by the OCR fallback trigger.
     */
    fun readTree(): TreeResult {
        val root = service.rootInActiveWindow
            ?: return TreeResult(JSONArray(), 0, 0, null, false)

        val nodes = JSONArray()
        var interactiveCount = 0
        val rootPackage = root.packageName?.toString()

        fun walk(node: AccessibilityNodeInfo, depth: Int) {
            val bounds = Rect()
            node.getBoundsInScreen(bounds)

            val nodeJson = JSONObject().apply {
                put("depth", depth)
                put("class_name", node.className?.toString() ?: "")
                put("package", node.packageName?.toString() ?: "")
                put("text", node.text?.toString() ?: "")
                put("content_description", node.contentDescription?.toString() ?: "")
                put("view_id", node.viewIdResourceName ?: "")
                put("clickable", node.isClickable)
                put("scrollable", node.isScrollable)
                put("editable", node.isEditable)
                put("enabled", node.isEnabled)
                put("bounds", JSONObject().apply {
                    put("left", bounds.left)
                    put("top", bounds.top)
                    put("right", bounds.right)
                    put("bottom", bounds.bottom)
                })
            }
            nodes.put(nodeJson)

            if (node.isClickable || node.isScrollable || node.isEditable) {
                interactiveCount++
            }

            for (i in 0 until node.childCount) {
                node.getChild(i)?.let { child ->
                    walk(child, depth + 1)
                    child.recycle()
                }
            }
        }

        walk(root, 0)
        root.recycle()

        val isWebView = detectWebView(root, nodes)
        return TreeResult(nodes, nodes.length(), interactiveCount, rootPackage, isWebView)
    }

    /**
     * Serialize the tree to the MCP screen_read format.
     */
    fun toMcpFormat(result: TreeResult): JSONObject {
        return JSONObject().apply {
            put("type", "ui_tree")
            put("node_count", result.nodeCount)
            put("interactive_count", result.interactiveCount)
            put("root_package", result.rootPackage ?: "")
            put("is_webview", result.isWebView)
            put("nodes", result.nodes)
        }
    }

    /**
     * Detect if the top-level content is a WebView.
     */
    private fun detectWebView(root: AccessibilityNodeInfo, nodes: JSONArray): Boolean {
        val className = root.className?.toString() ?: ""
        if (className.contains("WebView", ignoreCase = true)) return true

        // Check first few nodes for WebView indicators
        for (i in 0 until minOf(3, nodes.length())) {
            val node = nodes.optJSONObject(i) ?: continue
            val cn = node.optString("class_name", "")
            if (cn.contains("WebView", ignoreCase = true) ||
                cn.contains("Chrome", ignoreCase = true) ||
                cn.contains("Browser", ignoreCase = true)
            ) {
                return true
            }
        }
        return false
    }

    /**
     * Determine which app package contains the given screen coordinates.
     * Used by the consent manager to resolve the target app before
     * executing a gesture.
     */
    fun resolveAppAtCoordinates(x: Int, y: Int): String? {
        val root = service.rootInActiveWindow ?: return null
        val result = findPackageAtCoordinates(root, x, y)
        root.recycle()
        return result
    }

    private fun findPackageAtCoordinates(
        node: AccessibilityNodeInfo,
        x: Int,
        y: Int,
    ): String? {
        val bounds = Rect()
        node.getBoundsInScreen(bounds)
        if (bounds.contains(x, y)) {
            val pkg = node.packageName?.toString()
            if (pkg != null) return pkg
        }
        for (i in 0 until node.childCount) {
            node.getChild(i)?.let { child ->
                val result = findPackageAtCoordinates(child, x, y)
                if (result != null) {
                    child.recycle()
                    return result
                }
                child.recycle()
            }
        }
        return null
    }
}
