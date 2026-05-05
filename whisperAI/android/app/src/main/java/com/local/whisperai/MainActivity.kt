package com.local.whisperai

import android.content.Context
import android.database.Cursor
import android.net.Uri
import android.os.Bundle
import android.provider.OpenableColumns
import android.view.ViewGroup
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.media3.common.MediaItem
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.ui.PlayerView
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody
import okio.BufferedSink
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.util.concurrent.TimeUnit

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                WhisperMobileApp()
            }
        }
    }
}

data class Token(
    val surface: String,
    val reading: String,
    val lemma: String,
    val posText: String,
    val hasKanji: Boolean,
)

data class TranscriptSegment(
    val id: Int,
    val start: Double,
    val end: Double,
    val text: String,
    val tokens: List<Token>,
)

data class TranscribeResponse(
    val text: String,
    val language: String,
    val durationSeconds: Double,
    val segments: List<TranscriptSegment>,
    val tokens: List<Token>,
)

@Composable
fun WhisperMobileApp() {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var serverUrl by remember { mutableStateOf("http://10.0.2.2:8000") }
    var selectedUri by remember { mutableStateOf<Uri?>(null) }
    var selectedName by remember { mutableStateOf("Chua chon file") }
    var isLoading by remember { mutableStateOf(false) }
    var status by remember { mutableStateOf("San sang.") }
    var result by remember { mutableStateOf<TranscribeResponse?>(null) }
    var currentMs by remember { mutableLongStateOf(0L) }

    val picker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) {
            context.contentResolver.takePersistableUriPermission(
                uri,
                android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION,
            )
            selectedUri = uri
            selectedName = getFileName(context, uri)
            result = null
            status = "Da chon $selectedName"
        }
    }

    Surface(modifier = Modifier.fillMaxSize(), color = Color(0xFFF4F6F8)) {
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            item {
                Text("Whisper AI Mobile", fontSize = 26.sp, fontWeight = FontWeight.Bold)
                Text("Upload audio/video len FastAPI backend de transcribe tieng Nhat.")
            }

            item {
                Card(shape = RoundedCornerShape(8.dp), colors = CardDefaults.cardColors(containerColor = Color.White)) {
                    Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                        OutlinedTextField(
                            value = serverUrl,
                            onValueChange = { serverUrl = it },
                            modifier = Modifier.fillMaxWidth(),
                            label = { Text("Backend URL") },
                            singleLine = true,
                        )

                        Row(horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically) {
                            Button(onClick = { picker.launch(arrayOf("audio/*", "video/*")) }) {
                                Text("Chon file")
                            }
                            Text(selectedName, maxLines = 1, overflow = TextOverflow.Ellipsis)
                        }

                        Button(
                            enabled = selectedUri != null && !isLoading,
                            onClick = {
                                val uri = selectedUri ?: return@Button
                                scope.launch {
                                    isLoading = true
                                    status = "Dang upload va xu ly..."
                                    result = null
                                    runCatching { transcribe(context, serverUrl, uri) }
                                        .onSuccess {
                                            result = it
                                            status = "Hoan tat: ${it.language}, ${it.durationSeconds}s"
                                        }
                                        .onFailure { status = it.message ?: "Loi khong xac dinh" }
                                    isLoading = false
                                }
                            },
                        ) {
                            Text("Bat dau transcribe")
                        }

                        if (isLoading) {
                            Row(horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically) {
                                CircularProgressIndicator(modifier = Modifier.height(22.dp), strokeWidth = 2.dp)
                                Text(status)
                            }
                        } else {
                            Text(status)
                        }
                    }
                }
            }

            selectedUri?.let { uri ->
                item {
                    MediaPlayer(uri = uri, onPositionChanged = { currentMs = it })
                }
            }

            result?.let { response ->
                item {
                    Text("Transcript", fontSize = 20.sp, fontWeight = FontWeight.Bold)
                }

                items(response.segments) { segment ->
                    val currentSeconds = currentMs / 1000.0
                    TranscriptRow(
                        segment = segment,
                        active = currentSeconds >= segment.start && currentSeconds < segment.end,
                    )
                }

                item {
                    Text("Tu loai va furigana", fontSize = 20.sp, fontWeight = FontWeight.Bold)
                    Spacer(Modifier.height(8.dp))
                    TokenGrid(response.tokens)
                }
            }
        }
    }
}

@Composable
fun MediaPlayer(uri: Uri, onPositionChanged: (Long) -> Unit) {
    val context = LocalContext.current
    val player = remember {
        ExoPlayer.Builder(context).build()
    }

    LaunchedEffect(uri) {
        player.setMediaItem(MediaItem.fromUri(uri))
        player.prepare()
    }

    LaunchedEffect(player) {
        while (true) {
            onPositionChanged(player.currentPosition)
            delay(250)
        }
    }

    DisposableEffect(Unit) {
        onDispose { player.release() }
    }

    Card(shape = RoundedCornerShape(8.dp), colors = CardDefaults.cardColors(containerColor = Color.White)) {
        AndroidView(
            modifier = Modifier
                .fillMaxWidth()
                .height(220.dp),
            factory = {
                PlayerView(it).apply {
                    this.player = player
                    layoutParams = ViewGroup.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.MATCH_PARENT,
                    )
                }
            },
        )
    }
}

