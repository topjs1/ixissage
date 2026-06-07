package com.ixissage.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import com.ixissage.app.ui.IxissageApp
import com.ixissage.app.ui.theme.IxissageTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            IxissageTheme {
                IxissageApp()
            }
        }
    }
}

