import os
import json
import asyncio
import websockets
import aiohttp
import time
import audioop
import base64
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from prompts import SYSTEM_INSTRUCTIONS, QA_PROMPT, EMAIL_TEMPLATE

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


# ===== TRANSFER CALL TO HUMAN AGENT =====
async def transfer_call_to_agent(shared_state):
    call_sid = shared_state.get("call_sid")
    if not call_sid or not twilio_client:
        print("⚠ Cannot transfer — missing call SID or Twilio client")
        return

    try:
        twilio_client.calls(call_sid).update(
            url=f"{PUBLIC_BASE_URL}/transfer_to_agent_twiml"
        )
        print("📞 Call transferred to live agent.")
    except Exception as e:
        print("⚠ Transfer failed:", e)


# ===== QA REPORT GENERATION =====
def build_quality_report_sync(conversation_text: str) -> str:
    convo = conversation_text.strip()
    if not convo:
        return (
            "Summary: Caller disconnected immediately before any conversation could begin.\n"
            "Detailed Analysis: No interaction occurred, so call quality cannot be evaluated.\n"
            "Strengths: None (no conversation).\n"
            "Areas for Improvement: Not enough data to analyze.\n"
            "AI Recommendations: None for this call."
        )

    lines = [ln for ln in convo.splitlines() if ln.strip()]
    caller_lines = [ln for ln in lines if "[Caller]" in ln]
    ai_lines = [ln for ln in lines if "[AI]" in ln]

    if len(caller_lines) == 0:
        return (
            "Summary: The caller disconnected before providing any information or engaging in a conversation.\n"
            "Detailed Analysis: The AI did not have a chance to interact with the caller, "
            "so this call cannot be evaluated for quality.\n"
            "Strengths: None identified (no conversation).\n"
            "Areas for Improvement: Not enough data to identify specific improvement points.\n"
            "AI Recommendations: None for this call."
        )

    if (len(caller_lines) + len(ai_lines) < 4):
        return (
            "Summary: The conversation was too brief to generate a meaningful quality evaluation. "
            "The caller may have disconnected early or shared only minimal information.\n"
            "Detailed Analysis: With only a few short utterances, it is not possible to reliably assess greeting, "
            "active listening, empathy, or technical accuracy. Any numeric scores would be misleading.\n"
            "Strengths: The system successfully answered the call and attempted to respond, "
            "but the dialogue length was insufficient for evaluation.\n"
            "Areas for Improvement: Encourage longer engagement to collect enough context for QA analysis.\n"
            "AI Recommendations: No specific behavior changes are recommended based on this call alone."
        )

    prompt = f"{QA_PROMPT}\n\nConversation Log:\n{convo}"

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert HVAC call QA reviewer. You never hallucinate and only use evidence in the transcript.",
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


