package com.ixissage.app.classifier

import android.content.Context
import com.ixissage.app.data.ClassificationResult
import com.ixissage.app.data.SampleMessage
import java.util.Locale
import kotlin.math.exp
import kotlin.math.ln
import kotlin.math.sqrt
import org.json.JSONObject

class OnDeviceBaselineClassifier(
    context: Context,
    private val assetName: String = "baseline_tfidf_logreg.json",
) : SmishingClassifier {
    private val appContext = context.applicationContext
    private val model: BaselineModel by lazy {
        BaselineModel.load(appContext, assetName)
    }

    override fun classify(message: SampleMessage): ClassificationResult {
        return model.predict(message.body)
    }
}

private data class BaselineModel(
    val vocabulary: Map<String, Int>,
    val idf: FloatArray,
    val coefficients: FloatArray,
    val intercept: Double,
    val minNgram: Int,
    val maxNgram: Int,
    val lowercase: Boolean,
    val sublinearTf: Boolean,
    val stripUrlLikeSpans: Boolean,
) {
    fun predict(text: String): ClassificationResult {
        val counts = countKnownNgrams(preprocess(text))
        val values = HashMap<Int, Double>(counts.size)
        var normSquared = 0.0

        for ((featureIndex, count) in counts) {
            val tf = if (sublinearTf) ln(count.toDouble()) + 1.0 else count.toDouble()
            val value = tf * idf[featureIndex].toDouble()
            values[featureIndex] = value
            normSquared += value * value
        }

        val norm = sqrt(normSquared)
        var decision = intercept
        if (norm > 0.0) {
            for ((featureIndex, value) in values) {
                decision += (value / norm) * coefficients[featureIndex].toDouble()
            }
        }

        val phishingProbability = sigmoid(decision).toFloat()
        val normalProbability = (1.0f - phishingProbability).coerceIn(0f, 1f)
        val predictedLabel = if (phishingProbability >= normalProbability) {
            "smishing"
        } else {
            "normal"
        }

        return ClassificationResult(
            normalProbability = normalProbability,
            phishingProbability = phishingProbability.coerceIn(0f, 1f),
            predictedLabel = predictedLabel,
        )
    }

    private fun preprocess(text: String): String {
        val withoutUrlSurface = if (stripUrlLikeSpans) {
            urlLikePattern.replace(text, " ")
        } else {
            text
        }
        val lowered = if (lowercase) withoutUrlSurface.lowercase(Locale.ROOT) else withoutUrlSurface
        return repeatedWhitespace.replace(lowered, " ").trim()
    }

    private fun countKnownNgrams(text: String): HashMap<Int, Int> {
        val counts = HashMap<Int, Int>()
        val textLength = text.length
        if (textLength < minNgram) {
            return counts
        }

        val lastNgram = minOf(maxNgram, textLength)
        for (ngramSize in minNgram..lastNgram) {
            val lastStart = textLength - ngramSize
            for (start in 0..lastStart) {
                val term = text.substring(start, start + ngramSize)
                val featureIndex = vocabulary[term] ?: continue
                counts[featureIndex] = (counts[featureIndex] ?: 0) + 1
            }
        }
        return counts
    }

    companion object {
        private val repeatedWhitespace = Regex("\\s\\s+")
        private val urlLikePattern = Regex(
            pattern = "\\b(?:https?://|www\\.)\\S+|" +
                "\\b[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\\." +
                "(?:com|net|org|kr|co\\.kr|go\\.kr|or\\.kr|ne\\.kr|io|me|ly|live|site|xyz)\\b\\S*",
            options = setOf(RegexOption.IGNORE_CASE),
        )

        fun load(context: Context, assetName: String): BaselineModel {
            val json = context.assets.open(assetName)
                .bufferedReader()
                .use { it.readText() }
            val root = JSONObject(json)
            val vectorizer = root.getJSONObject("vectorizer")
            val classifier = root.getJSONObject("classifier")
            val textNormalization = root.optJSONObject("textNormalization")
            val ngramRange = vectorizer.getJSONArray("ngramRange")
            val features = root.getJSONArray("features")
            val featureCount = features.length()

            val vocabulary = HashMap<String, Int>((featureCount * 4 / 3) + 1)
            val idf = FloatArray(featureCount)
            val coefficients = FloatArray(featureCount)

            for (index in 0 until featureCount) {
                val feature = features.getJSONObject(index)
                vocabulary[feature.getString("term")] = index
                idf[index] = feature.getDouble("idf").toFloat()
                coefficients[index] = feature.getDouble("coef").toFloat()
            }

            return BaselineModel(
                vocabulary = vocabulary,
                idf = idf,
                coefficients = coefficients,
                intercept = classifier.getDouble("intercept"),
                minNgram = ngramRange.getInt(0),
                maxNgram = ngramRange.getInt(1),
                lowercase = vectorizer.getBoolean("lowercase"),
                sublinearTf = vectorizer.getBoolean("sublinearTf"),
                stripUrlLikeSpans = textNormalization?.optBoolean("stripUrlLikeSpans", false) ?: false,
            )
        }

        private fun sigmoid(value: Double): Double {
            return if (value >= 0.0) {
                val z = exp(-value)
                1.0 / (1.0 + z)
            } else {
                val z = exp(value)
                z / (1.0 + z)
            }
        }
    }
}
