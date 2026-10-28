package com.jvindustries.oms.dashboard

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
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

@OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)
@Composable
fun DashboardScreen(
    onLogout: () -> Unit,
    onVehicleEntry: () -> Unit = {},
    onWeighment: () -> Unit = {},
    viewModel: DashboardViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("JV-OMS Dashboard") },
                actions = {
                    TextButton(onClick = {
                        viewModel.logout()
                        onLogout()
                    }) { Text("Logout") }
                },
            )
        },
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(16.dp)
                .verticalScroll(rememberScrollState()),
        ) {
            Text(
                text = state.userName.ifBlank { "Operator" },
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.Bold,
            )
            Text(
                text = state.roles.joinToString(),
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
            )
            Spacer(Modifier.height(16.dp))

            if (state.loading) {
                CircularProgressIndicator()
            } else if (state.error != null) {
                Text(state.error!!, color = MaterialTheme.colorScheme.error)
                Button(onClick = viewModel::refresh) { Text("Retry") }
            } else {
                val s = state.summary
                if (s != null) {
                    StatusGrid(
                        items = listOf(
                            "Vehicles In" to s.vehicles_in,
                            "Vehicles Out" to s.vehicles_out,
                            "Material Received" to s.material_received,
                            "Material Loaded" to s.material_loaded,
                            "Pending Approvals" to s.pending_approvals,
                            "OTP Pending" to s.customer_otp_pending,
                            "Exceptions" to s.exceptions,
                            "Equipment Out" to s.equipment_out,
                            "Canteen" to s.canteen_purchases,
                        ),
                    )
                }
            }

            Spacer(Modifier.height(24.dp))
            Text("Actions", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Spacer(Modifier.height(8.dp))
            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                if (viewModel.canSee("vehicle")) ActionChip("Vehicle Entry", onClick = onVehicleEntry)
                if (viewModel.canSee("vehicle")) ActionChip("Material Receiving")
                if (viewModel.canSee("vehicle")) ActionChip("Material Loading")
                if (viewModel.canSee("weighment")) ActionChip("Weighment", onClick = onWeighment)
                ActionChip("Job Work")
                ActionChip("Equipment")
                if (viewModel.canSee("canteen")) ActionChip("Canteen")
                if (viewModel.canSee("reports")) ActionChip("Reports")
            }
            Spacer(Modifier.height(12.dp))
            Text(
                "Phase 3: Live camera + device GPS + on-device OCR. Weighbridge tare/gross/net + density litres.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
            )
        }
    }
}

@Composable
private fun StatusGrid(items: List<Pair<String, Int>>) {
    LazyVerticalGrid(
        columns = GridCells.Fixed(2),
        modifier = Modifier
            .fillMaxWidth()
            .height(320.dp),
        contentPadding = PaddingValues(0.dp),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
        userScrollEnabled = false,
    ) {
        items(items.size) { index ->
            val (label, value) = items[index]
            Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
                Column(Modifier.padding(12.dp)) {
                    Text(label, style = MaterialTheme.typography.labelMedium)
                    Text("$value", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
                }
            }
        }
    }
}

@Composable
private fun ActionChip(label: String, onClick: () -> Unit = {}) {
    Button(onClick = onClick) { Text(label) }
}
