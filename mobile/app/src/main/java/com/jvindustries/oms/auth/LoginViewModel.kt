package com.jvindustries.oms.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class LoginUiState(
    val userId: String = "",
    val password: String = "",
    val loading: Boolean = false,
    val error: String? = null,
    val loggedIn: Boolean = false,
)

@HiltViewModel
class LoginViewModel @Inject constructor(
    private val authRepository: AuthRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(LoginUiState())
    val state: StateFlow<LoginUiState> = _state.asStateFlow()

    fun onUserId(value: String) = _state.update { it.copy(userId = value, error = null) }
    fun onPassword(value: String) = _state.update { it.copy(password = value, error = null) }

    fun login() {
        val s = _state.value
        if (s.userId.isBlank() || s.password.isBlank()) {
            _state.update { it.copy(error = "Enter User ID and password.") }
            return
        }
        viewModelScope.launch {
            _state.update { it.copy(loading = true, error = null) }
            val result = authRepository.login(s.userId, s.password)
            _state.update {
                result.fold(
                    onSuccess = { it.copy(loading = false, loggedIn = true) },
                    onFailure = { err ->
                        it.copy(
                            loading = false,
                            error = friendlyError(err),
                        )
                    },
                )
            }
        }
    }

    private fun friendlyError(err: Throwable): String {
        val msg = err.message.orEmpty()
        return when {
            msg.contains("Unable to resolve host", true) ||
                msg.contains("failed to connect", true) ||
                msg.contains("timeout", true) ->
                "Unable to reach JV-OMS server. Check network and try again."
            msg.contains("401") || msg.contains("Unauthorized", true) ->
                "Invalid User ID or password."
            else -> "Unable to log in. Please try again."
        }
    }
}
