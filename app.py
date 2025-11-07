import os
from flask import Flask, request, Response, render_template, jsonify
from flask_socketio import SocketIO
from twilio.twiml.voice_response import VoiceResponse
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VoiceGrant
from dotenv import load_dotenv

# ===== Load Environment =====
load_dotenv()

app = Flask(__name__, static_folder="static", template_folder="templates")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# ===== Environment Variables =====
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_API_KEY = os.getenv("TWILIO_API_KEY")
TWILIO_API_SECRET = os.getenv("TWILIO_API_SECRET")
TWIML_APP_SID = os.getenv("TWIML_APP_SID")
TWILIO_NUMBER = os.getenv("TWILIO_NUMBER")

STREAM_SERVER_URL = os.getenv("STREAM_SERVER_URL")
BROWSER_IDENTITY = os.getenv("BROWSER_IDENTITY", "agent")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL")
STATUS_CALLBACK_URL = os.getenv("STATUS_CALLBACK_URL", f"{PUBLIC_BASE_URL}/status")

# Make sure tts folder exists for generated AI voice responses
os.makedirs(os.path.join(app.static_folder, "tts"), exist_ok=True)

# ===== Routes =====

@app.route("/")
def index():
    return render_template("dashboard.html")

# ---- Incoming call (AI answers directly) ----
@app.route("/voice", methods=["POST"])
def voice():
    from_number = request.form.get("From")
    call_sid = request.form.get("CallSid")

    socketio.emit("call_incoming", {"from": from_number, "callSid": call_sid})

    vr = VoiceResponse()

    # Stream caller audio to your AI stream server
    start = vr.start()
    start.stream(url=STREAM_SERVER_URL, track="inbound_track")

    # AI greets caller automatically
    # vr.say("Hello, this is the AI assistant. How can I help you today?")
    vr.redirect("/hold")

    return Response(str(vr), mimetype="text/xml")

@app.route("/hold", methods=["GET", "POST"])
def hold():
    vr = VoiceResponse()
    vr.pause(length=600)
    return Response(str(vr), mimetype="text/xml")

# ---- Play AI response via Twilio ----
@app.route("/play_tts", methods=["GET", "POST"])
def play_tts():
    filename = request.args.get("file")
    vr = VoiceResponse()
    if filename:
        vr.play(f"{PUBLIC_BASE_URL}/static/tts/{filename}")
    vr.redirect("/hold")
    return Response(str(vr), mimetype="text/xml")

# ---- Token for browser client (still works for dashboard) ----
@app.route("/token")
def token():
    identity = request.args.get("identity", BROWSER_IDENTITY)
    token = AccessToken(TWILIO_ACCOUNT_SID, TWILIO_API_KEY, TWILIO_API_SECRET, identity=identity)
    grant = VoiceGrant(outgoing_application_sid=TWIML_APP_SID, incoming_allow=True)
    token.add_grant(grant)
    raw = token.to_jwt()
    jwt_token = raw.decode("utf-8") if hasattr(raw, "decode") else raw
    return jsonify({"identity": identity, "token": jwt_token})

# ---- Live AI updates ----
@app.route("/update", methods=["POST"])
def update_route():
    data = request.json
    socketio.emit("update", data)
    return jsonify({"status": "ok"})

# ---- Final report ----
@app.route("/report", methods=["POST"])
def report_route():
    report = (request.json or {}).get("report", "")
    socketio.emit("call_report", {"report": report})
    return jsonify({"status": "received"})

# ---- Twilio status callback ----
@app.route("/status", methods=["POST"])
def status_callback():
    call_status = request.form.get("CallStatus")
    call_sid = request.form.get("CallSid")
    print(f"[STATUS CALLBACK] {call_sid} → {call_status}")

    if call_status in ["completed", "failed", "canceled", "busy", "no-answer"]:
        socketio.emit("call_ended", {"status": call_status})
        print("🔔 Emitted call_ended to dashboard")

    return Response("OK", 200)

if __name__ == "__main__":
    print("🚀 Flask + SocketIO running on port 5000")
    socketio.run(app, host="0.0.0.0", port=5000)
