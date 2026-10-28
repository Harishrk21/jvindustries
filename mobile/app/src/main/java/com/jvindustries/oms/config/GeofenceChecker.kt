package com.jvindustries.oms.config

import kotlin.math.asin
import kotlin.math.cos
import kotlin.math.sin
import kotlin.math.sqrt
import javax.inject.Inject
import javax.inject.Singleton

data class GpsSample(
    val latitude: Double,
    val longitude: Double,
    val accuracyM: Double,
)

data class GeofenceResult(
    val authorized: Boolean,
    val message: String,
    val distanceM: Double,
)

/**
 * Client-side geofence check for UX. Server re-validates on critical operations.
 */
@Singleton
class GeofenceChecker @Inject constructor() {
    // Defaults mirror backend .env.example; Owner-configurable remote config comes later.
    var centerLat: Double = 13.0827
    var centerLon: Double = 80.2707
    var radiusM: Double = 300.0
    var maxAccuracyM: Double = 250.0

    fun verify(sample: GpsSample): GeofenceResult {
        val distance = haversineM(sample.latitude, sample.longitude, centerLat, centerLon)
        if (distance > radiusM) {
            return GeofenceResult(
                authorized = false,
                message = "OPERATION NOT AUTHORIZED. Please move inside JV Industries premises.",
                distanceM = distance,
            )
        }
        // Inside fence: allow moderate Wi-Fi/browser accuracy noise up to fence radius.
        val softCeiling = maxOf(maxAccuracyM, radiusM)
        if (sample.accuracyM > softCeiling) {
            return GeofenceResult(
                authorized = false,
                message = "OPERATION NOT AUTHORIZED. GPS accuracy is too low. Please wait for a better signal inside JV Industries premises.",
                distanceM = distance,
            )
        }
        return GeofenceResult(
            authorized = true,
            message = "GPS verified inside authorized premises.",
            distanceM = distance,
        )
    }

    companion object {
        fun haversineM(lat1: Double, lon1: Double, lat2: Double, lon2: Double): Double {
            val r = 6_371_000.0
            val p1 = Math.toRadians(lat1)
            val p2 = Math.toRadians(lat2)
            val dp = Math.toRadians(lat2 - lat1)
            val dl = Math.toRadians(lon2 - lon1)
            val a = sin(dp / 2) * sin(dp / 2) + cos(p1) * cos(p2) * sin(dl / 2) * sin(dl / 2)
            return 2 * r * asin(sqrt(a))
        }
    }
}
