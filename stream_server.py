# import os, io, json, base64, wave, audioop, asyncio, websockets, aiohttp, time, re, glob, requests
# from concurrent.futures import ThreadPoolExecutor
# from datetime import datetime
# from dotenv import load_dotenv
# from openai import OpenAI
# from twilio.rest import Client as TwilioClient
# from pydub import AudioSegment 


# # ===== Load Environment =====
# load_dotenv()

# # ===== ENVIRONMENT VARIABLES =====
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# PORT = int(os.getenv("STREAM_PORT", 8000))
# FLASK_SOCKET_URL = os.getenv("FLASK_SOCKET_URL")
# PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL")
# FLASK_REPORT_URL = f"{PUBLIC_BASE_URL}/report"

# TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
# TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

# # NEW: Deepgram API key
# DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

# # ===== CLIENTS =====
# client = OpenAI(api_key=OPENAI_API_KEY)
# twilio_client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# # ===== SETTINGS =====
# SAMPLE_RATE = 8000
# BYTES_PER_SAMPLE = 2
# POOL = ThreadPoolExecutor(max_workers=8)
# LOG_FILE = "conversation_log.txt"
# CURRENT_CALL_SID = None

# # ===== TTS CLEANUP =====
# def cleanup_tts():
#     """
#     Delete all temporary TTS files (tts_*.mp3) before a new call starts,
#     but preserve permanent audio assets like greeting.mp3 and ai_reply.mp3.
#     """
#     tts_dir = os.path.join("static", "tts")
#     try:
#         if not os.path.exists(tts_dir):
#             os.makedirs(tts_dir)
#             return
#         files = glob.glob(os.path.join(tts_dir, "*.mp3"))
#         deleted = 0
#         for f in files:
#             base = os.path.basename(f).lower()
#             if base.startswith("tts_"):  # only remove generated temporary files
#                 os.remove(f)
#                 deleted += 1
#         print(f"🧹 Cleaned up {deleted} temporary TTS files (permanent files preserved).")
#     except Exception as e:
#         print(f"⚠️ TTS cleanup failed: {e}")

# def cleanup_recordings():
#     rec_dir = os.path.join("static", "recordings")
#     try:
#         if not os.path.exists(rec_dir):
#             os.makedirs(rec_dir)
#             return
#         files = glob.glob(os.path.join(rec_dir, "*.mp3"))
#         deleted = 0
#         for f in files:
#             os.remove(f)
#             deleted += 1
#         print(f"🗑 Deleted {deleted} old call recordings.")
#     except Exception as e:
#         print(f"⚠ Recording cleanup failed: {e}")

# # ===== RESTAURANT CONTEXT =====
# RESTAURANT_INFO = """
# Restaurant Name: The Restaurant
# Cuisine: Italian & Continental
# Timings: 10:00 AM – 10:00 PM
# Location: 123 Main Street, Austin, TX
# Contact: +1 (507) 554-1673
# Menu Highlights:
#   - Starters: Garlic Bread, Caesar Salad, Bruschetta
#   - Main Course: Alfredo Pasta, Margherita Pizza, Lasagna
#   - Desserts: Tiramisu, Chocolate Mousse
#   - Beverages: Coffee, Wine, Fresh Juice
# Policies:
#   - Accepts reservations up to 10 people.
#   - Takeout and curbside pickup available.
#   - No home delivery.
# """

# # ===== UTILITIES =====
# def _ts(): 
#     return datetime.now().strftime("%H:%M:%S")

# def reset_log():
#     open(LOG_FILE, "w", encoding="utf-8").write(f"[{_ts()}] --- Call Started ---\n")

# def append_log(role, text):
#     if text:
#         with open(LOG_FILE, "a", encoding="utf-8") as f:
#             f.write(f"[{_ts()}] [{role}] {text}\n")

# def read_log():
#     try: 
#         return open(LOG_FILE, "r", encoding="utf-8").read()
#     except FileNotFoundError: 
#         return ""

# def mulaw_to_pcm16_16k(b: bytes) -> bytes:
#     pcm8k = audioop.ulaw2lin(b, 2)
#     pcm16k, _ = audioop.ratecv(pcm8k, 2, 1, 8000, 16000, None)
#     return audioop.mul(pcm16k, 2, 0.95)

