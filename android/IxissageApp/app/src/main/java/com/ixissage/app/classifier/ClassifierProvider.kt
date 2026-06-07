package com.ixissage.app.classifier

import android.content.Context

object ClassifierProvider {
    fun provideSampleClassifier(): SmishingClassifier {
        return PrecomputedSampleClassifier()
    }

    fun provideOnDeviceBaselineClassifier(context: Context): SmishingClassifier {
        return OnDeviceBaselineClassifier(context)
    }

    fun provideMockClassifier(): SmishingClassifier {
        return MockSmishingClassifier()
    }
}
