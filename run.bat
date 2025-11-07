@echo off
chcp 65001 >nul
title AI Call Assistant
call venv\Scripts\activate.bat

start "Flask" cmd /k python app.py
timeout /t 3 >nul
start "Stream" cmd /k python stream_server.py
timeout /t 3 >nul
start "Ngrok Flask" cmd /k ngrok http --domain=flask-tunnel.ngrok.dev 5000
timeout /t 3 >nul
start "Ngrok Stream" cmd /k ngrok http --domain=stream-tunnel.ngrok.dev 8000
timeout /t 3 >nul
start http://127.0.0.1:5000

echo -------------------------------------------------
echo Dashboard:  http://127.0.0.1:5000
echo Flask URL:  https://flask-tunnel.ngrok.dev/voice
echo Stream URL: wss://stream-tunnel.ngrok.dev/stream
echo -------------------------------------------------
pause