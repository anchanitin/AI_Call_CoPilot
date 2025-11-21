import os
import json
import asyncio
import websockets
import aiohttp
import time
import re
import audioop
import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from prompts import SYSTEM_INSTRUCTIONS, RESTAURANT_INFO, QA_PROMPT

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


# ===== QA REPORT GENERATION =====
def build_quality_report_sync(conversation_text: str) -> str:

    convo = conversation_text.strip()
    if not convo:
        # No content at all
        return (
            "Summary: Caller disconnected immediately before any conversation could begin.\n"
            "Detailed Analysis: No interaction occurred, so call quality cannot be evaluated.\n"
            "Strengths: None (no conversation).\n"
            "Areas for Improvement: Not enough data to analyze.\n"
            "AI Recommendations: None for this call."
        )

    # Separate lines and detect caller/AI lines
    lines = [ln for ln in convo.splitlines() if ln.strip()]
    caller_lines = [ln for ln in lines if "[Caller]" in ln]
    ai_lines = [ln for ln in lines if "[AI]" in ln]

    # Count words to estimate how much content we actually have
    word_count = len(re.findall(r"\w+", convo))

    # Case 1: caller never really spoke
    if len(caller_lines) == 0:
        return (
            "Summary: The caller disconnected before providing any information or engaging in a conversation.\n"
            "Detailed Analysis: The AI did not have a chance to interact with the caller in a meaningful way, "
            "so this call cannot be evaluated for quality.\n"
            "Strengths: None identified (no conversation).\n"
            "Areas for Improvement: Not enough data to identify specific improvement points.\n"
            "AI Recommendations: None for this call."
        )

    # Case 2: very short or trivial conversation → avoid fake detailed scoring
    if (len(caller_lines) + len(ai_lines) < 4) or word_count < 40:
        return (
            "Summary: The conversation was too brief to generate a meaningful quality evaluation. "
            "The caller may have disconnected early or shared only minimal information.\n"
            "Detailed Analysis: With only a few short utterances, it is not possible to reliably assess greeting, "
            "active listening, empathy, or accuracy. Any numeric scores would be misleading.\n"
            "Strengths: The system successfully answered the call and attempted to respond, "
            "but the dialogue length was insufficient for evaluation.\n"
            "Areas for Improvement: Encourage longer engagement to collect enough context for QA analysis.\n"
            "AI Recommendations: No specific behavior changes are recommended based on this call alone."
        )

    # For longer, meaningful conversations → perform full QA scoring
    prompt = f"{QA_PROMPT}\n\nConversation Log:\n{convo}"
    

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,  
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert call QA reviewer. You never hallucinate and only use evidence in the transcript.",
                },
                {"role": "user", "content": prompt},
            ],
        )
        text = resp.choices[0].message.content.strip()
        return text
    except Exception as e:
        print(" Report generation error:", e)
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
                shared_state["call_start_time"] = time.time()

                print(f"📞 Call started: {call_sid}")
                print(f"🛰 Stream SID: {stream_sid}")
                append_log("SYSTEM", f"Call started: {call_sid}")

                # Start Twilio call recording
                if twilio_client and call_sid:
                    try:
                        twilio_client.calls(call_sid).recordings.create(
                            recording_channels="dual"
                        )
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

                # Track call duration
                start_time = shared_state.get("call_start_time")
                if start_time:
                    duration = time.time() - start_time
                    shared_state["duration"] = duration
                    append_log("SYSTEM", f"Call duration: {duration:.2f} seconds")

                # Tell OpenAI we're done with input audio
                await asyncio.sleep(0.25)
                try:
                    await openai_ws.send(
                        json.dumps({"type": "input_audio_buffer.commit"})
                    )
                except Exception as e:
                    print("⚠ Error committing audio buffer:", e)
                break

            else:
                print(f"ℹ Twilio event: {evt}")

    except Exception as e:
        print("⚠ Twilio WS error:", e)
    finally:
        shared_state["stopped"] = True
        print("🔚 twilio_to_openai finished.")


# ===== BRIDGE: OpenAI -> Twilio =====
async def openai_to_twilio(openai_ws, twilio_ws, shared_state):
    
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