# def pcm16k_to_wav(pcm16k: bytes) -> bytes:
#     buf = io.BytesIO()
#     with wave.open(buf, "wb") as wf:
#         wf.setnchannels(1)
#         wf.setsampwidth(2)
#         wf.setframerate(16000)
#         wf.writeframes(pcm16k)
#     return buf.getvalue()

# # ===== CONTACT NORMALIZER =====
# def normalize_contact_info(text: str) -> str:
#     t = text.lower()
#     t = t.replace(" at ", "@").replace(" dot ", ".").replace(" underscore ", "_").replace(" dash ", "-")
#     t = t.replace(" space ", " ").replace(" period ", ".").replace(" comma ", ",")
#     t = re.sub(r"\bcom(\s*)com\b", "com", t)
#     t = re.sub(r"[^0-9@._a-zA-Z+-]", " ", t)
#     t = re.sub(r"\s+", " ", t).strip()
#     return t

# # ===== AI MEMORY =====
# context = []

# def clean_repeated_words(text: str) -> str:
#     words = text.split()
#     cleaned = [w for i, w in enumerate(words) if i == 0 or w.lower() != words[i - 1].lower()]
#     return " ".join(cleaned)

# # ===== MEANINGLESS TEXT FILTER =====
# MEANINGLESS_PATTERNS = [
#     r"^\s*(hi|thanks|thank you.|thank you|okay|ok|yeah|yes|no|hmm|uh|ah|huh|bye|goodbye|you)\s*$"
# ]

# def is_potential_contact_info(text: str) -> bool:
#     if re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text): return True
#     if re.search(r"\b\d{7,15}\b", text): return True
#     if re.search(r"([a-zA-Z]-){2,}[a-zA-Z]", text): return True
#     if len(re.findall(r"\b(zero|one|two|three|four|five|six|seven|eight|nine)\b", text.lower())) >= 3: return True
#     return False

# def is_meaningful_text(text: str) -> bool:
#     if not text: return False
#     if is_potential_contact_info(text): return True
#     for pat in MEANINGLESS_PATTERNS:
#         if re.match(pat, text.lower()):
#             return False
#     words = text.split()
#     if len(words) < 2:
#         if re.search(r"[@\d]", text): return True
#         return False
#     return True

# # ===== TRANSCRIBE + AI RESPONSE (Deepgram instead of Whisper) =====
# def transcribe_and_reply(wav: bytes):
#     global context

#     # ---- Deepgram transcription ----
#     try:
#         if not DEEPGRAM_API_KEY:
#             print("⚠ Deepgram API key missing (DEEPGRAM_API_KEY).")
#             return "", ""

#         headers = {
#             "Authorization": f"Token {DEEPGRAM_API_KEY}",
#             "Content-Type": "audio/wav",
#         }
#         params = {
#             "model": "nova-3",       # Deepgram model
#             "smart_format": "true",  # punctuation, formatting
#             "language": "en-US",
#         }

#         dg_resp = requests.post(
#             "https://api.deepgram.com/v1/listen",
#             headers=headers,
#             params=params,
#             data=wav,
#             timeout=10,
#         )
#         dg_resp.raise_for_status()
#         dg_json = dg_resp.json()

#         # Deepgram JSON shape: results.channels[0].alternatives[0].transcript
#         text = dg_json.get("results", {}) \
#                       .get("channels", [{}])[0] \
#                       .get("alternatives", [{}])[0] \
#                       .get("transcript", "") \
#                       .strip()

#         text = clean_repeated_words(text)
#         text = normalize_contact_info(text)

#     except Exception as e:
#         print("⚠ Deepgram STT Error:", e)
#         return "", ""

#     if not text:
#         return "", ""

#     if not is_meaningful_text(text):
#         print(f"🪶 Ignored meaningless chunk: '{text}'")
#         return "", ""

#     # ---- Log + context ----
#     append_log("Caller", text)
#     context.append({"role": "user", "content": text})
#     short_context = context[-50:]

