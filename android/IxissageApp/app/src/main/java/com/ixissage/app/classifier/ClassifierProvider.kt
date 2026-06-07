package com.ixissage.app.classifier

object ClassifierProvider {
    fun provideSampleClassifier(): SmishingClassifier {
        return PrecomputedSampleClassifier()
    }

    fun provideMockClassifier(): SmishingClassifier {
        return MockSmishingClassifier()
    }
}

