package com.ixissage.app.classifier

import com.ixissage.app.data.ClassificationResult
import com.ixissage.app.data.SampleMessage

class PrecomputedSampleClassifier : SmishingClassifier {
    override fun classify(message: SampleMessage): ClassificationResult {
        return message.precomputedResult
    }
}

