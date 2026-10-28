package com.jvindustries.oms.weighbridge

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.jvindustries.oms.auth.AuthRepository
import com.jvindustries.oms.core.camera.CapturedEvidence
import com.jvindustries.oms.core.location.DeviceLocationProvider
import com.jvindustries.oms.core.network.DensityConfirmDto
import com.jvindustries.oms.core.network.DensityDetectDto
import com.jvindustries.oms.core.network.JvOmsApi
import com.jvindustries.oms.core.network.WeighmentConfirmDto
import com.jvindustries.oms.core.network.WeighmentDetectDto
import com.jvindustries.oms.core.network.WeighmentSummaryDto
import com.jvindustries.oms.core.network.imagePart
import com.jvindustries.oms.core.network.textPart
import com.jvindustries.oms.core.ocr.TextRecognitionHelper
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

enum class WeighStep { OVERVIEW, CAMERA, CONFIRM_WEIGHT, CONFIRM_DENSITY, DONE }

data class WeighmentUiState(
    val transactionPk: String,
    val step: WeighStep = WeighStep.OVERVIEW,
    val loading: Boolean = false,
    val error: String? = null,
    val info: String? = null,
    val summary: WeighmentSummaryDto? = null,
    val detect: WeighmentDetectDto? = null,
    val densityDetect: DensityDetectDto? = null,
    val cameraKind: String = "TARE",
    val showCamera: Boolean = false,
    val confirmedWeightText: String = "",
    val densityText: String = "",
    val tempText: String = "",
)

