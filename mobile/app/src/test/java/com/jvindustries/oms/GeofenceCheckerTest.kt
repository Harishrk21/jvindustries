package com.jvindustries.oms

import com.jvindustries.oms.config.GeofenceChecker
import com.jvindustries.oms.config.GpsSample
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class GeofenceCheckerTest {
    @Test
    fun insidePremisesAuthorized() {
        val checker = GeofenceChecker()
        val result = checker.verify(GpsSample(13.0827, 80.2707, 10.0))
        assertTrue(result.authorized)
    }

    @Test
    fun outsidePremisesBlocked() {
        val checker = GeofenceChecker()
        val result = checker.verify(GpsSample(12.0, 80.0, 10.0))
        assertFalse(result.authorized)
    }

    @Test
    fun poorAccuracyBlocked() {
        val checker = GeofenceChecker()
        val result = checker.verify(GpsSample(13.0827, 80.2707, 99.0))
        assertFalse(result.authorized)
    }
}
