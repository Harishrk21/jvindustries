package com.jvindustries.oms.vehicle

import android.Manifest
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.google.accompanist.permissions.ExperimentalPermissionsApi
import com.google.accompanist.permissions.rememberMultiplePermissionsState
import com.jvindustries.oms.core.camera.LiveCameraCapture

@OptIn(ExperimentalMaterial3Api::class, ExperimentalPermissionsApi::class)
@Composable
fun VehicleEntryScreen(
    onBack: () -> Unit,
    onOpenWeighment: (String) -> Unit = {},
    viewModel: VehicleEntryViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsState()
    val permissions = rememberMultiplePermissionsState(
        listOf(
            Manifest.permission.CAMERA,
            Manifest.permission.ACCESS_FINE_LOCATION,
            Manifest.permission.ACCESS_COARSE_LOCATION,
        ),
    )

    if (state.showCamera) {
        LiveCameraCapture(
            title = if (state.cameraMode == "EXIT") "Capture EXIT live photo" else "Capture ENTRY live photo",
            onCaptured = viewModel::onLiveCaptured,
            onError = { /* surfaced via retry */ },
        )
        return
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Vehicle Entry") },
                navigationIcon = { TextButton(onClick = onBack) { Text("Back") } },
            )
        },
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(16.dp)
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            if (!permissions.allPermissionsGranted) {
                Text("Camera and location permissions are required for live evidence and geofence checks.")
                Button(onClick = { permissions.launchMultiplePermissionRequest() }, modifier = Modifier.fillMaxWidth()) {
                    Text("Grant permissions")
                }
                return@Column
            }

            state.txn?.let {
                Text("Txn: ${it.transaction_id}", fontWeight = FontWeight.Bold)
                Text("Status: ${it.status}")
                it.vehicle_number?.let { plate -> Text("Vehicle: $plate") }
            }
            state.gatePass?.let { Text("Gate Pass: ${it.gate_pass_number}", fontWeight = FontWeight.SemiBold) }
            state.info?.let { Text(it, style = MaterialTheme.typography.bodyMedium) }
            state.error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
            if (state.loading) CircularProgressIndicator()

            when (state.step) {
                VehicleStep.START -> {
                    Text("Starts a real transaction with device GPS geofence verification.")
                    Button(
                        onClick = { viewModel.startEntry() },
                        enabled = !state.loading,
                        modifier = Modifier.fillMaxWidth().height(52.dp),
                    ) { Text("Start Entry") }
                }

                VehicleStep.CAPTURE -> {
                    Text("LIVE CAMERA ONLY — gallery is blocked for operators.", fontWeight = FontWeight.SemiBold)
                    Text("Photo is stored as evidence. On-device ML Kit OCR extracts plate candidates (never invented).")
                    Button(
                        onClick = { viewModel.openLiveCamera("ENTRY") },
                        enabled = !state.loading,
                        modifier = Modifier.fillMaxWidth().height(52.dp),
                    ) { Text("Open live camera") }
                }

                VehicleStep.ANPR -> {
                    val anpr = state.anpr
                    Text("DETECTED DATA", fontWeight = FontWeight.Bold)
                    Text("Plate: ${anpr?.vehicle_number ?: "—"}")
                    Text("Confidence: ${((anpr?.confidence ?: 0.0) * 100).toInt()}%")
                    Text("Provider: ${anpr?.provider} (${anpr?.status})")
                    if (!anpr?.candidates.isNullOrEmpty()) {
                        Text("Candidates: ${anpr?.candidates?.joinToString()}")
                    }
                    OutlinedTextField(
                        value = state.manualPlate,
                        onValueChange = viewModel::onManualPlate,
                        label = { Text("Confirm / manual plate") },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true,
                    )
                    OutlinedTextField(
                        value = state.manualReason,
                        onValueChange = viewModel::onManualReason,
                        label = { Text("Manual reason (required if override / OCR fail)") },
                        modifier = Modifier.fillMaxWidth(),
                    )
                    Button(
                        onClick = viewModel::confirmVehicle,
                        enabled = !state.loading,
                        modifier = Modifier.fillMaxWidth().height(52.dp),
                    ) { Text("CONFIRM") }
                    OutlinedButton(
                        onClick = viewModel::retake,
                        enabled = !state.loading,
                        modifier = Modifier.fillMaxWidth().height(52.dp),
                    ) { Text("RETAKE") }
                }

                VehicleStep.DRIVER -> {
                    OutlinedTextField(value = state.driverName, onValueChange = viewModel::onDriverName, label = { Text("Driver name") }, modifier = Modifier.fillMaxWidth())
                    OutlinedTextField(value = state.driverMobile, onValueChange = viewModel::onDriverMobile, label = { Text("Driver mobile") }, modifier = Modifier.fillMaxWidth())
                    OutlinedTextField(value = state.transporter, onValueChange = viewModel::onTransporter, label = { Text("Transporter") }, modifier = Modifier.fillMaxWidth())
                    Button(onClick = viewModel::saveDriver, enabled = !state.loading, modifier = Modifier.fillMaxWidth().height(52.dp)) {
                        Text("Save driver")
                    }
                }

                VehicleStep.GATE_PASS -> {
                    Button(onClick = viewModel::createGatePass, enabled = !state.loading, modifier = Modifier.fillMaxWidth().height(52.dp)) {
                        Text("Generate Gate Pass")
                    }
                    state.txn?.let { txn ->
                        OutlinedButton(
                            onClick = { onOpenWeighment(txn.id) },
                            modifier = Modifier.fillMaxWidth().height(52.dp),
                        ) { Text("Go to Weighment (Tare/Gross)") }
                    }
                }

                VehicleStep.EXIT_CAPTURE -> {
                    Text("Capture live EXIT photograph + OCR.")
                    Button(
                        onClick = { viewModel.openLiveCamera("EXIT") },
                        enabled = !state.loading,
                        modifier = Modifier.fillMaxWidth().height(52.dp),
                    ) { Text("Open exit live camera") }
                    state.txn?.let { txn ->
                        if (txn.status == "AWAITING_TARE" || txn.status == "LOADING" || txn.status == "DOCUMENTS_PENDING") {
                            OutlinedButton(onClick = { onOpenWeighment(txn.id) }, modifier = Modifier.fillMaxWidth()) {
                                Text("Weighment first")
                            }
                        }
                    }
                }

                VehicleStep.DONE -> {
                    Text("Vehicle gate steps recorded.", fontWeight = FontWeight.Bold)
                    Text("${state.txn?.transaction_id} → ${state.txn?.status}")
                    state.txn?.let { txn ->
                        if (txn.status != "COMPLETED") {
                            Button(onClick = { onOpenWeighment(txn.id) }, modifier = Modifier.fillMaxWidth()) {
                                Text("Continue to Weighment")
                            }
                        }
                    }
                    Spacer(Modifier.height(8.dp))
                    Button(onClick = onBack, modifier = Modifier.fillMaxWidth()) { Text("Back to dashboard") }
                }
            }
        }
    }
}
