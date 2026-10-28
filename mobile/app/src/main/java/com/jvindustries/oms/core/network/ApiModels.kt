package com.jvindustries.oms.core.network

import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class LoginRequest(val user_id: String, val password: String)

@JsonClass(generateAdapter = true)
data class UserDto(
    val id: String,
    val user_code: String,
    val full_name: String,
    val roles: List<String>,
    val permissions: List<String>,
)

@JsonClass(generateAdapter = true)
data class LoginResponse(
    val access_token: String,
    val token_type: String,
    val user: UserDto,
)

@JsonClass(generateAdapter = true)
data class DeviceRegisterRequest(
    val device_uid: String,
    val device_name: String,
    val platform: String = "android",
    val app_version: String,
)

@JsonClass(generateAdapter = true)
data class DeviceDto(
    val id: String,
    val device_uid: String,
    val device_name: String,
    val platform: String,
    val app_version: String,
    val is_active: Boolean,
)

@JsonClass(generateAdapter = true)
data class DashboardSummaryDto(
    val vehicles_in: Int = 0,
    val vehicles_out: Int = 0,
    val material_received: Int = 0,
    val material_loaded: Int = 0,
    val weighments: Int = 0,
    val pending_approvals: Int = 0,
    val customer_otp_pending: Int = 0,
    val exceptions: Int = 0,
    val production_loss_alerts: Int = 0,
    val equipment_out: Int = 0,
    val canteen_purchases: Int = 0,
)

@JsonClass(generateAdapter = true)
data class GpsDto(val lat: Double, val lon: Double, val accuracy_m: Double)

@JsonClass(generateAdapter = true)
data class VehicleEntryStartRequest(
    val client_transaction_id: String? = null,
    val type: String = "MATERIAL_LOADING_OUTWARD",
    val device_id: String? = null,
    val gps: GpsDto,
)

@JsonClass(generateAdapter = true)
data class VehicleTxnDto(
    val id: String,
    val transaction_id: String,
    val type: String,
    val status: String,
    val vehicle_number: String? = null,
    val driver_name: String? = null,
    val driver_mobile: String? = null,
    val transporter_name: String? = null,
    val geofence_ok: Boolean? = null,
    val tare_kg: Double? = null,
    val gross_kg: Double? = null,
    val net_kg: Double? = null,
    val density_kg_per_l: Double? = null,
    val temperature_c: Double? = null,
    val calculated_litres: Double? = null,
    val created_at: String? = null,
)

@JsonClass(generateAdapter = true)
data class AnprResultDto(
    val id: String,
    val transaction_id: String,
    val vehicle_number: String? = null,
    val confidence: Double? = null,
    val provider: String,
    val status: String,
    val message: String? = null,
    val candidates: List<String> = emptyList(),
    val photo_id: String? = null,
    val ocr_raw_preview: String? = null,
)

@JsonClass(generateAdapter = true)
data class AnprConfirmRequestDto(
    val transaction_pk: String,
    val anpr_result_id: String,
    val confirm: Boolean = true,
    val vehicle_number: String? = null,
    val manual_reason: String? = null,
    val gps: GpsDto? = null,
)

@JsonClass(generateAdapter = true)
data class DriverDetailsRequestDto(
    val transaction_pk: String,
    val driver_name: String,
    val driver_mobile: String,
    val transporter_name: String? = null,
)

@JsonClass(generateAdapter = true)
data class GatePassCreateRequestDto(
    val transaction_pk: String,
    val pass_type: String = "OUTWARD_LOADING",
    val direction: String = "INWARD",
)

@JsonClass(generateAdapter = true)
data class GatePassDto(
    val id: String,
    val gate_pass_number: String,
    val transaction_id: String,
    val pass_type: String,
    val vehicle_number: String? = null,
    val driver_name: String? = null,
    val direction: String,
    val created_at: String? = null,
)

@JsonClass(generateAdapter = true)
data class VehicleExitConfirmDto(
    val transaction_pk: String,
    val anpr_result_id: String? = null,
    val gps: GpsDto,
    val complete_transaction: Boolean = false,
)

@JsonClass(generateAdapter = true)
data class WeighmentDetectDto(
    val transaction_id: String,
    val kind: String,
    val detected_weight_kg: Double? = null,
    val confidence: Double,
    val provider: String,
    val failed: Boolean,
    val message: String,
    val candidates_kg: List<Double> = emptyList(),
    val photo_id: String? = null,
    val hardware_weight_kg: Double? = null,
    val ocr_raw_preview: String? = null,
)

@JsonClass(generateAdapter = true)
data class WeighmentConfirmDto(
    val transaction_pk: String,
    val kind: String,
    val photo_id: String,
    val confirmed_weight_kg: Double,
    val ocr_weight_kg: Double? = null,
    val ocr_confidence: Double? = null,
    val ocr_provider: String? = null,
    val ocr_raw_text: String? = null,
    val gps: GpsDto,
    val after_tare_mode: String? = "LOADING",
)

@JsonClass(generateAdapter = true)
data class WeighmentSummaryDto(
    val transaction_id: String,
    val status: String,
    val tare_kg: Double? = null,
    val gross_kg: Double? = null,
    val net_kg: Double? = null,
    val density_kg_per_l: Double? = null,
    val temperature_c: Double? = null,
    val calculated_litres: Double? = null,
    val calculated_quantity_label: String = "CALCULATED QUANTITY",
)

@JsonClass(generateAdapter = true)
data class DensityDetectDto(
    val transaction_id: String,
    val detected_density: Double? = null,
    val detected_temperature_c: Double? = null,
    val confidence: Double,
    val provider: String,
    val failed: Boolean,
    val message: String,
    val photo_id: String? = null,
    val ocr_raw_preview: String? = null,
)

@JsonClass(generateAdapter = true)
data class DensityConfirmDto(
    val transaction_pk: String,
    val photo_id: String,
    val confirmed_density: Double,
    val confirmed_temperature_c: Double? = null,
    val ocr_density: Double? = null,
    val ocr_temperature: Double? = null,
    val ocr_confidence: Double? = null,
    val ocr_provider: String? = null,
    val ocr_raw_text: String? = null,
    val gps: GpsDto,
)

@JsonClass(generateAdapter = true)
data class DensityOutDto(
    val id: String,
    val transaction_id: String,
    val density_kg_per_l: Double,
    val temperature_c: Double? = null,
    val calculated_litres: Double? = null,
    val net_kg_snapshot: Double? = null,
)
