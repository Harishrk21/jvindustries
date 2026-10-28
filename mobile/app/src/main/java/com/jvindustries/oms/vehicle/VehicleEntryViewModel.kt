package com.jvindustries.oms.vehicle

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.jvindustries.oms.auth.AuthRepository
import com.jvindustries.oms.core.camera.CapturedEvidence
import com.jvindustries.oms.core.location.DeviceLocationProvider
import com.jvindustries.oms.core.network.AnprConfirmRequestDto
import com.jvindustries.oms.core.network.AnprResultDto
import com.jvindustries.oms.core.network.DriverDetailsRequestDto
import com.jvindustries.oms.core.network.GatePassCreateRequestDto
import com.jvindustries.oms.core.network.GatePassDto
import com.jvindustries.oms.core.network.GpsDto
import com.jvindustries.oms.core.network.JvOmsApi
import com.jvindustries.oms.core.network.VehicleEntryStartRequest
import com.jvindustries.oms.core.network.VehicleExitConfirmDto
import com.jvindustries.oms.core.network.VehicleTxnDto
import com.jvindustries.oms.core.network.imagePart
import com.jvindustries.oms.core.network.textPart
import com.jvindustries.oms.core.ocr.TextRecognitionHelper
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.util.UUID
import javax.inject.Inject

enum class VehicleStep {
    START, CAPTURE, ANPR, DRIVER, GATE_PASS, EXIT_CAPTURE, DONE
}

data class VehicleEntryUiState(
    val step: VehicleStep = VehicleStep.START,
    val loading: Boolean = false,
    val error: String? = null,
    val txn: VehicleTxnDto? = null,
    val anpr: AnprResultDto? = null,
    val exitAnpr: AnprResultDto? = null,
    val manualPlate: String = "",
    val manualReason: String = "",
    val driverName: String = "",
    val driverMobile: String = "",
    val transporter: String = "",
    val gatePass: GatePassDto? = null,
    val info: String? = null,
    val showCamera: Boolean = false,
    val cameraMode: String = "ENTRY",
)

