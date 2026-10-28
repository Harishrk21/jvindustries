package com.jvindustries.oms.core.location

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.content.pm.PackageManager
import android.location.Location
import android.os.Looper
import androidx.core.content.ContextCompat
import com.google.android.gms.location.LocationCallback
import com.google.android.gms.location.LocationRequest
import com.google.android.gms.location.LocationResult
import com.google.android.gms.location.LocationServices
import com.google.android.gms.location.Priority
import com.jvindustries.oms.core.network.GpsDto
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.suspendCancellableCoroutine
import javax.inject.Inject
import javax.inject.Singleton
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

class LocationUnavailableException(message: String) : Exception(message)

@Singleton
class DeviceLocationProvider @Inject constructor(
    @ApplicationContext private val context: Context,
) {
    private val client = LocationServices.getFusedLocationProviderClient(context)

    fun hasPermission(): Boolean {
        val fine = ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION)
        val coarse = ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_COARSE_LOCATION)
        return fine == PackageManager.PERMISSION_GRANTED || coarse == PackageManager.PERMISSION_GRANTED
    }

    @SuppressLint("MissingPermission")
    suspend fun currentGps(): GpsDto {
        if (!hasPermission()) {
            throw LocationUnavailableException("Location permission is required for JV Industries operations.")
        }
        val last = suspendCancellableCoroutine<Location?> { cont ->
            client.lastLocation
                .addOnSuccessListener { cont.resume(it) }
                .addOnFailureListener { cont.resume(null) }
        }
        if (last != null && last.accuracy <= 80f && (System.currentTimeMillis() - last.time) < 60_000) {
            return GpsDto(last.latitude, last.longitude, last.accuracy.toDouble())
        }
        return suspendCancellableCoroutine { cont ->
            val request = LocationRequest.Builder(Priority.PRIORITY_HIGH_ACCURACY, 2000L)
                .setMaxUpdates(1)
                .setDurationMillis(15_000L)
                .build()
            val callback = object : LocationCallback() {
                override fun onLocationResult(result: LocationResult) {
                    client.removeLocationUpdates(this)
                    val loc = result.lastLocation
                    if (loc == null) {
                        cont.resumeWithException(
                            LocationUnavailableException("Unable to read GPS. Move outdoors and try again."),
                        )
                    } else {
                        cont.resume(GpsDto(loc.latitude, loc.longitude, loc.accuracy.toDouble()))
                    }
                }
            }
            client.requestLocationUpdates(request, callback, Looper.getMainLooper())
            cont.invokeOnCancellation { client.removeLocationUpdates(callback) }
        }
    }
}
