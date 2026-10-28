package com.jvindustries.oms.core.ocr

import android.graphics.BitmapFactory
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.latin.TextRecognizerOptions
import kotlinx.coroutines.suspendCancellableCoroutine
import java.io.File
import javax.inject.Inject
import javax.inject.Singleton
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

data class OcrScanResult(
    val fullText: String,
    val blockCount: Int,
)

@Singleton
class TextRecognitionHelper @Inject constructor() {
    private val recognizer = TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS)

    suspend fun recognizeFile(file: File): OcrScanResult {
        val bitmap = BitmapFactory.decodeFile(file.absolutePath)
            ?: throw IllegalStateException("Unable to decode captured image for OCR.")
        val image = InputImage.fromBitmap(bitmap, 0)
        return suspendCancellableCoroutine { cont ->
            recognizer.process(image)
                .addOnSuccessListener { text ->
                    cont.resume(
                        OcrScanResult(
                            fullText = text.text.trim(),
                            blockCount = text.textBlocks.size,
                        ),
                    )
                }
                .addOnFailureListener { e ->
                    cont.resumeWithException(
                        IllegalStateException("OCR failed: ${e.message ?: "unknown error"}"),
                    )
                }
        }
    }
}
