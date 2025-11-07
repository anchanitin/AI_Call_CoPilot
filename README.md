AI CALL COPILOT
───────────────────────────────────────────────

AI Call CoPilot is a voice-call assistant that integrates Twilio Voice, Flask, and OpenAI to handle and assist with live phone conversations.
It enables agents to accept incoming calls, view real-time transcriptions, see AI-generated suggestions, and optionally take over the call manually — all through a sleek, browser-based dashboard.

───────────────────────────────────────────────
FEATURES
───────────────────────────────────────────────

• Twilio Voice Integration – Accept or decline incoming calls directly from the web dashboard
• Real-Time Speech Recognition – Streams and transcribes caller speech using Whisper-based AI
• AI Conversation Suggestions – Displays AI-generated, context-aware responses in real time
• Takeover Mode – Allows the human agent to seamlessly speak in place of the AI
• Automated Call Quality Reports – Generates an AI-evaluated report at the end of each call
• Modular Architecture – Clean separation between Flask backend, WebSocket stream server, and dashboard frontend

───────────────────────────────────────────────
TECHNOLOGY STACK
───────────────────────────────────────────────

Backend: Python (Flask, Flask-SocketIO)
Streaming: WebSockets, Twilio Media Streams
AI: OpenAI API (GPT, Whisper, and TTS models)
Frontend: HTML, CSS, JavaScript
Optional: Node.js for managing frontend dependencies

───────────────────────────────────────────────
PROJECT STRUCTURE
───────────────────────────────────────────────

AI_Call_CoPilot/
│
├── app.py → Flask backend (routes and dashboard updates)
├── stream_server.py → Handles Twilio media stream and AI logic
│
├── templates/
│ └── dashboard.html → Agent dashboard UI
│
├── static/
│ ├── css/ → Stylesheets
│ ├── js/ → Dashboard scripts
│ └── tts/ → Temporary and permanent TTS files
│
├── logs/ → Optional logs directory
├── requirements.txt → Python dependencies
├── package.json → Node dependencies (optional)
├── README.md → Project documentation
└── .env → Environment variables (excluded from Git)

───────────────────────────────────────────────
PREREQUISITES
───────────────────────────────────────────────

Python 3.x installed

Node.js and npm installed (only if using frontend packages)

A Twilio account with a verified phone number

OpenAI API key

Ngrok, Cloudflared, or LocalTunnel for exposing local server to Twilio

───────────────────────────────────────────────
ENVIRONMENT VARIABLES
───────────────────────────────────────────────

Create a file named .env in your project root with the following content:

OPENAI_API_KEY=your_openai_api_key
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWIML_APP_SID=your_twiml_app_sid
TWILIO_NUMBER=your_twilio_phone_number
STREAM_PORT=your port number
FLASK_SOCKET_URL=http://your-flask-url/update
PUBLIC_BASE_URL=https://your-public-url

Note: The .env file should be ignored in .gitignore to prevent exposing sensitive credentials.

───────────────────────────────────────────────
SETUP INSTRUCTIONS
───────────────────────────────────────────────

Step 1: Create and activate a virtual environment

For Windows:
python -m venv venv
venv\Scripts\activate

For Mac or Linux:
python3 -m venv venv
source venv/bin/activate

Step 2: Install Python dependencies
pip install -r requirements.txt

Step 3: (Optional) Install Node.js dependencies
npm install

Step 4: Verify that your .env file is properly configured.

───────────────────────────────────────────────
RUNNING THE APPLICATION
───────────────────────────────────────────────

Start the Flask app:
python app.py

Start the stream server in another terminal:
python stream_server.py

Open the dashboard:
http://your-flask-url

If Twilio needs to reach your local server, expose your Flask app publicly using Ngrok, Cloudflared, or LocalTunnel, and update the PUBLIC_BASE_URL value in your .env file accordingly.

───────────────────────────────────────────────
TYPICAL CALL FLOW
───────────────────────────────────────────────

The caller dials the Twilio number.

Twilio triggers your Flask endpoint and opens a media stream.

stream_server.py receives audio, transcribes it, and sends it to the AI model.

Flask pushes updates to the dashboard via Socket.IO.

The agent sees both caller messages and AI-generated replies.

The agent can take over the conversation at any time.

When the call ends, a call quality report is automatically generated.

───────────────────────────────────────────────
ADDITIONAL NOTES
───────────────────────────────────────────────

• node_modules and venv are intentionally excluded from the repository.
• All keys and credentials are stored securely in .env.
• Update FLASK_SOCKET_URL in .env if the dashboard or Socket.IO endpoint changes.
• Temporary audio files such as tts_*.mp3 are automatically ignored to keep the repository clean.