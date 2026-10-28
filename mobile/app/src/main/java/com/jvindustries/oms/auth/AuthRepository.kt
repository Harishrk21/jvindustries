package com.jvindustries.oms.auth

import android.os.Build
import com.jvindustries.oms.BuildConfig
import com.jvindustries.oms.core.network.DeviceRegisterRequest
import com.jvindustries.oms.core.network.JvOmsApi
import com.jvindustries.oms.core.network.LoginRequest
import com.jvindustries.oms.core.network.UserDto
import com.jvindustries.oms.core.security.TokenStore
import java.util.UUID
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AuthRepository @Inject constructor(
    private val api: JvOmsApi,
    private val tokenStore: TokenStore,
) {
    var currentUser: UserDto? = null
        private set

    fun hasSession(): Boolean = !tokenStore.getToken().isNullOrBlank()

    suspend fun login(userId: String, password: String): Result<UserDto> = runCatching {
        val response = api.login(LoginRequest(userId.trim(), password))
        tokenStore.saveToken(response.access_token)
        currentUser = response.user
        registerDeviceQuietly()
        response.user
    }

    suspend fun loadSession(): Result<UserDto> = runCatching {
        val token = tokenStore.getToken() ?: error("Not logged in")
        val user = api.me(bearer(token))
        currentUser = user
        user
    }.onFailure {
        tokenStore.clear()
        currentUser = null
    }

    fun logout() {
        tokenStore.clear()
        currentUser = null
    }

    fun bearerOrNull(): String? = tokenStore.getToken()?.let { bearer(it) }

    private suspend fun registerDeviceQuietly() {
        val token = tokenStore.getToken() ?: return
        val uid = "${Build.MANUFACTURER}-${Build.MODEL}-${Build.FINGERPRINT}".hashCode().toString()
        runCatching {
            api.registerDevice(
                bearer(token),
                DeviceRegisterRequest(
                    device_uid = "android-$uid-${UUID.nameUUIDFromBytes(uid.toByteArray())}",
                    device_name = "${Build.MANUFACTURER} ${Build.MODEL}",
                    app_version = BuildConfig.VERSION_NAME,
                ),
            )
        }
    }

    private fun bearer(token: String) = "Bearer $token"
}
