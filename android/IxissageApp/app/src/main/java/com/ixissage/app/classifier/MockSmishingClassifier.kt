package com.ixissage.app.classifier

import com.ixissage.app.data.ClassificationResult
import com.ixissage.app.data.SampleMessage

class MockSmishingClassifier(
    private val result: ClassificationResult = ClassificationResult(
        normalProbability = 0.50f,
        phishingProbability = 0.50f,
        predictedLabel = "normal",
    ),
) : SmishingClassifier {
    override fun classify(message: SampleMessage): ClassificationResult {
        return result
    }
}

