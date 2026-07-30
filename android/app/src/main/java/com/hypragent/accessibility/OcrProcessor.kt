package com.hypragent.accessibility

import android.graphics.Bitmap
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.latin.TextRecognizerOptions
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

/**
 * OcrProcessor — extracts text from a screenshot bitmap via ML Kit.
 *
 * Used when the accessibility tree is insufficient (WebView, game,
 * sparse nodes) and the agent needs raw screen text.
 */
class OcrProcessor {

    private val recognizer = TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS)

    /**
     * Extract text blocks from a bitmap. Blocks for up to 10s.
     * Safe to call from the WebSocket IO thread — never the main thread.
     */
    fun extractText(bitmap: Bitmap): JSONObject {
        val latch = CountDownLatch(1)
        var result = JSONObject().put("error", "OCR timed out")

        recognizer.process(InputImage.fromBitmap(bitmap, 0))
            .addOnSuccessListener { visionText ->
                val blocks = JSONArray()
                for (block in visionText.textBlocks) {
                    blocks.put(JSONObject().apply {
                        put("text", block.text)
                        block.boundingBox?.let { box ->
                            put("bounds", JSONObject().apply {
                                put("left", box.left)
                                put("top", box.top)
                                put("right", box.right)
                                put("bottom", box.bottom)
                            })
                        }
                    })
                }
                result = JSONObject().apply {
                    put("type", "ocr_result")
                    put("full_text", visionText.text)
                    put("block_count", blocks.length())
                    put("blocks", blocks)
                }
                latch.countDown()
            }
            .addOnFailureListener { e ->
                result = JSONObject().put("error", "OCR failed: ${e.message}")
                latch.countDown()
            }

        latch.await(10, TimeUnit.SECONDS)
        return result
    }

    fun close() {
        recognizer.close()
    }
}