#     # ---- GPT reply (unchanged) ----
#     try:
#         comp = client.chat.completions.create(
#             model="gpt-4o-mini",
#             temperature=0.7,
#             messages=[
#                 {
#                     "role": "system",
#                     "content": (
#                         "You are Mia, a polite and professional restaurant receptionist for 'The Restaurant'. "
#                         "You handle calls for reservations, timings, and menu questions. "
#                         "Keep track of what the caller already said and never ask the same question again. "
#                         "And also be sure to only provide information that is in the restaurant info provided. "
#                         "Be warm, concise, and conversational. Use short natural English sentences. "
#                         "If the caller gives reservation details, confirm clearly, then ask for their name, email and phone "
#                         "If they provide contact info, repeat it back to confirm accuracy. If they said its correct or right or anything that means yes, proceed. "
#                         "If unclear. Ask them to spell each slowly and confirm what you understood. "
#                         "Unclear even after spelling out, ask only for that portion to be repeated. Once both are clear, confirm everything, "
#                         "then say: 'Thank you! Your reservation is confirmed. We look forward to seeing you.' "
#                         f"Here is the restaurant information:\n{RESTAURANT_INFO}"
#                     ),
#                 },
#                 *short_context,
#             ],
#         )

#         ai_text = comp.choices[0].message.content.strip()
#         append_log("AI", ai_text)
#         context.append({"role": "assistant", "content": ai_text})
#         return text, ai_text

#     except Exception as e:
#         print("⚠ GPT Error:", e)
#         return text, ""

# # ===== DASHBOARD UPDATE =====
# async def update_dashboard(caller, ai):
#     try:
#         async with aiohttp.ClientSession() as s:
#             await s.post(FLASK_SOCKET_URL, json={"caller": caller, "suggestion": ai})
#     except Exception as e:
#         print("⚠ Dashboard update failed:", e)

# # ===== OPENAI TTS =====
# async def play_tts(ai_text):
#     if not ai_text or not CURRENT_CALL_SID:
#         return
#     filename = f"tts_{int(time.time()*1000)}.mp3"
#     path = os.path.join("static", "tts", filename)
#     os.makedirs(os.path.dirname(path), exist_ok=True)
#     try:
#         speech = client.audio.speech.create(
#             model="gpt-4o-mini-tts",
#             voice="nova",
#             input=ai_text,
#         )
#         with open(path, "wb") as f:
#             f.write(speech.read())
#         twilio_client.calls(CURRENT_CALL_SID).update(
#             url=f"{PUBLIC_BASE_URL}/play_tts?file={filename}",
#             method="POST",
#         )
#         print(f"🔊 Played {filename}")
#     except Exception as e:
#         print("⚠ TTS playback error:", e)

# # ===== STREAM HANDLING =====
# audio_buffer = b""
# last_audio_time = 0
# last_processing = None

# async def handle_media_chunk(mulaw_bytes: bytes):
#     global audio_buffer, last_audio_time, last_processing
#     now = time.time()
#     audio_buffer += mulaw_bytes
#     long_enough = len(audio_buffer) >= (SAMPLE_RATE * 4 * BYTES_PER_SAMPLE)
#     silence_gap = now - last_audio_time > 0.25
#     if long_enough or silence_gap:
#         chunk = audio_buffer
#         audio_buffer = b""
#         if last_processing and not last_processing.done():
#             last_processing.cancel()
#         last_processing = asyncio.create_task(process_audio(chunk))
#     last_audio_time = now

# async def process_audio(data: bytes):
#     pcm = mulaw_to_pcm16_16k(data)
#     wav = await asyncio.get_running_loop().run_in_executor(POOL, pcm16k_to_wav, pcm)
#     caller, ai = await asyncio.get_running_loop().run_in_executor(POOL, transcribe_and_reply, wav)
#     if caller or ai:
#         await update_dashboard(caller, ai)
#         if ai:
#             asyncio.create_task(play_tts(ai))

# # ===================================================================
# #  RECORDING DOWNLOAD + MERGE (unchanged)
# # ===================================================================

# def download_twilio_recording(call_sid):
#     try:
#         os.makedirs("static/recordings", exist_ok=True)

#         recordings = twilio_client.recordings.list(call_sid=call_sid)
#         if not recordings:
#             print("⚠ No recordings found for this call.")
#             return None

#         rec = recordings[0]
#         mp3_url = f"https://api.twilio.com{rec.uri.replace('.json', '.mp3')}"
#         save_path = f"static/recordings/{rec.sid}.mp3"

#         r = requests.get(mp3_url, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN))
#         with open(save_path, "wb") as f:
#             f.write(r.content)

#         print(f"📥 Downloaded Twilio raw recording → {save_path}")
#         return save_path
#     except Exception as e:
#         print("⚠ Error downloading recording:", e)
#         return None

