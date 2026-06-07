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
    val isManualTestMode: Boolean = false,
    val manualText: String = "",
    val manualClassification: ClassificationResult? = null,
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

    fun openManualTest() {
        uiState.value = uiState.value.copy(
            selectedMessageId = null,
            isManualTestMode = true,
        )
    }

    fun closeManualTest() {
        uiState.value = uiState.value.copy(isManualTestMode = false)
    }

    fun updateManualText(text: String) {
        uiState.value = uiState.value.copy(
            manualText = text,
            manualClassification = null,
        )
    }

    fun classifyManualText() {
        val text = uiState.value.manualText.trim()
        if (text.isEmpty()) {
            uiState.value = uiState.value.copy(manualClassification = null)
            return
        }

        val sample = SampleMessage(
            id = "manual-test",
            sender = "직접 입력",
            body = text,
            groundTruthLabel = "unknown",
            precomputedResult = ClassificationResult(
                normalProbability = 0f,
                phishingProbability = 0f,
                predictedLabel = "unknown",
            ),
        )
        uiState.value = uiState.value.copy(
            manualClassification = classifier.classify(sample),
        )
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