# ===== EXTRACT HVAC DETAILS FROM TRANSCRIPT =====
async def extract_hvac_details():
    convo = read_log()

    prompt = (
        "Extract the following fields from this HVAC customer call:\n"
        "- name\n"
        "- email\n"
        "- phone\n"
        "- address\n"
        "- issue_description\n"
        "- service_type (one of: emergency, no_heat, no_cool, standard)\n"
        "- appointment_date\n"
        "- appointment_time\n"
        "- urgency_level (low, medium, high)\n\n"
        "Rules:\n"
        "1. Always return ONLY a JSON object.\n"
        "2. Do NOT wrap JSON in code fences.\n"
        "3. Do NOT include any explanation.\n"
        "4. If uncertain, set the field to null.\n"
        "5. once the details are collected the ai will spell them out for the caller if the caller confirms all are correct or any thing to confirm take those values adn if something is changes by the caller take the most recently updated values.\n"
        "6. Do not consider any special characters like dash, underscore, or spaces unless the caller mentions them.\n"
        f"Conversation Log:\n{convo}"
    )

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )

    raw_output = resp.choices[0].message.content.strip()
    print("🔍 GPT RAW OUTPUT:", raw_output)

    cleaned = raw_output.replace("```json", "").replace("```", "").strip()
    print("🔧 CLEANED OUTPUT:", cleaned)

    try:
        data = json.loads(cleaned)
        print("✅ Parsed HVAC JSON:", data)
        return data
    except Exception as e:
        print("⚠ JSON parsing failed:", e)
        print("⚠ Falling back to basic regex extraction.")

        
        fallback = {
            "name": None,
            "email": None,
            "phone": None,
            "address": None,
            "issue_description": None,
            "service_type": None,
            "appointment_date": None,
            "appointment_time": None,
            "urgency_level": None,
        }

        email_match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", convo)
        fallback["email"] = email_match.group(0) if email_match else None

        phone_match = re.search(r"\b\d{3}[- ]?\d{3}[- ]?\d{4}\b", convo)
        fallback["phone"] = phone_match.group(0) if phone_match else None

        name_match = re.search(r"(my name is|name is)\s+([A-Za-z ]+)", convo, re.IGNORECASE)
        fallback["name"] = name_match.group(2).strip() if name_match else None

        # Very simple address heuristic
        addr_match = re.search(
            r"\d{2,5}\s+[A-Za-z0-9\s]+(Street|St|Avenue|Ave|Road|Rd|Lane|Ln|Drive|Dr)",
            convo,
        )
        fallback["address"] = addr_match.group(0) if addr_match else None

        caller_lines = [ln for ln in convo.splitlines() if "[Caller]" in ln]
        if caller_lines:
            fallback["issue_description"] = " ".join(
                ln.split("] ", 1)[-1] for ln in caller_lines
            )

        # rough service_type classification
        lower = convo.lower()
        if any(k in lower for k in ["gas smell", "burning", "smoke", "fire", "carbon monoxide"]):
            fallback["service_type"] = "emergency"
        elif any(k in lower for k in ["no heat", "furnace not working", "heater blowing cold"]):
            fallback["service_type"] = "no_heat"
        elif any(k in lower for k in ["no cool", "not cooling", "warm air", "ac not working"]):
            fallback["service_type"] = "no_cool"
        else:
            fallback["service_type"] = "standard"

        fallback["urgency_level"] = None

        print("🔍 FALLBACK HVAC EXTRACTED:", fallback)
        return fallback


