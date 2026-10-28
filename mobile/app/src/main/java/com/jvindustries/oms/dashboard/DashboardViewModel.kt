package com.jvindustries.oms.dashboard

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.jvindustries.oms.auth.AuthRepository
import com.jvindustries.oms.core.network.DashboardSummaryDto
import com.jvindustries.oms.core.network.JvOmsApi
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class DashboardUiState(
    val loading: Boolean = true,
    val error: String? = null,
    val userName: String = "",
    val roles: List<String> = emptyList(),
    val summary: DashboardSummaryDto? = null,
)

@HiltViewModel
class DashboardViewModel @Inject constructor(
    private val api: JvOmsApi,
    private val authRepository: AuthRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(DashboardUiState())
    val state: StateFlow<DashboardUiState> = _state.asStateFlow()

    init {
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            val user = authRepository.currentUser
            val bearer = authRepository.bearerOrNull()
            if (bearer == null) {
                _state.update { it.copy(loading = false, error = "Session expired. Please log in again.") }
                return@launch
            }
            _state.update {
                it.copy(
                    loading = true,
                    error = null,
                    userName = user?.full_name.orEmpty(),
                    roles = user?.roles.orEmpty(),
                )
            }
            runCatching { api.dashboard(bearer) }
                .onSuccess { summary ->
                    _state.update { it.copy(loading = false, summary = summary) }
                }
                .onFailure {
                    _state.update {
                        it.copy(
                            loading = false,
                            error = "Unable to load dashboard. Please check your connection and try again.",
                        )
                    }
                }
        }
    }

    fun logout() = authRepository.logout()

    fun canSee(module: String): Boolean {
        val perms = authRepository.currentUser?.permissions.orEmpty().toSet()
        val roles = authRepository.currentUser?.roles.orEmpty()
        if (roles.contains("OWNER_ADMIN") || perms.contains("owner.full")) return true
        return when (module) {
            "vehicle" -> perms.contains("vehicle.entry") || perms.contains("vehicle.exit")
            "weighment" -> perms.contains("weighment.tare") || perms.contains("weighment.gross")
            "canteen" -> perms.contains("canteen.purchase")
            "reports" -> perms.contains("dashboard.view")
            else -> perms.contains("dashboard.view")
        }
    }
}
