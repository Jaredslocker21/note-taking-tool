let mediaRecorder;
let audioChunks = [];
let startTime;
let timerInterval;
let lastResult = null;

const recordBtn = document.getElementById("recordBtn");
const stopBtn = document.getElementById("stopBtn");
const timerEl = document.getElementById("timer");
const statusEl = document.getElementById("status");
const resultsCard = document.getElementById("resultsCard");
const titleInput = document.getElementById("titleInput");
const saveBtn = document.getElementById("saveBtn");

const APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbytREiEO9koVUKEWSJTwQpd1NHCvMFKPMljIRsdXuaWdRcXOq-ac2PqDPoWiBMbyLK-/exec";

recordBtn.addEventListener("click", startRecording);
stopBtn.addEventListener("click", stopRecording);
saveBtn.addEventListener("click", saveToGoogleDoc);

async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    audioChunks = [];

    mediaRecorder.ondataavailable = (e) => {
      audioChunks.push(e.data);
    };

    mediaRecorder.onstop = async () => {
      const audioBlob = new Blob(audioChunks, { type: "audio/webm" });
      statusEl.textContent = "Uploading and transcribing...";
      await sendToBackend(audioBlob);
    };

    mediaRecorder.start();
    startTime = Date.now();
    timerInterval = setInterval(updateTimer, 1000);

    recordBtn.disabled = true;
    stopBtn.disabled = false;
    statusEl.textContent = "Recording...";
    resultsCard.style.display = "none";
  } catch (err) {
    console.error(err);
    statusEl.textContent = "Microphone access denied";
  }
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    mediaRecorder.stop();
    mediaRecorder.stream.getTracks().forEach(track => track.stop());
  }
  clearInterval(timerInterval);
  recordBtn.disabled = false;
  stopBtn.disabled = true;
}

function updateTimer() {
  const elapsed = Math.floor((Date.now() - startTime) / 1000);
  const minutes = String(Math.floor(elapsed / 60)).padStart(2, "0");
  const seconds = String(elapsed % 60).padStart(2, "0");
  timerEl.textContent = `${minutes}:${seconds}`;
}

async function sendToBackend(audioBlob) {
  const formData = new FormData();
  formData.append("audio", audioBlob, "recording.webm");
  formData.append("title", titleInput.value || "Untitled Meeting");

  try {
    const response = await fetch("/transcribe", {
      method: "POST",
      body: formData
    });

    const data = await response.json();
    lastResult = data;

    document.getElementById("summary").textContent = data.summary;
    document.getElementById("actions").textContent = data.actions;
    document.getElementById("transcript").textContent = data.transcript;

    resultsCard.style.display = "block";
    statusEl.textContent = "Done!";
  } catch (err) {
    console.error(err);
    statusEl.textContent = "Error talking to server";
  }
}

async function saveToGoogleDoc() {
  if (!lastResult) {
    alert("Nothing to save yet. Please record first.");
    return;
  }

  statusEl.textContent = "Creating Google Doc...";
  saveBtn.disabled = true;

  const payload = {
    title: titleInput.value || lastResult.title || "Untitled Meeting",
    summary: lastResult.summary,
    actions: lastResult.actions,
    transcript: lastResult.transcript,
    duration: timerEl.textContent
  };

  try {
    const response = await fetch("/save", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });

    const result = await response.json();

    if (result.status === "success") {
      statusEl.textContent = "Google Doc created! Check your Google Drive.";
    } else {
      statusEl.textContent = "Error: " + result.message;
    }
  } catch (err) {
    console.error(err);
    statusEl.textContent = "Failed to create Google Doc";
  }

  saveBtn.disabled = false;
}