# def merge_recordings(greeting_path, twilio_path, output_path):
#     try:
#         greeting = AudioSegment.from_mp3(greeting_path)
#         call_audio = AudioSegment.from_mp3(twilio_path)

#         final = greeting + call_audio
#         final.export(output_path, format="mp3")

#         print(f"🎧 Final merged recording saved: {output_path}")
#         return output_path
#     except Exception as e:
#         print("⚠ Merge error:", e)
#         return None

# # ===== REPORT GENERATION =====
# def build_quality_report_sync(conversation_text: str) -> str:
#     if not conversation_text.strip():
#         return "No conversation content available."
#     prompt = (
#         "You are a senior QA evaluator analyzing a restaurant receptionist call between a customer and the AI. "
#         "Provide a clear, structured, business-grade report with the following sections:\n\n"
#         "1. Overall Score (out of 100)\n"
#         "2. Communication Metrics:\n"
#         "   - Greeting & Politeness (out of 10)\n"
#         "   - Active Listening (out of 10)\n"
#         "   - Clarity & Conciseness (out of 10)\n"
#         "   - Empathy & Tone (out of 10)\n"
#         "   - Accuracy of Information (out of 10)\n"
#         "3. Summary (2–3 sentences on how the receptionist performed overall)\n"
#         "4. Detailed Analysis (3–5 sentences explaining major highlights and issues)\n"
#         "5. Strengths (3 short bullet points)\n"
#         "6. Areas for Improvement (3 short bullet points)\n"
#         "7. AI Recommendations (specific actions to improve future interactions)\n\n"
#         "Avoid markdown, tables, or asterisks — just plain clean text."
#     )
#     try:
#         resp = client.chat.completions.create(
#             model="gpt-4o-mini",
#             messages=[
#                 {"role": "system", "content": "You are an expert QA reviewer."},
#                 {"role": "user", "content": f"{prompt}\n\n---\n{conversation_text}\n---"},
#             ],
#         )
#         return re.sub(r"\\(.?)\\*", r"\1", resp.choices[0].message.content.strip())
#     except Exception as e:
#         print("⚠ Report generation error:", e)
#         return "Report generation failed."

# async def make_report():
#     text = read_log()
#     report = await asyncio.get_running_loop().run_in_executor(POOL, build_quality_report_sync, text)
#     try:
#         async with aiohttp.ClientSession() as s:
#             await s.post(FLASK_REPORT_URL, json={"report": report})
#         print("📊 Report sent to dashboard")
#     except Exception as e:
#         print("⚠ Report post failed:", e)

# # ===== Warm up models (Deepgram + GPT + TTS) =====
# async def warm_up_models():
#     print("🔥 Warming up Deepgram, GPT, and TTS...")

#     # Deepgram warmup with 1s of silence
#     try:
#         if DEEPGRAM_API_KEY:
#             silent_pcm = b"\x00" * 32000  # 1 sec @ 16k
#             wav = pcm16k_to_wav(silent_pcm)
#             headers = {
#                 "Authorization": f"Token {DEEPGRAM_API_KEY}",
#                 "Content-Type": "audio/wav",
#             }
#             params = {
#                 "model": "nova-3",
#                 "language": "en-US",
#             }
#             requests.post(
#                 "https://api.deepgram.com/v1/listen",
#                 headers=headers,
#                 params=params,
#                 data=wav,
#                 timeout=10,
#             )
#         else:
#             print("⚠ Deepgram warmup skipped: DEEPGRAM_API_KEY not set.")
#     except Exception as e:
#         print("Deepgram warmup skipped:", e)

#     # GPT warmup
#     try:
#         client.chat.completions.create(
#             model="gpt-4o-mini",
#             messages=[{"role": "user", "content": "warmup"}]
#         )
#     except Exception as e:
#         print("GPT warmup skipped:", e)

#     # TTS warmup
#     try:
#         speech = client.audio.speech.create(
#             model="gpt-4o-mini-tts",
#             voice="nova",
#             input="warming up"
#         )
#         speech.read()
#     except Exception as e:
#         print("TTS warmup skipped:", e)

#     print("🔥 Warmup complete.")

# # ===== TWILIO STREAM =====
# async def handle_twilio(ws):
#     global CURRENT_CALL_SID
#     print("🔗 Twilio connected.")
#     reset_log()
#     buf = b""
#     try:
#         async for msg in ws:
#             data = json.loads(msg)
#             evt = data.get("event")

