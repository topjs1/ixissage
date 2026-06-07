package com.ixissage.app.data

data class SampleMessage(
    val id: String,
    val sender: String,
    val body: String,
    val groundTruthLabel: String,
    val precomputedResult: ClassificationResult,
)

data class ClassificationResult(
    val normalProbability: Float,
    val phishingProbability: Float,
    val predictedLabel: String,
)

enum class AiBadge(val label: String) {
    Normal("정상"),
    Caution("주의"),
    Warning("스팸 경고"),
}

fun badgeForProbability(phishingProbability: Float): AiBadge = when {
    phishingProbability >= 0.70 -> AiBadge.Warning
    phishingProbability >= 0.40 -> AiBadge.Caution
    else -> AiBadge.Normal
}
