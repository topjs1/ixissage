package com.ixissage.app.ui

import android.app.Application
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.platform.LocalContext
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory

@Composable
fun IxissageApp() {
    val application = LocalContext.current.applicationContext as Application
    val viewModel: MessageViewModel = viewModel(
        factory = viewModelFactory {
            initializer {
                MessageViewModel(application)
            }
        },
    )
    val state by viewModel.uiState

    val selected = state.selectedMessage
    if (state.isManualTestMode) {
        ManualTestScreen(
            state = state,
            onTextChange = viewModel::updateManualText,
            onClassifyClick = viewModel::classifyManualText,
            onBack = viewModel::closeManualTest,
        )
    } else if (selected == null) {
        MessageListScreen(
            state = state,
            onMessageClick = viewModel::selectMessage,
            onManualTestClick = viewModel::openManualTest,
        )
    } else {
        MessageDetailScreen(
            message = selected,
            onBack = viewModel::clearSelection,
        )
    }
}