@Composable
fun TranscriptRow(segment: TranscriptSegment, active: Boolean) {
    val background = if (active) Color(0xFFDFF5F1) else Color.White
    val borderText = if (active) Color(0xFF0F766E) else Color(0xFF667085)

    Card(shape = RoundedCornerShape(8.dp), colors = CardDefaults.cardColors(containerColor = background)) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text(formatTime(segment.start), color = borderText, fontWeight = FontWeight.Bold)
            TokenLine(segment.tokens, fallback = segment.text)
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun TokenLine(tokens: List<Token>, fallback: String) {
    if (tokens.isEmpty()) {
        Text(fallback)
        return
    }

    FlowRow(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(2.dp)) {
        tokens.forEach { token ->
            JapaneseToken(token)
        }
    }
}

@Composable
fun JapaneseToken(token: Token) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        if (token.hasKanji && token.reading.isNotBlank()) {
            Text(token.reading, fontSize = 10.sp, color = Color(0xFF667085), maxLines = 1)
        }
        Text(token.surface, fontSize = 18.sp)
    }
}

@Composable
fun TokenGrid(tokens: List<Token>) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        tokens.forEach { token ->
            Card(shape = RoundedCornerShape(8.dp), colors = CardDefaults.cardColors(containerColor = Color.White)) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(10.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    JapaneseToken(token)
                    Column(horizontalAlignment = Alignment.End) {
                        Text(token.posText.ifBlank { "Khong ro tu loai" }, color = Color(0xFF667085))
                        Text("Dang goc: ${token.lemma}", color = Color(0xFF667085), fontSize = 13.sp)
                    }
                }
            }
        }
    }
}

fun formatTime(seconds: Double): String {
    val safe = seconds.toLong().coerceAtLeast(0)
    val minutes = safe / 60
    val rest = safe % 60
    return "%02d:%02d".format(minutes, rest)
}

suspend fun transcribe(context: Context, serverUrl: String, uri: Uri): TranscribeResponse {
    return withContext(Dispatchers.IO) {
        val cleanUrl = serverUrl.trim().trimEnd('/')
        val client = OkHttpClient.Builder()
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.MINUTES)
            .writeTimeout(30, TimeUnit.MINUTES)
            .build()

        val body = MultipartBody.Builder()
            .setType(MultipartBody.FORM)
            .addFormDataPart("file", getFileName(context, uri), uri.asRequestBody(context))
            .build()

        val request = Request.Builder()
            .url("$cleanUrl/api/transcribe")
            .post(body)
            .build()

        client.newCall(request).execute().use { response ->
            val text = response.body?.string().orEmpty()
            if (!response.isSuccessful) {
                throw IOException("Backend loi ${response.code}: $text")
            }
            parseTranscribeResponse(JSONObject(text))
        }
    }
}

fun Uri.asRequestBody(context: Context): RequestBody {
    val contentType = context.contentResolver.getType(this)?.toMediaTypeOrNull()
    return object : RequestBody() {
        override fun contentType() = contentType

        override fun contentLength(): Long {
            return querySize(context, this@asRequestBody)
        }

        override fun writeTo(sink: BufferedSink) {
            context.contentResolver.openInputStream(this@asRequestBody).use { input ->
                if (input == null) throw IOException("Khong doc duoc file da chon")
                val buffer = ByteArray(DEFAULT_BUFFER_SIZE)
                while (true) {
                    val read = input.read(buffer)
                    if (read == -1) break
                    sink.write(buffer, 0, read)
                }
            }
        }
    }
}

fun getFileName(context: Context, uri: Uri): String {
    val cursor: Cursor? = context.contentResolver.query(uri, null, null, null, null)
    cursor.use {
        if (it != null && it.moveToFirst()) {
            val index = it.getColumnIndex(OpenableColumns.DISPLAY_NAME)
            if (index >= 0) return it.getString(index)
        }
    }
    return "upload"
}

fun querySize(context: Context, uri: Uri): Long {
    val cursor: Cursor? = context.contentResolver.query(uri, null, null, null, null)
    cursor.use {
        if (it != null && it.moveToFirst()) {
            val index = it.getColumnIndex(OpenableColumns.SIZE)
            if (index >= 0) return it.getLong(index)
        }
    }
    return -1L
}

fun parseTranscribeResponse(json: JSONObject): TranscribeResponse {
    return TranscribeResponse(
        text = json.optString("text"),
        language = json.optString("language"),
        durationSeconds = json.optDouble("duration_seconds"),
        segments = parseSegments(json.optJSONArray("segments") ?: JSONArray()),
        tokens = parseTokens(json.optJSONArray("tokens") ?: JSONArray()),
    )
}

fun parseSegments(array: JSONArray): List<TranscriptSegment> {
    return List(array.length()) { index ->
        val item = array.getJSONObject(index)
        TranscriptSegment(
            id = item.optInt("id"),
            start = item.optDouble("start"),
            end = item.optDouble("end"),
            text = item.optString("text"),
            tokens = parseTokens(item.optJSONArray("tokens") ?: JSONArray()),
        )
    }
}

fun parseTokens(array: JSONArray): List<Token> {
    return List(array.length()) { index ->
        val item = array.getJSONObject(index)
        Token(
            surface = item.optString("surface"),
            reading = item.optString("reading"),
            lemma = item.optString("lemma"),
            posText = item.optString("pos_text"),
            hasKanji = item.optBoolean("has_kanji"),
        )
    }
}
