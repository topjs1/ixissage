package com.ixissage.app.data

import android.content.Context
import org.json.JSONArray

class MessageRepository(
    private val context: Context,
) {
    fun loadSampleMessages(): List<SampleMessage> {
        val json = context.assets.open("sample_messages.json")
            .bufferedReader()
            .use { it.readText() }
        val array = JSONArray(json)

        return buildList {
            for (index in 0 until array.length()) {
                val item = array.getJSONObject(index)
                add(
                    SampleMessage(
                        id = item.getString("id"),
                        sender = item.getString("sender"),
                        body = item.getString("body"),
                        groundTruthLabel = item.getString("groundTruthLabel"),
                        precomputedResult = ClassificationResult(
                            normalProbability = item.getDouble("normalProbability").toFloat(),
                            phishingProbability = item.getDouble("phishingProbability").toFloat(),
                            predictedLabel = item.getString("predictedLabel"),
                        ),
                    ),
                )
            }
        }
    }
}
