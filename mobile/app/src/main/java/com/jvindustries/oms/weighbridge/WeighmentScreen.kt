package com.jvindustries.oms.weighbridge

import android.Manifest
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
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
fun WeighmentScreen(
    onBack: () -> Unit,
    viewModel: WeighmentViewModel = hiltViewModel(),
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
            title = "Capture live ${state.cameraKind} evidence",
            onCaptured = viewModel::onLiveCaptured,
            onError = {},
        )
        return
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Weighbridge") },
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
                Text("Camera + GPS required for weighbridge evidence.")
                Button(onClick = { permissions.launchMultiplePermissionRequest() }, modifier = Modifier.fillMaxWidth()) {
                    Text("Grant permissions")
                }
                return@Column
            }

            Text("Transaction: ${state.transactionPk}", fontWeight = FontWeight.Bold)
            state.summary?.let { s ->
                Text("Status: ${s.status}")
                Text("Tare: ${s.tare_kg ?: "—"} kg")
                Text("Gross: ${s.gross_kg ?: "—"} kg")
                Text("Net (server): ${s.net_kg ?: "—"} kg")
                Text("Density: ${s.density_kg_per_l ?: "—"} kg/L @ ${s.temperature_c ?: "—"} °C")
                Text("${s.calculated_quantity_label}: ${s.calculated_litres ?: "—"} L", fontWeight = FontWeight.SemiBold)
            }
            state.info?.let { Text(it) }
            state.error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
            if (state.loading) CircularProgressIndicator()

            when (state.step) {
                WeighStep.OVERVIEW, WeighStep.DONE -> {
                    Text("LIVE CAMERA ONLY for TRUWEIGH / hydrometer evidence.")
                    Button(
                        onClick = { viewModel.openCamera("TARE") },
                        enabled = !state.loading,
                        modifier = Modifier.fillMaxWidth().height(52.dp),
                    ) { Text("Capture TARE") }
                    Button(
                        onClick = { viewModel.openCamera("GROSS") },
                        enabled = !state.loading,
                        modifier = Modifier.fillMaxWidth().height(52.dp),
                    ) { Text("Capture GROSS") }
                    Button(
                        onClick = { viewModel.openCamera("DENSITY") },
                        enabled = !state.loading,
                        modifier = Modifier.fillMaxWidth().height(52.dp),
                    ) { Text("Capture DENSITY") }
                    OutlinedButton(onClick = viewModel::refreshSummary, modifier = Modifier.fillMaxWidth()) {
                        Text("Refresh server summary")
                    }
                }

                WeighStep.CONFIRM_WEIGHT -> {
                    val d = state.detect
                    Text("DETECTED WEIGHT", fontWeight = FontWeight.Bold)
                    Text("OCR: ${d?.detected_weight_kg ?: "—"} kg  (${((d?.confidence ?: 0.0) * 100).toInt()}%)")
                    Text("Provider: ${d?.provider}")
                    if (d?.failed == true) Text(d.message, color = MaterialTheme.colorScheme.error)
                    OutlinedTextField(
                        value = state.confirmedWeightText,
                        onValueChange = viewModel::onWeightText,
                        label = { Text("Confirm weight (kg)") },
                        modifier = Modifier.fillMaxWidth(),
                    )
                    Text("Net weight is calculated only by the server after gross confirm — operators cannot set net.")
                    Button(onClick = viewModel::confirmWeight, enabled = !state.loading, modifier = Modifier.fillMaxWidth().height(52.dp)) {
                        Text("CONFIRM ${d?.kind}")
                    }
                    OutlinedButton(onClick = { viewModel.openCamera(d?.kind ?: "TARE") }, modifier = Modifier.fillMaxWidth()) {
                        Text("RETAKE")
                    }
                }

                WeighStep.CONFIRM_DENSITY -> {
                    val d = state.densityDetect
                    Text("DETECTED DENSITY", fontWeight = FontWeight.Bold)
                    Text("Density: ${d?.detected_density ?: "—"}")
                    Text("Temp: ${d?.detected_temperature_c ?: "—"} °C")
                    Text("Confidence: ${((d?.confidence ?: 0.0) * 100).toInt()}%")
                    OutlinedTextField(value = state.densityText, onValueChange = viewModel::onDensityText, label = { Text("Confirm density kg/L") }, modifier = Modifier.fillMaxWidth())
                    OutlinedTextField(value = state.tempText, onValueChange = viewModel::onTempText, label = { Text("Confirm temperature °C") }, modifier = Modifier.fillMaxWidth())
                    Button(onClick = viewModel::confirmDensity, enabled = !state.loading, modifier = Modifier.fillMaxWidth().height(52.dp)) {
                        Text("CONFIRM DENSITY")
                    }
                    OutlinedButton(onClick = { viewModel.openCamera("DENSITY") }, modifier = Modifier.fillMaxWidth()) {
                        Text("RETAKE")
                    }
                }

                WeighStep.CAMERA -> Unit
            }
        }
    }
}
