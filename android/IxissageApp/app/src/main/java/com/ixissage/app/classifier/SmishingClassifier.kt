package com.ixissage.app.classifier

import com.ixissage.app.data.ClassificationResult
import com.ixissage.app.data.SampleMessage

interface SmishingClassifier {
    fun classify(message: SampleMessage): ClassificationResult
}