# ===== SEND HVAC EMAIL =====
async def send_hvac_email(details):
    name = details.get("name") or "Customer"
    email = details.get("email")
    phone = details.get("phone") or ""
    address = details.get("address") or "Not provided"
    issue = details.get("issue_description") or "Not provided"
    service_type = details.get("service_type") or "standard"
    date = details.get("appointment_date") or "Not scheduled"
    time_str = details.get("appointment_time") or "Not scheduled"
    urgency = details.get("urgency_level") or "normal"

    if not email:
        print("⚠ No email available to send HVAC confirmation.")
        return

    if service_type == "emergency":
        title = "🔥 Emergency HVAC Case - Technician Notified"
        message_line = (
            "We detected an urgent HVAC issue during your call. "
            "A technician has been notified or is handling your case."
        )
    elif service_type == "no_heat":
        title = "❄️ Heating Issue - Service Details"
        message_line = "Your heating issue has been recorded. We will assist you as soon as possible."
    elif service_type == "no_cool":
        title = "☀️ Cooling Issue - Service Details"
        message_line = "Your cooling issue has been recorded. We will assist you as soon as possible."
    else:
        title = "🔧 HVAC Service - Appointment / Request Details"
        message_line = "Your HVAC service request has been recorded."

    html = (
        EMAIL_TEMPLATE
        .replace("{{title}}", title)
        .replace("{{name}}", name)
        .replace("{{message_line}}", message_line)
        .replace("{{service_type}}", service_type)
        .replace("{{issue}}", issue)
        .replace("{{date}}", date)
        .replace("{{time}}", time_str)
        .replace("{{urgency}}", urgency)
        .replace("{{phone}}", phone)
        .replace("{{email}}", email)
        .replace("{{address}}", address)
    )

    msg = Mail(
        from_email="anchanitin9@gmail.com",  # your verified SendGrid sender
        to_emails=email,
        subject=title,
        html_content=html,
    )

    try:
        sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
        sg.send(msg)
        print(f"📧 HVAC email sent to {email}")
    except Exception as e:
        print("⚠ Email send failed:", e)


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

    session_update = {
        "type": "session.update",
        "session": {
            "modalities": ["audio", "text"],
            "instructions": SYSTEM_INSTRUCTIONS,
            "input_audio_format": "g711_ulaw",
            "output_audio_format": "g711_ulaw",
            "input_audio_transcription": {
                "model": "gpt-4o-mini-transcribe",
                "language": "en"
            },
            "turn_detection": {
                "type": "server_vad",
                "silence_duration_ms": 300,
            },
        },
    }
    await ws.send(json.dumps(session_update))
    print("✅ Sent session.update to OpenAI")

    greeting_instructions = {
        "type": "response.create",
        "response": {
            "instructions": (
                "Start the call with: "
                "'Hello, this is Mia from ComfortCare HVAC Solutions. "
                "Before we begin, may I have your name, phone number, email address, "
                "and service address?' "
                "Then follow your system instructions exactly."
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

                try:
                    raw_ulaw = base64.b64decode(payload_b64)
                except Exception as e:
                    print("⚠ base64 decode failed:", e)
                    continue

                try:
                    pcm = audioop.ulaw2lin(raw_ulaw, 2)
                except Exception as e:
                    print("⚠ ulaw2lin failed:", e)
                    pcm = raw_ulaw

                try:
                    boosted_pcm = audioop.mul(pcm, 2, 2.0)
                except Exception as e:
                    print("⚠ boost failed:", e)
                    boosted_pcm = pcm

                try:
                    boosted_ulaw = audioop.lin2ulaw(boosted_pcm, 2)
                except Exception as e:
                    print("⚠ lin2ulaw failed:", e)
                    boosted_ulaw = raw_ulaw

                boosted_b64 = base64.b64encode(boosted_ulaw).decode("utf-8")

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

                start_time = shared_state.get("call_start_time")
                if start_time:
                    duration = time.time() - start_time
                    shared_state["duration"] = duration
                    append_log("SYSTEM", f"Call duration: {duration:.2f} seconds")

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

            elif etype == "response.audio_transcript.done":
                ai_text = evt.get("transcript", "").strip()
                if ai_text:
                    print("🤖 AI:", ai_text)
                    append_log("AI", ai_text)
                    await update_dashboard("", ai_text)

                    # Non-emergency: AI says it will send an email → send email
                    if "you will receive an email" in ai_text.lower():
                        print("📩 Trigger: AI mentioned email → Extracting HVAC details...")
                        details = await extract_hvac_details()
                        print("📌 Extracted:", details)
                        await send_hvac_email(details)

            elif etype == "conversation.item.input_audio_transcription.completed":
                caller_text = evt.get("transcript", "").strip()
                if caller_text:
                    print("👤 Caller:", caller_text)
                    append_log("Caller", caller_text)
                    await update_dashboard(caller_text, "")

                    lower = caller_text.lower()
                    emergency_keywords = [
                        "emergency",
                        "urgent",
                        "gas smell",
                        "smell gas",
                        "burning smell",
                        "smoke",
                        "sparking",
                        "fire",
                        "carbon monoxide",
                    ]
                    if any(k in lower for k in emergency_keywords):
                        print("🚨 Emergency keywords detected → transferring to agent")

                        shared_state["stopped"] = True
                        await update_dashboard("", "Transferred to agent")

                        transfer_msg = {
                            "type": "response.create",
                            "response": {
                                "instructions": (
                                    "This sounds urgent. Please hold on while I transfer you to a live technician."
                                )
                            },
                        }
                        await openai_ws.send(json.dumps(transfer_msg))
                        await asyncio.sleep(1.5)

                        await transfer_call_to_agent(shared_state)

                        # Send emergency email even if call ended quickly
                        details = await extract_hvac_details()
                        details["service_type"] = "emergency"
                        print("📩 Sending emergency HVAC email...")
                        await send_hvac_email(details)

                        return

            elif etype == "error":
                print("⚠ OpenAI Realtime error:", evt)

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