#             if evt == "start":
#                 CURRENT_CALL_SID = data["start"]["callSid"]
#                 print(f"📞 Call started: {CURRENT_CALL_SID}")
#                 # cleanup_tts()
#                 # cleanup_recordings()
                
#                 greeting_text = (
#                     "Hello! This is Mia from The Restaurant. "
#                     "How can I assist you today? Would you like to make a reservation or ask about our menu?"
#                 )
#                 append_log("AI", greeting_text)
#                 context.append({"role": "assistant", "content": greeting_text})
#                 asyncio.create_task(update_dashboard("", greeting_text))

#                 # Start Twilio recording via REST API
#                 try:
#                     twilio_client.calls(CURRENT_CALL_SID).recordings.create()
#                     print("🎙 Recording started via REST API.")
#                 except Exception as e:
#                     print("⚠ Error starting recording:", e)

#                 # asyncio.create_task(warm_up_models())

#             elif evt == "media":
#                 b64 = data["media"].get("payload", "")
#                 if b64:
#                     buf += base64.b64decode(b64)
#                     await handle_media_chunk(buf)
#                     buf = b""

#             elif evt == "stop":
#                 print("🛑 Call ended.")

#                 if buf:
#                     await process_audio(buf)

#                 await make_report()

#                 # Download Twilio recording
#                 raw_recording = download_twilio_recording(CURRENT_CALL_SID)

#                 # Merge with greeting.mp3
#                 if raw_recording:
#                     greeting_path = "static/tts/greeting.mp3"
#                     final_path = f"static/recordings/final_{CURRENT_CALL_SID}.mp3"
#                     merge_recordings(greeting_path, raw_recording, final_path)

#                 CURRENT_CALL_SID = None
#                 break

#             else:
#                 print(f"ℹ Event: {evt}")

#     except Exception as e:
#         print("⚠ WebSocket error:", e)

# # ===== MAIN =====
# async def main():
#     print(f"🧩 Restaurant Receptionist server running at ws://0.0.0.0:{PORT}/stream")
    
#     cleanup_tts()
#     cleanup_recordings()
    
#     await warm_up_models()

#     async with websockets.serve(handle_twilio, "0.0.0.0", PORT, ping_interval=20, ping_timeout=20):
#         await asyncio.Future()

# if __name__ == "__main__":
#     try:
#         asyncio.run(main())
#     except (KeyboardInterrupt, asyncio.CancelledError):
#         print("🛑 Server stopped gracefully.")





import os
import json
import asyncio
import websockets
import aiohttp
import time
import re
import requests
import audioop
import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from dotenv import load_dotenv
from openai import OpenAI
from twilio.rest import Client as TwilioClient

# ===== Load Environment =====
load_dotenv()

# ===== ENVIRONMENT VARIABLES =====
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PORT = int(os.getenv("STREAM_PORT", 8000))
FLASK_SOCKET_URL = os.getenv("FLASK_SOCKET_URL")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL")
FLASK_REPORT_URL = f"{PUBLIC_BASE_URL}/report"

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

# ===== CLIENTS =====
client = OpenAI(api_key=OPENAI_API_KEY)

twilio_client = None
if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
    twilio_client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# ===== SETTINGS =====
POOL = ThreadPoolExecutor(max_workers=4)
LOG_FILE = "conversation_log.txt"

# ===== RESTAURANT CONTEXT (same as your old prompt) =====
RESTAURANT_INFO = """
Restaurant Name: The Restaurant
Cuisine: Italian & Continental
Timings: 10:00 AM – 10:00 PM
Location: 123 Main Street, Austin, TX
Contact: +1 (507) 554-1673
Menu Highlights:
  - Starters: Garlic Bread, Caesar Salad, Bruschetta
  - Main Course: Alfredo Pasta, Margherita Pizza, Lasagna
  - Desserts: Tiramisu, Chocolate Mousse
  - Beverages: Coffee, Wine, Fresh Juice
Policies:
  - Accepts reservations up to 10 people.
  - Takeout and curbside pickup available.
  - No home delivery.
"""

