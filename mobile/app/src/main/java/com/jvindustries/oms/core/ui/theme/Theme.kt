package com.jvindustries.oms.core.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val Steel = Color(0xFF1B3A4B)
private val Amber = Color(0xFFE8A838)
private val Slate = Color(0xFF0F2430)
private val Mist = Color(0xFFF3F6F8)

private val LightColors = lightColorScheme(
    primary = Steel,
    onPrimary = Color.White,
    secondary = Amber,
    onSecondary = Slate,
    background = Mist,
    onBackground = Slate,
    surface = Color.White,
    onSurface = Slate,
)

private val DarkColors = darkColorScheme(
    primary = Amber,
    onPrimary = Slate,
    secondary = Steel,
    background = Slate,
    surface = Color(0xFF163445),
)

@Composable
fun JvOmsTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = LightColors,
        content = content,
    )
}
