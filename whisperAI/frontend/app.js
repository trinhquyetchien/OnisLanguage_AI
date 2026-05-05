const form = document.querySelector("#uploadForm");
const fileInput = document.querySelector("#fileInput");
const fileName = document.querySelector("#fileName");
const statusBox = document.querySelector("#status");
const submitButton = document.querySelector("#submitButton");
const copyButton = document.querySelector("#copyButton");
const meta = document.querySelector("#meta");
const mediaPreview = document.querySelector("#mediaPreview");
const audioPlayer = document.querySelector("#audioPlayer");
const videoPlayer = document.querySelector("#videoPlayer");
const transcriptList = document.querySelector("#transcriptList");
const tokenList = document.querySelector("#tokenList");

let selectedFileUrl = null;
let activePlayer = audioPlayer;
let transcriptText = "";
let activeSegmentId = null;

function setStatus(message, isError = false) {
  statusBox.textContent = message;
  statusBox.classList.toggle("error", isError);
}

fileInput.addEventListener("change", () => {
  const file = fileInput.files[0];
  fileName.textContent = file ? `${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)` : "Ho tro file audio va video";

  if (selectedFileUrl) {
    URL.revokeObjectURL(selectedFileUrl);
  }

  if (!file) {
    mediaPreview.hidden = true;
    return;
  }

  selectedFileUrl = URL.createObjectURL(file);
  const isVideo = file.type.startsWith("video/");
  activePlayer = isVideo ? videoPlayer : audioPlayer;

  audioPlayer.hidden = isVideo;
  videoPlayer.hidden = !isVideo;
  audioPlayer.removeAttribute("src");
  videoPlayer.removeAttribute("src");
  activePlayer.src = selectedFileUrl;
  mediaPreview.hidden = false;
});

function formatTime(seconds) {
  const safeSeconds = Math.max(0, Math.floor(seconds));
  const minutes = String(Math.floor(safeSeconds / 60)).padStart(2, "0");
  const rest = String(safeSeconds % 60).padStart(2, "0");
  return `${minutes}:${rest}`;
}

function createTokenNode(token) {
  const wrapper = document.createElement("span");
  wrapper.className = "jp-token";
  wrapper.title = `${token.pos_text || "Khong ro tu loai"} | Dang goc: ${token.lemma || token.surface}`;

  if (token.has_kanji && token.reading) {
    const ruby = document.createElement("ruby");
    ruby.textContent = token.surface;

    const rt = document.createElement("rt");
    rt.textContent = token.reading;
    ruby.appendChild(rt);
    wrapper.appendChild(ruby);
  } else {
    wrapper.textContent = token.surface;
  }

  return wrapper;
}

function renderTokenText(container, tokens, fallbackText) {
  container.innerHTML = "";

  if (!tokens?.length) {
    container.textContent = fallbackText || "";
    return;
  }

  tokens.forEach((token) => {
    container.appendChild(createTokenNode(token));
  });
}

function renderSegments(segments) {
  transcriptList.innerHTML = "";

  if (!segments.length) {
    transcriptList.innerHTML = '<p class="empty-result">Khong co transcript.</p>';
    return;
  }

  const fragment = document.createDocumentFragment();
  segments.forEach((segment) => {
    const row = document.createElement("button");
    row.type = "button";
    row.className = "transcript-segment";
    row.dataset.start = segment.start;
    row.dataset.end = segment.end;
    row.dataset.segmentId = segment.id;

    const time = document.createElement("span");
    time.className = "segment-time";
    time.textContent = formatTime(segment.start);

    const text = document.createElement("span");
    text.className = "segment-text";
    renderTokenText(text, segment.tokens || [], segment.text || "");

    row.append(time, text);
    row.addEventListener("click", () => {
      activePlayer.currentTime = Number(segment.start);
      activePlayer.play();
    });
    fragment.appendChild(row);
  });

  transcriptList.appendChild(fragment);
}

function renderTokenList(tokens) {
  tokenList.innerHTML = "";

  if (!tokens?.length) {
    tokenList.innerHTML = '<p class="empty-result">Khong co token de phan tich.</p>';
    return;
  }

  const fragment = document.createDocumentFragment();
  tokens.forEach((token) => {
    const item = document.createElement("article");
    item.className = "token-card";

    const surface = document.createElement("div");
    surface.className = "token-surface";
    surface.appendChild(createTokenNode(token));

    const details = document.createElement("div");
    details.className = "token-details";

    const pos = document.createElement("span");
    pos.textContent = token.pos_text || "Khong ro tu loai";

    const reading = document.createElement("span");
    reading.textContent = token.reading ? `Furigana: ${token.reading}` : "Furigana: -";

    const lemma = document.createElement("span");
    lemma.textContent = `Dang goc: ${token.lemma || token.surface}`;

    details.append(pos, reading, lemma);
    item.append(surface, details);
    fragment.appendChild(item);
  });

  tokenList.appendChild(fragment);
}


function syncTranscript() {
  const currentTime = activePlayer.currentTime;
  const segments = [...document.querySelectorAll(".transcript-segment")];
  const currentSegment = segments.find((segment) => {
    const start = Number(segment.dataset.start);
    const end = Number(segment.dataset.end);
    return currentTime >= start && currentTime < end;
  });

  if (!currentSegment || currentSegment.dataset.segmentId === activeSegmentId) {
    return;
  }

  document.querySelector(".transcript-segment.active")?.classList.remove("active");
  currentSegment.classList.add("active");
  activeSegmentId = currentSegment.dataset.segmentId;
  currentSegment.scrollIntoView({ block: "nearest", behavior: "smooth" });
}

audioPlayer.addEventListener("timeupdate", syncTranscript);
videoPlayer.addEventListener("timeupdate", syncTranscript);

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const file = fileInput.files[0];
  if (!file) {
    setStatus("Vui long chon file truoc khi chuyen doi.", true);
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  submitButton.disabled = true;
  copyButton.disabled = true;
  transcriptText = "";
  activeSegmentId = null;
  transcriptList.innerHTML = '<p class="empty-result">Dang xu ly...</p>';
  tokenList.innerHTML = '<p class="empty-result">Dang phan tich tieng Nhat...</p>';
  meta.textContent = "";
  setStatus("Dang tai file len va xu ly bang Whisper...");

  try {
    const response = await fetch("/api/transcribe", {
      method: "POST",
      body: formData,
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "Backend tra ve loi khong xac dinh.");
    }

    transcriptText = data.text || "";
    renderSegments(data.segments || []);
    renderTokenList(data.tokens || []);
    copyButton.disabled = !data.text;
    meta.textContent = `Ngon ngu: ${data.language || "khong xac dinh"} | Thoi gian xu ly: ${data.duration_seconds}s`;
    setStatus("Hoan tat.");
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    submitButton.disabled = false;
  }
});

copyButton.addEventListener("click", async () => {
  if (!transcriptText) {
    return;
  }

  await navigator.clipboard.writeText(transcriptText);
  setStatus("Da copy ket qua vao clipboard.");
});