SYSTEM_INSTRUCTIONS = (
    "You are Mia, a polite and professional restaurant receptionist for 'The Restaurant'. "
    "You handle calls for reservations, timings, and menu questions. "
    "Keep track of what the caller already said and never ask the same question again. "
    "And also be sure to only provide information that is in the restaurant info provided. "
    "Be warm, concise, and conversational. Use short natural English sentences. "
    "If the caller gives reservation details, confirm clearly, then ask for their name, email and phone "
    "If they provide contact info, repeat it back to confirm accuracy. If they said its correct or right or anything that means yes, proceed. "
    "If unclear. Ask them to spell each slowly and confirm what you understood. "
    "Still unclear, ask only for that portion to be repeated. Once both are clear, confirm everything, "
    "then say: 'Thank you! Your reservation is confirmed. We look forward to seeing you.' "
    f"Here is the restaurant information:\n{RESTAURANT_INFO}"
)


# ===== RECORDING DOWNLOAD =====
def download_call_recording(call_sid):
    if not twilio_client:
        print("⚠ Twilio client not configured.")
        return None
    try:
        recordings = twilio_client.recordings.list(call_sid=call_sid)
        if not recordings:
            print("⚠ No Twilio recordings found.")
            return None

        rec = recordings[0]
        url = f"https://api.twilio.com{rec.uri.replace('.json', '.mp3')}"
        os.makedirs("static/recordings", exist_ok=True)
        save_path = f"static/recordings/{rec.sid}.mp3"

        r = requests.get(url, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN))
        with open(save_path, "wb") as f:
            f.write(r.content)

        print(f"🎧 Saved call recording → {save_path}")
        return save_path

    except Exception as e:
        print("⚠ Recording download error:", e)
        return None



# ===== LOGGING UTILITIES =====
def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def reset_log() -> None:
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"[{_ts()}] --- Call Started ---\n")


def append_log(role: str, text: str) -> None:
    if not text:
        return
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{_ts()}] [{role}] {text}\n")


def read_log() -> str:
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""


# ===== DASHBOARD UPDATE =====
async def update_dashboard(caller_text: str, ai_text: str) -> None:
    if not FLASK_SOCKET_URL:
        return
    try:
        async with aiohttp.ClientSession() as s:
            await s.post(
                FLASK_SOCKET_URL,
                json={"caller": caller_text, "suggestion": ai_text},
                timeout=5,
            )
    except Exception as e:
        print("⚠ Dashboard update failed:", e)


# ===== QA REPORT GENERATION (same structure as before) =====
def build_quality_report_sync(conversation_text: str) -> str:
    if not conversation_text.strip():
        return "No conversation content available."

    prompt = (
        "You are a senior QA evaluator analyzing a restaurant receptionist call between a customer and the AI. "
        "Provide a clear, structured, business-grade report with the following sections:\n\n"
        "1. Overall Score (out of 100)\n"
        "2. Communication Metrics:\n"
        "   - Greeting & Politeness (out of 10)\n"
        "   - Active Listening (out of 10)\n"
        "   - Clarity & Conciseness (out of 10)\n"
        "   - Empathy & Tone (out of 10)\n"
        "   - Accuracy of Information (out of 10)\n"
        "3. Summary (2–3 sentences on how the receptionist performed overall)\n"
        "4. Detailed Analysis (3–5 sentences explaining major highlights and issues)\n"
        "5. Strengths (3 short bullet points)\n"
        "6. Areas for Improvement (3 short bullet points)\n"
        "7. AI Recommendations (specific actions to improve future interactions)\n\n"
        "Avoid markdown, tables, or asterisks — just plain clean text."
    )

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert QA reviewer."},
                {"role": "user", "content": f"{prompt}\n\n---\n{conversation_text}\n---"},
            ],
        )
        text = resp.choices[0].message.content.strip()
        # remove stray markdown bullet syntax if any
        return re.sub(r"\\(.?)\\*", r"\1", text)
    except Exception as e:
        print("⚠ Report generation error:", e)
        return "Report generation failed."


async def make_report() -> None:
    text = read_log()
    loop = asyncio.get_running_loop()
    report = await loop.run_in_executor(POOL, build_quality_report_sync, text)
    if not FLASK_REPORT_URL:
        print("📊 QA Report (no FLASK_REPORT_URL configured):\n", report)
        return
    try:
        async with aiohttp.ClientSession() as s:
            await s.post(FLASK_REPORT_URL, json={"report": report}, timeout=10)
        print("📊 Report sent to dashboard")
    except Exception as e:
        print("⚠ Report post failed:", e)