@HiltViewModel
class VehicleEntryViewModel @Inject constructor(
    private val api: JvOmsApi,
    private val authRepository: AuthRepository,
    private val locationProvider: DeviceLocationProvider,
    private val ocrHelper: TextRecognitionHelper,
) : ViewModel() {

    private val _state = MutableStateFlow(VehicleEntryUiState())
    val state: StateFlow<VehicleEntryUiState> = _state.asStateFlow()

    fun onManualPlate(v: String) = _state.update { it.copy(manualPlate = v, error = null) }
    fun onManualReason(v: String) = _state.update { it.copy(manualReason = v, error = null) }
    fun onDriverName(v: String) = _state.update { it.copy(driverName = v) }
    fun onDriverMobile(v: String) = _state.update { it.copy(driverMobile = v) }
    fun onTransporter(v: String) = _state.update { it.copy(transporter = v) }

    private fun bearer(): String =
        authRepository.bearerOrNull() ?: error("Session expired")

    private suspend fun gps(): GpsDto = locationProvider.currentGps()

    fun startEntry(type: String = "MATERIAL_LOADING_OUTWARD") {
        viewModelScope.launch {
            _state.update { it.copy(loading = true, error = null) }
            runCatching {
                val g = gps()
                api.startVehicleEntry(
                    bearer(),
                    VehicleEntryStartRequest(
                        client_transaction_id = UUID.randomUUID().toString(),
                        type = type,
                        gps = g,
                    ),
                )
            }.onSuccess { txn ->
                _state.update {
                    it.copy(
                        loading = false,
                        txn = txn,
                        step = VehicleStep.CAPTURE,
                        info = "GPS verified on premises. Capture a LIVE vehicle photograph.",
                    )
                }
            }.onFailure { e ->
                _state.update { it.copy(loading = false, error = friendly(e)) }
            }
        }
    }

    fun openLiveCamera(mode: String = "ENTRY") {
        _state.update { it.copy(showCamera = true, cameraMode = mode, error = null) }
    }

    fun closeCamera() = _state.update { it.copy(showCamera = false) }

    fun onLiveCaptured(evidence: CapturedEvidence) {
        val txn = _state.value.txn ?: return
        val mode = _state.value.cameraMode
        viewModelScope.launch {
            _state.update { it.copy(loading = true, showCamera = false, error = null, info = "Running on-device OCR…") }
            runCatching {
                val g = gps()
                val ocr = ocrHelper.recognizeFile(evidence.file)
                if (mode == "EXIT") {
                    api.exitDetect(
                        bearer(),
                        textPart(txn.id),
                        textPart(g.lat.toString()),
                        textPart(g.lon.toString()),
                        textPart(g.accuracy_m.toString()),
                        textPart(evidence.captureSource),
                        textPart(ocr.fullText),
                        imagePart(evidence.file),
                    ) to g
                } else {
                    api.runAnpr(
                        bearer(),
                        textPart(txn.id),
                        textPart(g.lat.toString()),
                        textPart(g.lon.toString()),
                        textPart(g.accuracy_m.toString()),
                        textPart(evidence.captureSource),
                        textPart(ocr.fullText),
                        imagePart(evidence.file),
                    ) to g
                }
            }.onSuccess { (anpr, _) ->
                if (mode == "EXIT") {
                    _state.update {
                        it.copy(
                            loading = false,
                            exitAnpr = anpr,
                            step = VehicleStep.EXIT_CAPTURE,
                            info = anpr.message,
                        )
                    }
                    // auto-confirm exit after successful detect if plate matches / not mismatch
                    confirmExit()
                } else {
                    _state.update {
                        it.copy(
                            loading = false,
                            anpr = anpr,
                            step = VehicleStep.ANPR,
                            manualPlate = anpr.vehicle_number.orEmpty(),
                            info = anpr.message,
                        )
                    }
                }
            }.onFailure { e ->
                _state.update { it.copy(loading = false, error = friendly(e)) }
            }
        }
    }

    fun retake() {
        _state.update { it.copy(step = VehicleStep.CAPTURE, anpr = null, info = "Retake live photo.") }
    }

    fun confirmVehicle() {
        val s = _state.value
        val txn = s.txn ?: return
        val anpr = s.anpr ?: return
        viewModelScope.launch {
            _state.update { it.copy(loading = true, error = null) }
            runCatching {
                val g = gps()
                val manual = s.manualPlate.isNotBlank() &&
                    s.manualPlate.trim().uppercase() != anpr.vehicle_number.orEmpty().trim().uppercase()
                api.confirmAnpr(
                    bearer(),
                    AnprConfirmRequestDto(
                        transaction_pk = txn.id,
                        anpr_result_id = anpr.id,
                        confirm = true,
                        vehicle_number = s.manualPlate.ifBlank { null },
                        manual_reason = if (manual || anpr.status == "FAILED") s.manualReason.ifBlank { null } else null,
                        gps = g,
                    ),
                )
            }.onSuccess { updated ->
                _state.update {
                    it.copy(loading = false, txn = updated, step = VehicleStep.DRIVER, info = "Vehicle verified.")
                }
            }.onFailure { e ->
                _state.update { it.copy(loading = false, error = friendly(e)) }
            }
        }
    }

    fun saveDriver() {
        val s = _state.value
        val txn = s.txn ?: return
        if (s.driverName.isBlank() || s.driverMobile.isBlank()) {
            _state.update { it.copy(error = "Enter driver name and mobile.") }
            return
        }
        viewModelScope.launch {
            _state.update { it.copy(loading = true, error = null) }
            runCatching {
                api.saveDriver(
                    bearer(),
                    DriverDetailsRequestDto(
                        transaction_pk = txn.id,
                        driver_name = s.driverName.trim(),
                        driver_mobile = s.driverMobile.trim(),
                        transporter_name = s.transporter.ifBlank { null },
                    ),
                )
            }.onSuccess { updated ->
                _state.update { it.copy(loading = false, txn = updated, step = VehicleStep.GATE_PASS) }
            }.onFailure { e ->
                _state.update { it.copy(loading = false, error = friendly(e)) }
            }
        }
    }

    fun createGatePass() {
        val txn = _state.value.txn ?: return
        viewModelScope.launch {
            _state.update { it.copy(loading = true, error = null) }
            runCatching {
                api.createGatePass(bearer(), GatePassCreateRequestDto(transaction_pk = txn.id))
            }.onSuccess { gp ->
                _state.update {
                    it.copy(
                        loading = false,
                        gatePass = gp,
                        step = VehicleStep.EXIT_CAPTURE,
                        info = "Gate pass created. Capture live exit photo when ready (or continue to weighment first).",
                    )
                }
            }.onFailure { e ->
                _state.update { it.copy(loading = false, error = friendly(e)) }
            }
        }
    }

    fun confirmExit() {
        val txn = _state.value.txn ?: return
        val exitAnpr = _state.value.exitAnpr
        viewModelScope.launch {
            _state.update { it.copy(loading = true, error = null) }
            runCatching {
                val g = gps()
                api.exitConfirm(
                    bearer(),
                    VehicleExitConfirmDto(
                        transaction_pk = txn.id,
                        anpr_result_id = exitAnpr?.id,
                        gps = g,
                        complete_transaction = false,
                    ),
                )
            }.onSuccess { updated ->
                _state.update {
                    it.copy(loading = false, txn = updated, step = VehicleStep.DONE, info = "Exit recorded. Continue weighment from dashboard if still open.")
                }
            }.onFailure { e ->
                _state.update { it.copy(loading = false, error = friendly(e)) }
            }
        }
    }

    private fun friendly(e: Throwable): String {
        val m = e.message.orEmpty()
        return when {
            m.contains("Location permission", true) -> m
            m.contains("NOT AUTHORIZED", true) || m.contains("403") ->
                "OPERATION NOT AUTHORIZED. Please move inside JV Industries premises."
            m.contains("Failed to connect") || m.contains("Unable to resolve") ->
                "Unable to reach JV-OMS server on port 8080."
            else -> m.ifBlank { "Unable to complete this step. Please try again." }
        }
    }
}
