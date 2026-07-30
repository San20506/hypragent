package com.hypragent.accessibility

/**
 * OcrFallbackTrigger — decides when the tree read is insufficient and
 * requests a raw screenshot for OCR.
 *
 * Bridge between the accessibility service and the OCR engine.
 */
class OcrFallbackTrigger(
    private val sparseThreshold: Int = DEFAULT_SPARSE_THRESHOLD,
) {

    companion object {
        private const val DEFAULT_SPARSE_THRESHOLD = 3
    }

    /**
     * Determine if OCR fallback is needed based on the tree read result.
     *
     * Returns true if:
     * - The node tree is empty (0 or 1 nodes)
     * - The node tree is sparse (below threshold) OR has zero interactive nodes
     * - The content is a WebView
     *
     * Returns false if the tree is rich enough to use directly.
     */
    fun shouldFallback(result: TreeReader.TreeResult): Boolean {
        // Empty tree
        if (result.nodeCount <= 1) return true

        // Sparse tree (below threshold) or no interactive elements
        if (result.nodeCount < sparseThreshold || result.interactiveCount == 0) return true

        // WebView content
        if (result.isWebView) return true

        return false
    }

    /**
     * Get a human-readable reason for the fallback decision.
     * Useful for logging and status display.
     */
    fun fallbackReason(result: TreeReader.TreeResult): String {
        return when {
            result.nodeCount <= 1 -> "empty_node_tree"
            result.nodeCount < sparseThreshold -> "sparse_node_tree (${result.nodeCount} nodes)"
            result.interactiveCount == 0 -> "no_interactive_nodes (${result.nodeCount} nodes, 0 interactive)"
            result.isWebView -> "webview_content"
            else -> "no_fallback"
        }
    }
}