# ===== OPENAI REALTIME CONNECTION =====
async def connect_openai_realtime():
    """
    Connect to OpenAI Realtime API and configure the session
    for G.711 ulaw audio in/out + transcription + Mia instructions.
    """
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set")

    url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview"

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "OpenAI-Beta": "realtime=v1",
    }

    ws = await websockets.connect(url, extra_headers=headers, max_size=None)
    print("✅ Connected to OpenAI Realtime")

    # --- Session configuration ---
    session_update = {
        "type": "session.update",
        "session": {
            "modalities": ["audio", "text"],
            "instructions": SYSTEM_INSTRUCTIONS,

            # Twilio sends and expects G.711 u-law (8k)
            "input_audio_format": "g711_ulaw",
            "output_audio_format": "g711_ulaw",

            # Use the realtime transcription model
            "input_audio_transcription": {
                "model": "gpt-4o-mini-transcribe"
            },
            

            "turn_detection": {
                "type": "server_vad",
                "silence_duration_ms": 300,
            },
        },
    }
    await ws.send(json.dumps(session_update))
    print("✅ Sent session.update to OpenAI")

    # --- Trigger initial greeting via the model itself ---
    greeting_instructions = {
        "type": "response.create",
        "response": {
            "instructions": (
                "Start the call by greeting the caller with: "
                "\"Hello! This is Mia from The Restaurant. How can I assist you today? "
                "Would you like to make a reservation or ask about our menu?\" "
                "Then continue the conversation following your usual instructions."
            )
        },
    }
    await ws.send(json.dumps(greeting_instructions))
    print("✅ Requested initial greeting from OpenAI")

    return ws


# ===== BRIDGE: Twilio -> OpenAI =====
async def twilio_to_openai(twilio_ws, openai_ws, shared_state):
    """
    Receive audio/media events from Twilio Media Streams,
    forward audio to OpenAI Realtime as input_audio_buffer.append events,
    and manage call start/stop & recording.
    """
    reset_log()
    print("🔗 Twilio connected.")

    try:
        async for message in twilio_ws:
            data = json.loads(message)
            evt = data.get("event")

            if evt == "start":
                start_info = data.get("start", {})
                call_sid = start_info.get("callSid")
                stream_sid = start_info.get("streamSid")

                shared_state["call_sid"] = call_sid
                shared_state["stream_sid"] = stream_sid

                print(f"📞 Call started: {call_sid}")
                print(f"🛰 Stream SID: {stream_sid}")
                append_log("SYSTEM", f"Call started: {call_sid}")

                # Start Twilio call recording
                if twilio_client and call_sid:
                    try:
                        twilio_client.calls(call_sid).recordings.create(recording_channels="dual")
                        print("🎙 Recording started via REST API.")
                    except Exception as e:
                        print("⚠ Error starting recording:", e)

            elif evt == "media":
                payload_b64 = data.get("media", {}).get("payload")
                if not payload_b64:
                    continue

                # --- STEP 1: decode base64 to raw μ-law bytes ---
                try:
                    raw_ulaw = base64.b64decode(payload_b64)
                except Exception as e:
                    print("⚠ base64 decode failed:", e)
                    continue

                # --- STEP 2: μ-law → PCM16 (linear) ---
                try:
                    pcm = audioop.ulaw2lin(raw_ulaw, 2)   # 16-bit PCM
                except Exception as e:
                    print("⚠ ulaw2lin failed:", e)
                    pcm = raw_ulaw

                # --- STEP 3: BOOST (2.0 = +6dB) ---
                try:
                    boosted_pcm = audioop.mul(pcm, 2, 2.0)    # second argument = width(2 bytes)
                except Exception as e:
                    print("⚠ boost failed:", e)
                    boosted_pcm = pcm

                # --- STEP 4: PCM16 → μ-law ---
                try:
                    boosted_ulaw = audioop.lin2ulaw(boosted_pcm, 2)
                except Exception as e:
                    print("⚠ lin2ulaw failed:", e)
                    boosted_ulaw = raw_ulaw

                # --- STEP 5: encode to base64 again ---
                boosted_b64 = base64.b64encode(boosted_ulaw).decode("utf-8")

                # --- STEP 6: SEND TO OPENAI ---
                event_to_openai = {
                    "type": "input_audio_buffer.append",
                    "audio": boosted_b64,
                }

                try:
                    await openai_ws.send(json.dumps(event_to_openai))
                except Exception as e:
                    print("⚠ Error sending boosted audio to OpenAI:", e)
                    break


            elif evt == "stop":
                print("🛑 Twilio sent stop event.")
                append_log("SYSTEM", "Twilio stop event received.")
                shared_state["stopped"] = True

                # Tell OpenAI we're done with input audio
                
                await asyncio.sleep(0.25)
                try:
                    await openai_ws.send(json.dumps({"type": "input_audio_buffer.commit"}))
                except Exception as e:
                    print("⚠ Error committing audio buffer:", e)
                break

            else:
                # e.g. "connected" etc.
                print(f"ℹ Twilio event: {evt}")

    except Exception as e:
        print("⚠ Twilio WS error:", e)
    finally:
        shared_state["stopped"] = True
        print("🔚 twilio_to_openai finished.")


