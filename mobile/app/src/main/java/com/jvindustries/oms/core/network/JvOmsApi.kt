package com.jvindustries.oms.core.network

import okhttp3.MultipartBody
import okhttp3.RequestBody
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part
import retrofit2.http.Path

interface JvOmsApi {
    @POST("api/v1/auth/login")
    suspend fun login(@Body body: LoginRequest): LoginResponse

    @GET("api/v1/auth/me")
    suspend fun me(@Header("Authorization") bearer: String): UserDto

    @POST("api/v1/devices/register")
    suspend fun registerDevice(
        @Header("Authorization") bearer: String,
        @Body body: DeviceRegisterRequest,
    ): DeviceDto

    @GET("api/v1/dashboard/summary")
    suspend fun dashboard(@Header("Authorization") bearer: String): DashboardSummaryDto

    @POST("api/v1/vehicles/entry/start")
    suspend fun startVehicleEntry(
        @Header("Authorization") bearer: String,
        @Body body: VehicleEntryStartRequest,
    ): VehicleTxnDto

    @Multipart
    @POST("api/v1/vehicles/anpr")
    suspend fun runAnpr(
        @Header("Authorization") bearer: String,
        @Part("transaction_pk") transactionPk: RequestBody,
        @Part("gps_lat") gpsLat: RequestBody,
        @Part("gps_lon") gpsLon: RequestBody,
        @Part("gps_accuracy_m") gpsAccuracy: RequestBody,
        @Part("capture_source") captureSource: RequestBody,
        @Part("ocr_text") ocrText: RequestBody,
        @Part image: MultipartBody.Part,
    ): AnprResultDto

    @POST("api/v1/vehicles/anpr/confirm")
    suspend fun confirmAnpr(
        @Header("Authorization") bearer: String,
        @Body body: AnprConfirmRequestDto,
    ): VehicleTxnDto

    @POST("api/v1/vehicles/driver")
    suspend fun saveDriver(
        @Header("Authorization") bearer: String,
        @Body body: DriverDetailsRequestDto,
    ): VehicleTxnDto

    @POST("api/v1/gate-passes")
    suspend fun createGatePass(
        @Header("Authorization") bearer: String,
        @Body body: GatePassCreateRequestDto,
    ): GatePassDto

    @Multipart
    @POST("api/v1/vehicles/exit/detect")
    suspend fun exitDetect(
        @Header("Authorization") bearer: String,
        @Part("transaction_pk") transactionPk: RequestBody,
        @Part("gps_lat") gpsLat: RequestBody,
        @Part("gps_lon") gpsLon: RequestBody,
        @Part("gps_accuracy_m") gpsAccuracy: RequestBody,
        @Part("capture_source") captureSource: RequestBody,
        @Part("ocr_text") ocrText: RequestBody,
        @Part image: MultipartBody.Part,
    ): AnprResultDto

    @POST("api/v1/vehicles/exit/confirm")
    suspend fun exitConfirm(
        @Header("Authorization") bearer: String,
        @Body body: VehicleExitConfirmDto,
    ): VehicleTxnDto

    @Multipart
    @POST("api/v1/weighments/detect")
    suspend fun detectWeighment(
        @Header("Authorization") bearer: String,
        @Part("transaction_pk") transactionPk: RequestBody,
        @Part("kind") kind: RequestBody,
        @Part("gps_lat") gpsLat: RequestBody,
        @Part("gps_lon") gpsLon: RequestBody,
        @Part("gps_accuracy_m") gpsAccuracy: RequestBody,
        @Part("capture_source") captureSource: RequestBody,
        @Part("ocr_text") ocrText: RequestBody,
        @Part image: MultipartBody.Part,
    ): WeighmentDetectDto

    @POST("api/v1/weighments/confirm")
    suspend fun confirmWeighment(
        @Header("Authorization") bearer: String,
        @Body body: WeighmentConfirmDto,
    ): WeighmentSummaryDto

    @Multipart
    @POST("api/v1/weighments/density/detect")
    suspend fun detectDensity(
        @Header("Authorization") bearer: String,
        @Part("transaction_pk") transactionPk: RequestBody,
        @Part("gps_lat") gpsLat: RequestBody,
        @Part("gps_lon") gpsLon: RequestBody,
        @Part("gps_accuracy_m") gpsAccuracy: RequestBody,
        @Part("capture_source") captureSource: RequestBody,
        @Part("ocr_text") ocrText: RequestBody,
        @Part image: MultipartBody.Part,
    ): DensityDetectDto

    @POST("api/v1/weighments/density/confirm")
    suspend fun confirmDensity(
        @Header("Authorization") bearer: String,
        @Body body: DensityConfirmDto,
    ): DensityOutDto

    @GET("api/v1/weighments/summary/{transactionPk}")
    suspend fun weighmentSummary(
        @Header("Authorization") bearer: String,
        @Path("transactionPk") transactionPk: String,
    ): WeighmentSummaryDto
}
