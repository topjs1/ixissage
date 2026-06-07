package com.ixissage.app.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val IxissageLightColors = lightColorScheme(
    primary = Color(0xFF285C8E),
    onPrimary = Color.White,
    secondary = Color(0xFF5E6B3D),
    onSecondary = Color.White,
    tertiary = Color(0xFF8C4B5A),
    onTertiary = Color.White,
    background = Color(0xFFF7F8FA),
    onBackground = Color(0xFF1E242B),
    surface = Color(0xFFFFFFFF),
    onSurface = Color(0xFF1E242B),
    onSurfaceVariant = Color(0xFF5E6874),
    error = Color(0xFFB3261E),
)

@Composable
fun IxissageTheme(
    content: @Composable () -> Unit,
) {
    MaterialTheme(
        colorScheme = IxissageLightColors,
        content = content,
    )
}