@HiltViewModel
class WeighmentViewModel @Inject constructor(
    savedStateHandle: SavedStateHandle,
    private val api: JvOmsApi,
    private val authRepository: AuthRepository,
    private val locationProvider: DeviceLocationProvider,
    private val ocrHelper: TextRecognitionHelper,
) : ViewModel() {

    private val transactionPk: String = checkNotNull(savedStateHandle["transactionPk"])

    private val _state = MutableStateFlow(WeighmentUiState(transactionPk = transactionPk))
    val state: StateFlow<WeighmentUiState> = _state.asStateFlow()

    init {
        refreshSummary()
    }

    fun onWeightText(v: String) = _state.update { it.copy(confirmedWeightText = v) }
    fun onDensityText(v: String) = _state.update { it.copy(densityText = v) }
    fun onTempText(v: String) = _state.update { it.copy(tempText = v) }

    private fun bearer() = authRepository.bearerOrNull() ?: error("Session expired")

    fun refreshSummary() {
        viewModelScope.launch {
            _state.update { it.copy(loading = true, error = null) }
            runCatching { api.weighmentSummary(bearer(), transactionPk) }
                .onSuccess { summary ->
                    _state.update {
                        it.copy(loading = false, summary = summary, info = "Server summary loaded.")
                    }
                }
                .onFailure { e ->
                    _state.update {
                        it.copy(
                            loading = false,
                            error = e.message ?: "Unable to load weighment summary.",
                            // Allow first tare even if summary endpoint fails before weighments exist
                            summary = it.summary,
                        )
                    }
                }
        }
    }

    fun openCamera(kind: String) {
        _state.update { it.copy(showCamera = true, cameraKind = kind, error = null) }
    }

    fun closeCamera() = _state.update { it.copy(showCamera = false) }

    fun onLiveCaptured(evidence: CapturedEvidence) {
        val kind = _state.value.cameraKind
        viewModelScope.launch {
            _state.update { it.copy(loading = true, showCamera = false, info = "OCR on TRUWEIGH / hydrometer image…") }
            runCatching {
                val g = locationProvider.currentGps()
                val ocr = ocrHelper.recognizeFile(evidence.file)
                if (kind == "DENSITY") {
                    Triple(
                        null as WeighmentDetectDto?,
                        api.detectDensity(
                            bearer(),
                            textPart(transactionPk),
                            textPart(g.lat.toString()),
                            textPart(g.lon.toString()),
                            textPart(g.accuracy_m.toString()),
                            textPart(evidence.captureSource),
                            textPart(ocr.fullText),
                            imagePart(evidence.file),
                        ),
                        ocr.fullText,
                    )
                } else {
                    Triple(
                        api.detectWeighment(
                            bearer(),
                            textPart(transactionPk),
                            textPart(kind),
                            textPart(g.lat.toString()),
                            textPart(g.lon.toString()),
                            textPart(g.accuracy_m.toString()),
                            textPart(evidence.captureSource),
                            textPart(ocr.fullText),
                            imagePart(evidence.file),
                        ),
                        null as DensityDetectDto?,
                        ocr.fullText,
                    )
                }
            }.onSuccess { (w, d, _) ->
                if (kind == "DENSITY") {
                    _state.update {
                        it.copy(
                            loading = false,
                            densityDetect = d,
                            step = WeighStep.CONFIRM_DENSITY,
                            densityText = d?.detected_density?.toString().orEmpty(),
                            tempText = d?.detected_temperature_c?.toString().orEmpty(),
                            info = d?.message,
                        )
                    }
                } else {
                    _state.update {
                        it.copy(
                            loading = false,
                            detect = w,
                            step = WeighStep.CONFIRM_WEIGHT,
                            confirmedWeightText = w?.detected_weight_kg?.toString().orEmpty(),
                            info = w?.message,
                        )
                    }
                }
            }.onFailure { e ->
                _state.update { it.copy(loading = false, error = e.message ?: "Capture/OCR failed.") }
            }
        }
    }

    fun confirmWeight() {
        val detect = _state.value.detect ?: return
        val weight = _state.value.confirmedWeightText.toDoubleOrNull()
        if (weight == null || weight <= 0) {
            _state.update { it.copy(error = "Enter a valid confirmed weight (kg).") }
            return
        }
        viewModelScope.launch {
            _state.update { it.copy(loading = true, error = null) }
            runCatching {
                val g = locationProvider.currentGps()
                api.confirmWeighment(
                    bearer(),
                    WeighmentConfirmDto(
                        transaction_pk = transactionPk,
                        kind = detect.kind,
                        photo_id = detect.photo_id ?: error("Missing photo evidence"),
                        confirmed_weight_kg = weight,
                        ocr_weight_kg = detect.detected_weight_kg,
                        ocr_confidence = detect.confidence,
                        ocr_provider = detect.provider,
                        ocr_raw_text = detect.ocr_raw_preview,
                        gps = g,
                        after_tare_mode = "LOADING",
                    ),
                )
            }.onSuccess { summary ->
                _state.update {
                    it.copy(
                        loading = false,
                        summary = summary,
                        step = WeighStep.OVERVIEW,
                        detect = null,
                        info = "Confirmed ${detect.kind}. Net is server-calculated.",
                    )
                }
            }.onFailure { e ->
                _state.update { it.copy(loading = false, error = e.message ?: "Confirm failed.") }
            }
        }
    }

    fun confirmDensity() {
        val detect = _state.value.densityDetect ?: return
        val density = _state.value.densityText.toDoubleOrNull()
        if (density == null || density <= 0) {
            _state.update { it.copy(error = "Enter a valid density (kg/L).") }
            return
        }
        viewModelScope.launch {
            _state.update { it.copy(loading = true, error = null) }
            runCatching {
                val g = locationProvider.currentGps()
                api.confirmDensity(
                    bearer(),
                    DensityConfirmDto(
                        transaction_pk = transactionPk,
                        photo_id = detect.photo_id ?: error("Missing photo evidence"),
                        confirmed_density = density,
                        confirmed_temperature_c = _state.value.tempText.toDoubleOrNull(),
                        ocr_density = detect.detected_density,
                        ocr_temperature = detect.detected_temperature_c,
                        ocr_confidence = detect.confidence,
                        ocr_provider = detect.provider,
                        ocr_raw_text = detect.ocr_raw_preview,
                        gps = g,
                    ),
                )
                api.weighmentSummary(bearer(), transactionPk)
            }.onSuccess { summary ->
                _state.update {
                    it.copy(
                        loading = false,
                        summary = summary,
                        step = WeighStep.DONE,
                        info = "Density confirmed. Calculated litres = ${summary.calculated_litres} (${summary.calculated_quantity_label}).",
                    )
                }
            }.onFailure { e ->
                _state.update { it.copy(loading = false, error = e.message ?: "Density confirm failed.") }
            }
        }
    }
}
