package com.ixissage.app.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.ixissage.app.data.AiBadge
import com.ixissage.app.data.badgeForProbability

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MessageListScreen(
    state: MessageUiState,
    onMessageClick: (String) -> Unit,
    onManualTestClick: () -> Unit,
) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("ixissage", fontWeight = FontWeight.SemiBold)
                        Text(
                            text = "AI 문자 분석 데모 · ${state.messages.size}개",
                            style = MaterialTheme.typography.labelMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.surface,
                ),
                actions = {
                    IconButton(onClick = onManualTestClick) {
                        Icon(
                            imageVector = Icons.Filled.Edit,
                            contentDescription = "직접 테스트",
                        )
                    }
                },
            )
        },
    ) { padding ->
        Surface(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding),
            color = MaterialTheme.colorScheme.background,
        ) {
            when {
                state.isLoading -> LoadingState()
                state.errorMessage != null -> ErrorState(state.errorMessage)
                else -> MessageList(
                    messages = state.messages,
                    onMessageClick = onMessageClick,
                )
            }
        }
    }
}

@Composable
private fun MessageList(
    messages: List<ClassifiedMessage>,
    onMessageClick: (String) -> Unit,
) {
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(horizontal = 16.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        items(messages, key = { it.sample.id }) { message ->
            MessageRow(
                message = message,
                onClick = { onMessageClick(message.sample.id) },
            )
        }
    }
}

@Composable
private fun MessageRow(
    message: ClassifiedMessage,
    onClick: () -> Unit,
) {
    val sample = message.sample
    val classification = message.classification

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
        shape = RoundedCornerShape(8.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface,
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(14.dp),
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    text = sample.sender,
                    modifier = Modifier.weight(1f),
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.SemiBold,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                Spacer(modifier = Modifier.width(10.dp))
                AiBadgePill(
                    badge = badgeForProbability(classification.phishingProbability),
                )
            }

            Spacer(modifier = Modifier.height(8.dp))

            Text(
                text = sample.body,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )

            Spacer(modifier = Modifier.height(10.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    text = "예측: ${classification.predictedLabel}",
                    modifier = Modifier.weight(1f),
                    style = MaterialTheme.typography.labelLarge,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                ProbabilityText(classification.phishingProbability)
            }
        }
    }
}

@Composable
fun AiBadgePill(
    badge: AiBadge,
    modifier: Modifier = Modifier,
) {
    val colors = badgeColors(badge)
    Box(
        modifier = modifier
            .clip(RoundedCornerShape(6.dp))
            .background(colors.background)
            .padding(horizontal = 9.dp, vertical = 5.dp),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text = badge.label,
            style = MaterialTheme.typography.labelMedium,
            color = colors.foreground,
            fontWeight = FontWeight.SemiBold,
            maxLines = 1,
        )
    }
}

@Composable
fun ProbabilityText(value: Float) {
    Text(
        text = "스미싱 ${formatProbability(value)}",
        style = MaterialTheme.typography.labelLarge,
        color = MaterialTheme.colorScheme.onSurface,
        fontWeight = FontWeight.SemiBold,
    )
}

fun formatProbability(value: Float): String = "${(value * 100).toInt()}%"

private data class BadgeColors(
    val background: Color,
    val foreground: Color,
)

@Composable
private fun badgeColors(badge: AiBadge): BadgeColors = when (badge) {
    AiBadge.Normal -> BadgeColors(
        background = Color(0xFFE3F5EC),
        foreground = Color(0xFF14633A),
    )

    AiBadge.Caution -> BadgeColors(
        background = Color(0xFFFFF0C2),
        foreground = Color(0xFF7A4D00),
    )

    AiBadge.Warning -> BadgeColors(
        background = Color(0xFFFFD9DE),
        foreground = Color(0xFF9C1F32),
    )
}

@Composable
private fun LoadingState() {
    Box(
        modifier = Modifier.fillMaxSize(),
        contentAlignment = Alignment.Center,
    ) {
        CircularProgressIndicator(modifier = Modifier.size(36.dp))
    }
}

@Composable
private fun ErrorState(message: String) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text = message,
            color = MaterialTheme.colorScheme.error,
            style = MaterialTheme.typography.bodyLarge,
        )
    }
}
