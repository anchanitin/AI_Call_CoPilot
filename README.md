# 🤖 AI Call CoPilot

AI Call CoPilot is a **voice-call assistant** that integrates **Twilio Voice**, **Flask**, and **OpenAI** to handle and assist with **live phone conversations**.  
It enables agents to **accept incoming calls**, view **real-time transcriptions**, see **AI-generated suggestions**, and optionally **take over the call manually** — all through a sleek, browser-based dashboard.

---

## 🚀 Project Overview

The goal of this project is to build a **fully autonomous AI-powered communication system** capable of:
- Managing **incoming and outgoing calls** through Twilio Voice  
- Transcribing calls in **real time** using **Whisper AI**  
- Using **GPT reasoning** to generate intelligent and context-aware responses  
- **Speaking directly to the caller** through **OpenAI Text-to-Speech (TTS)**
- Displaying all call activity, transcriptions, and AI responses on a **real-time agent dashboard**
- Generating **automated call summaries and quality reports** at the end of each call

Unlike traditional AI assist tools, the **AI Call CoPilot** operates **independently without agent intervention.**
The human agent **monitors the conversation** through the dashboard but does not interact with the caller.
All speech, logic, and flow are driven by the **AI in real time** — making it a complete **end-to-end Voice AI Communication System.**

This project showcases a **full-stack AI + Voice Engineering architecture**, combining:

- **Real-time AI inference (Whisper, GPT, TTS)**
- **Low-latency media streaming via WebSockets**
- **Twilio Voice orchestration**
- **Live analytics dashboard using Flask + SocketIO**

---

## 🧱 Architecture

**Data & Audio Flow:**  
<img width="5100" height="2300" alt="AI Call CoPilot Workflow" src="https://github.com/anchanitin/AI_Call_CoPilot/blob/main/Architecture_%26_Output_Screenshots/Workflow.png" />

---

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

- **Caller dials** the Twilio number.
- Twilio triggers a **Flask TwiML endpoint** that establishes the WebSocket connection.
- The **WebSocket Stream Server** receives live audio data from the caller.
- The audio is sent to **OpenAI Whisper** for **speech-to-text transcription**.
- **GPT reasoning** generates a real-time AI reply based on conversation context.
- The reply text is converted to speech using **OpenAI TTS**.
- The **TTS audio** is streamed **back to Twilio**, allowing the AI to **speak directly to the caller.**
- Meanwhile, the dashboard **displays** the full transcription, responses, and AI call analysis in real time.

---

## 🧾 Additional Notes
- node_modules and venv are intentionally excluded from the repository.
- All keys and credentials are stored securely in .env.
- Update FLASK_SOCKET_URL in .env if the dashboard or Socket.IO endpoint changes.
- Temporary audio files such as tts_*.mp3 are automatically ignored to keep the repository clean.