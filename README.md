# 🤖 AI Call CoPilot

AI Call CoPilot is a **voice-call assistant** that integrates **Twilio Voice**, **Flask**, and **OpenAI** to handle and assist with **live phone conversations**.  
It enables agents to **accept incoming calls**, view **real-time transcriptions**, see **AI-generated suggestions**, and optionally **take over the call manually** — all through a sleek, browser-based dashboard.

---

## 🚀 Project Overview

The goal of this project is to build an **AI-powered communication system** capable of:
- Managing **incoming and outgoing calls** through Twilio Voice  
- Transcribing calls in **real time** using **Whisper AI**  
- Generating **context-aware suggestions** using GPT  
- Allowing agents to **seamlessly take control** when needed  
- Producing **automated call quality reports** post-call  

This project demonstrates the integration of **real-time AI inference**, **telephony streaming**, and **web dashboard visualization**, representing a full-stack **AI + Voice Engineering** solution.

---

<img width="5100" height="2300" alt="AI Call CoPilot Workflow" src="https://github.com/anchanitin/AI_Call_CoPilot/blob/main/Architecture_%26_Output_Screenshots/Workflow.png" />

---

## 🧱 Architecture

**Data & Audio Flow:**  
`Caller → Twilio Voice → Flask (TwiML Endpoint) → WebSocket Stream Server → OpenAI (Whisper + GPT + TTS) → Agent Dashboard`

**Tools & Components:**
- **Twilio Voice API** – Handles call routing and audio streaming  
- **Flask Backend** – Hosts endpoints, TwiML responses, and dashboard updates  
- **Stream Server (WebSocket)** – Processes audio, transcription, and AI logic  
- **OpenAI (Whisper, GPT, TTS)** – Provides transcription, response generation, and speech synthesis  
- **Frontend (HTML, CSS, JS)** – Displays real-time updates, AI replies, and agent actions  

---

## ⚙️ Technology Stack

| Layer | Tools / Libraries |
|-------|-------------------|
| **Backend** | Python (Flask,Flask-SocketIO) |
| **Streaming** | WebSockets, Twilio Media Streams |
| **AI Models** | OpenAI Whisper, GPT, TTS |
| **Frontend** | HTML, CSS, JavaScript |
| **Optional** | Node.js for managing frontend dependencies |

---

## 📂 Repository Structure


```
AI_Call_CoPilot/
│
├── app.py # Flask backend (routes & dashboard updates)
├── stream_server.py # Handles Twilio media stream & AI logic
│
├── templates/ # HTML templates
│ └── dashboard.html # Agent dashboard UI
│
├── static/ # Frontend assets
│ ├── css/ # Stylesheets
│ ├── js/ # Dashboard scripts
│ └── tts/ # Temporary audio files
│
├── logs/ # Optional logs directory
├── requirements.txt # Python dependencies
├── package.json # Node dependencies (optional)
├── README.md # Documentation
└── .env # Environment variables (excluded from Git)
```

---
## ⚙️ Setup & Installation

### 1️⃣ Clone the Repository
```bash
git clone reponame
cd AI_Call_CoPilot
```

### 2️⃣ Create a Virtual Environment
```bash
python -m venv venv
venv\Scripts\activate    #(Mac or Linux : source venv/bin/activate)
pip install -r requirements.txt
npm install(optional)
```

### 3️⃣ Configure Environment Variables
Add your credentials in `.env` or environment variables:
```bash
OPENAI_API_KEY=your_openai_api_key
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWIML_APP_SID=your_twiml_app_sid
TWILIO_NUMBER=your_twilio_phone_number
STREAM_PORT=8000
FLASK_SOCKET_URL=http://127.0.0.1:5000/update
PUBLIC_BASE_URL=https://your-public-url
```

### 4️⃣ Run Application
```bash
# Terminal 1 - Start Flask backend
python app.py

# Terminal 2 - Start WebSocket stream server
python stream_server.py

```
If Twilio needs to access your local app, expose it using Ngrok, Cloudflared, or LocalTunnel, and update the PUBLIC_BASE_URL in .env.

---

## 🧩 Typical call flow

Caller dials your Twilio number

Twilio triggers the Flask endpoint and opens a media stream

stream_server.py receives audio → sends to Whisper → generates transcript

GPT produces a smart AI response

Flask pushes updates to the dashboard via Socket.IO

Agent can monitor, respond, or take over the conversation

At call end → AI generates a Call Quality Report

---

## 🧾 Additional Notes
node_modules and venv are intentionally excluded from the repository.
All keys and credentials are stored securely in .env.
Update FLASK_SOCKET_URL in .env if the dashboard or Socket.IO endpoint changes.
Temporary audio files such as tts_*.mp3 are automatically ignored to keep the repository clean.