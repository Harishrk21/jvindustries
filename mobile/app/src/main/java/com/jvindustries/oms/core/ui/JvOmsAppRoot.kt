package com.jvindustries.oms.core.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.jvindustries.oms.auth.AuthRepository
import com.jvindustries.oms.auth.LoginScreen
import com.jvindustries.oms.dashboard.DashboardScreen
import com.jvindustries.oms.vehicle.VehicleEntryScreen
import com.jvindustries.oms.weighbridge.WeighmentScreen
import dagger.hilt.EntryPoint
import dagger.hilt.InstallIn
import dagger.hilt.android.EntryPointAccessors
import dagger.hilt.components.SingletonComponent

@EntryPoint
@InstallIn(SingletonComponent::class)
interface AuthEntryPoint {
    fun authRepository(): AuthRepository
}

@Composable
fun JvOmsAppRoot() {
    val nav = rememberNavController()
    val context = LocalContext.current.applicationContext
    val auth = remember {
        EntryPointAccessors.fromApplication(context, AuthEntryPoint::class.java).authRepository()
    }
    val start = if (auth.hasSession()) "dashboard" else "login"

    NavHost(navController = nav, startDestination = start) {
        composable("login") {
            LoginScreen(onLoggedIn = {
                nav.navigate("dashboard") {
                    popUpTo("login") { inclusive = true }
                }
            })
        }
        composable("dashboard") {
            DashboardScreen(
                onLogout = {
                    nav.navigate("login") {
                        popUpTo("dashboard") { inclusive = true }
                    }
                },
                onVehicleEntry = { nav.navigate("vehicle_entry") },
                onWeighment = { nav.navigate("weighment_picker") },
            )
        }
        composable("vehicle_entry") {
            VehicleEntryScreen(
                onBack = { nav.popBackStack() },
                onOpenWeighment = { pk -> nav.navigate("weighment/$pk") },
            )
        }
        composable("weighment_picker") {
            WeighmentPickerScreen(
                onBack = { nav.popBackStack() },
                onOpen = { pk -> nav.navigate("weighment/$pk") },
            )
        }
        composable(
            route = "weighment/{transactionPk}",
            arguments = listOf(navArgument("transactionPk") { type = NavType.StringType }),
        ) {
            WeighmentScreen(onBack = { nav.popBackStack() })
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun WeighmentPickerScreen(onBack: () -> Unit, onOpen: (String) -> Unit) {
    var pk by remember { mutableStateOf("") }
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Weighment") },
                navigationIcon = { TextButton(onClick = onBack) { Text("Back") } },
            )
        },
    ) { padding ->
        Column(
            modifier = Modifier
                .padding(padding)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text("Prefer opening Weighment from Vehicle Entry after driver/gate pass. Or paste the transaction UUID.")
            OutlinedTextField(
                value = pk,
                onValueChange = { pk = it },
                label = { Text("Transaction UUID") },
                modifier = Modifier.fillMaxWidth(),
            )
            Button(
                onClick = { if (pk.isNotBlank()) onOpen(pk.trim()) },
                modifier = Modifier.fillMaxWidth(),
            ) { Text("Open weighment") }
        }
    }
}
