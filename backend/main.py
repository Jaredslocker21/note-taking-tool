from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from faster_whisper import WhisperModel
import uvicorn
import os
import requests
import tempfile
import shutil

app = FastAPI(title="Note Taking Tool")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Correct path to project root
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
STATIC_DIR = os.path.join(ROOT, "static")

print("ROOT folder is:", ROOT)
print("Looking for index.html at:", os.path.join(ROOT, "index.html"))

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbytREiEO9koVUKEWSJTwQpd1NHCvMFKPMljIRsdXuaWdRcXOq-ac2PqDPoWiBMbyLK-/exec"

print("Loading Whisper model...")
model = WhisperModel("small", device="cpu", compute_type="int8")
print("Whisper model loaded!")

def ask_ollama(prompt: str) -> str:
    try:
        response = requests.post(
            "http://127.0.0.1:11434/api/generate",
            json={
                "model": "tinyllama",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3
                }
            },
            timeout=90
        )
        result = response.json()
        text = result.get("response", "").strip()
        print("=== Ollama raw response ===")
        print(text)
        print("===========================")
        return text
    except Exception as e:
        print("Ollama error:", str(e))
        return ""

@app.get("/")
def home():
    index_path = os.path.join(ROOT, "index.html")
    if not os.path.exists(index_path):
        return {"error": f"index.html not found at {index_path}"}
    return FileResponse(index_path)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/transcribe")
async def transcribe(audio: UploadFile = File(...), title: str = Form("Untitled Meeting")):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
        shutil.copyfileobj(audio.file, tmp)
        tmp_path = tmp.name

    try:
        # Transcribe with Whisper
        segments, info = model.transcribe(tmp_path, beam_size=5)
        transcript_parts = [segment.text.strip() for segment in segments]
        full_transcript = " ".join(transcript_parts)

        if not full_transcript:
            full_transcript = "(No speech detected)"

        # Generate Summary + Action Items
        prompt = f"""Transcript:
{full_transcript}

Please do two things:
1. Write a short 2-sentence summary of the meeting.
2. List the action items as bullet points.

Format your answer exactly like this:

SUMMARY:
Write the summary here.

ACTION ITEMS:
- First action
- Second action
"""

        llm_response = ask_ollama(prompt)

        summary = full_transcript[:200] + "..." if len(full_transcript) > 200 else full_transcript
        actions = "- No clear action items found"

        if llm_response:
            # Extract SUMMARY
            if "SUMMARY:" in llm_response.upper():
                try:
                    after = llm_response.split("SUMMARY:")[1]
                    summary = after.split("ACTION")[0].strip()
                    summary = summary.replace("SUMMARY:", "").strip()
                except:
                    pass

            # Extract ACTION ITEMS
            if "ACTION ITEMS:" in llm_response.upper() or "ACTION ITEM" in llm_response.upper():
                try:
                    actions_part = llm_response.split("ACTION ITEMS:")[-1]
                    actions = actions_part.strip()
                except:
                    lines = [l.strip() for l in llm_response.splitlines() if l.strip().startswith("-")]
                    if lines:
                        actions = "\n".join(lines)

            # Final cleanup
            if summary.lower().startswith("meeting transcript") or len(summary) < 20:
                summary = full_transcript[:180] + "..." if len(full_transcript) > 180 else full_transcript

        return {
            "title": title,
            "summary": summary,
            "actions": actions,
            "transcript": full_transcript
        }

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

class SaveRequest(BaseModel):
    title: str
    summary: str
    actions: str
    transcript: str
    duration: str = ""

@app.post("/save")
async def save_to_google_doc(data: SaveRequest):
    try:
        response = requests.post(
            APPS_SCRIPT_URL,
            json={
                "title": data.title,
                "summary": data.summary,
                "actions": data.actions,
                "transcript": data.transcript,
                "duration": data.duration
            },
            headers={"Content-Type": "application/json"},
            timeout=30
        )

        print("=== Apps Script Response ===")
        print("Status code:", response.status_code)
        print("Response text:", response.text[:300])
        print("============================")

        return {
            "status": "success",
            "message": "Google Doc creation request sent"
        }

    except Exception as e:
        print("Error:", str(e))
        return {
            "status": "error",
            "message": str(e)
        }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)