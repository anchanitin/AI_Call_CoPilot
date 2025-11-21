import os
from flask import Flask, request, Response, render_template, jsonify
from flask_socketio import SocketIO
from twilio.twiml.voice_response import VoiceResponse, Connect
from dotenv import load_dotenv

# ===== Load Environment =====
load_dotenv()

app = Flask(__name__, static_folder="static", template_folder="templates")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# ===== Environment Variables =====
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_NUMBER = os.getenv("TWILIO_NUMBER")
STREAM_SERVER_URL = os.getenv("STREAM_SERVER_URL")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL")
STATUS_CALLBACK_URL = os.getenv("STATUS_CALLBACK_URL", f"{PUBLIC_BASE_URL}/status")

# ===== Routes =====
@app.route("/")
def index():
    return render_template("dashboard.html")

# ---- Status callback from Twilio ----
@app.route("/status", methods=["POST"])
def status():
    from_number = request.form.get("From")
    call_status = request.form.get("CallStatus")
    call_sid = request.form.get("CallSid")

    socketio.emit(
        "call_status",
        {
            "from": from_number,
            "status": call_status,
            "callSid": call_sid,
        },
    )
    
    if call_status == "completed":
        socketio.emit("call_ended")
        
    return Response("OK", 200)


# ---- Voice webhook: Twilio <Connect><Stream> to realtime server ----
@app.route("/voice", methods=["POST"])
def voice():
    from_number = request.form.get("From")
    call_sid = request.form.get("CallSid")

    
    socketio.emit("call_incoming", {"from": from_number, "callSid": call_sid})

    vr = VoiceResponse()

    connect = Connect()
    connect.stream(url=STREAM_SERVER_URL, track="inbound_track")
    vr.append(connect)

    # <Connect> takes over the call; no further TwiML is processed.
    return Response(str(vr), mimetype="text/xml")

# ---- Socket.IO endpoints for dashboard updates ----
@app.route("/update", methods=["POST"])
def update():
    data = request.get_json(force=True)
    caller = data.get("caller", "")
    suggestion = data.get("suggestion", "")

    socketio.emit("update", {"caller": caller, "suggestion": suggestion})
    return Response("OK", 200)


@app.route("/report", methods=["POST"])
def report():
    data = request.get_json(force=True)
    report_text = data.get("report", "")

    socketio.emit("call_report", {"report": report_text})
    return Response("OK", 200)


if __name__ == "__main__":
    print("🚀 Flask + SocketIO running on port 5000")
    socketio.run(app, host="0.0.0.0", port=5000)