# ===== BRIDGE: OpenAI -> Twilio =====
async def openai_to_twilio(openai_ws, twilio_ws, shared_state):
    """
    Receive events from OpenAI Realtime and:
      - stream G.711 ulaw audio back to Twilio,
      - capture caller transcripts,
      - capture AI transcripts,
      - push updates to dashboard and log for QA.
    """
    try:
        async for raw in openai_ws:
            try:
                evt = json.loads(raw)
            except Exception as parse_err:
                print("⚠ Failed to parse OpenAI event:", parse_err, raw)
                continue

            etype = evt.get("type")

            # Audio from AI to caller (u-law 8k as base64)
            if etype == "response.audio.delta":
                stream_sid = shared_state.get("stream_sid")
                if not stream_sid:
                    continue

                delta_b64 = evt.get("delta")
                if not delta_b64:
                    continue

                twilio_media = {
                    "event": "media",
                    "streamSid": stream_sid,
                    "media": {"payload": delta_b64},
                }
                try:
                    await twilio_ws.send(json.dumps(twilio_media))
                    await asyncio.sleep(0.0125)
                except Exception as e:
                    print("⚠ Error sending audio back to Twilio:", e)
                    break

            # Final transcript of AI's spoken output (greeting + replies)
            elif etype == "response.audio_transcript.done":
                ai_text = evt.get("transcript", "").strip()
                if ai_text:
                    print("🤖 AI:", ai_text)
                    append_log("AI", ai_text)
                    await update_dashboard("", ai_text)

            # Caller transcript from input audio
            elif etype == "conversation.item.input_audio_transcription.completed":
                caller_text = evt.get("transcript", "").strip()
                if caller_text:
                    print("👤 Caller:", caller_text)
                    append_log("Caller", caller_text)
                    await update_dashboard(caller_text, "")

            # Optional streaming text deltas (not used for dashboard right now)
            elif etype == "response.audio_transcript.delta":
                # Could be used later if you want live partial captions
                pass

            elif etype == "error":
                print("⚠ OpenAI Realtime error:", evt)

            # Exit once Twilio has stopped
            if shared_state.get("stopped"):
                break

    except Exception as e:
        print("⚠ OpenAI WS loop error:", e)
    finally:
        print("🔚 openai_to_twilio finished.")




# ===== MAIN HANDLER PER CALL =====
async def handle_twilio(ws):
    """
    For each incoming Twilio media stream:
      1) Create OpenAI Realtime connection.
      2) Run Twilio->OpenAI and OpenAI->Twilio bridges in parallel.
      3) When done, generate QA report from conversation_log.txt.
    """
    shared_state = {
        "call_sid": None,
        "stream_sid": None,
        "stopped": False,
    }

    openai_ws = await connect_openai_realtime()

    try:
        await asyncio.gather(
            twilio_to_openai(ws, openai_ws, shared_state),
            openai_to_twilio(openai_ws, ws, shared_state),
        )
    finally:
        try:
            await openai_ws.close()
        except Exception:
            pass

        # Build and push QA report
        await make_report()

        print("✅ Call handling complete.")


# ===== SERVER ENTRYPOINT =====
async def main():
    print(f"🧩 Realtime stream server running at ws://0.0.0.0:{PORT}/stream")
    async with websockets.serve(
        handle_twilio,
        "0.0.0.0",
        PORT,
        ping_interval=20,
        ping_timeout=20,
        max_size=None,
    ):
        await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("🛑 Server stopped.")
