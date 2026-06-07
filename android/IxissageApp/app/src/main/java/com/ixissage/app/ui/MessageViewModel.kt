package com.ixissage.app.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.ixissage.app.classifier.ClassifierProvider
import com.ixissage.app.data.ClassificationResult
import com.ixissage.app.data.MessageRepository
import com.ixissage.app.data.SampleMessage
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

data class ClassifiedMessage(
    val sample: SampleMessage,
    val classification: ClassificationResult,
)

data class MessageUiState(
    val isLoading: Boolean = true,
    val messages: List<ClassifiedMessage> = emptyList(),
    val selectedMessageId: String? = null,
    val errorMessage: String? = null,
) {
    val selectedMessage: ClassifiedMessage?
        get() = messages.firstOrNull { it.sample.id == selectedMessageId }
}

class MessageViewModel(
    application: Application,
) : AndroidViewModel(application) {
    private val repository = MessageRepository(application)
    private val classifier = ClassifierProvider.provideOnDeviceBaselineClassifier(application)

    var uiState = androidx.compose.runtime.mutableStateOf(MessageUiState())
        private set

    init {
        loadMessages()
    }

    fun selectMessage(id: String) {
        uiState.value = uiState.value.copy(selectedMessageId = id)
    }

    fun clearSelection() {
        uiState.value = uiState.value.copy(selectedMessageId = null)
    }

    private fun loadMessages() {
        viewModelScope.launch {
            uiState.value = uiState.value.copy(isLoading = true, errorMessage = null)
            runCatching {
                withContext(Dispatchers.IO) {
                    repository.loadSampleMessages().map { sample ->
                        ClassifiedMessage(
                            sample = sample,
                            classification = classifier.classify(sample),
                        )
                    }
                }
            }.onSuccess { messages ->
                uiState.value = MessageUiState(isLoading = false, messages = messages)
            }.onFailure { error ->
                uiState.value = MessageUiState(
                    isLoading = false,
                    errorMessage = error.message ?: "샘플 메시지를 불러오지 못했습니다.",
                )
            }
        }
    }
}
