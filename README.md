\# AI Call CoPilot



AI Call CoPilot is a voice-call assistant that connects Twilio voice calls to a Flask and Socket.IO backend and uses AI to provide real-time conversation transcription and agent suggestions. It is designed for call dashboards where an agent can accept a call, view the live conversation feed, see AI-generated replies, and optionally take over the call.



\## 1. Features



1\. Twilio voice call handling with accept/decline from the dashboard

2\. Real-time speech-to-text using the AI stream server

3\. AI suggestions displayed on the dashboard for the agent

4\. Take-over mode so the human can speak instead of AI

5\. Call report generation at the end of the call

6\. Separation of frontend (dashboard) and backend (Flask, stream server)



\## 2. Technology Stack



1\. Python (Flask, Socket.IO)

2\. Twilio Voice

3\. OpenAI API

4\. WebSockets

5\. HTML, CSS, JavaScript for the dashboard

6\. Optional: Node.js for frontend dependencies



\## 3. Project Structure



The project may look like this:



AI\_Call\_CoPilot/

&nbsp; app.py

&nbsp; stream\_server.py

&nbsp; templates/

&nbsp;   dashboard.html

&nbsp;   

&nbsp; static/

&nbsp;   css/

&nbsp;   js/

&nbsp; logs/

&nbsp; requirements.txt

&nbsp; package.json

&nbsp; README.md

&nbsp; .env  (not committed)



app.py runs the Flask server and exposes routes and Socket.IO events.

stream\_server.py listens to the Twilio media stream and forwards audio/text to the AI model.



\## 4. Prerequisites



1\. Python 3.x installed

2\. Node.js and npm installed (if using the frontend dependencies)

3\. A Twilio account with a verified phone number

4\. OpenAI API key

5\. Ngrok or Cloudflared or any public tunnel if Twilio needs to reach your local server



\## 5. Environment Variables



Create a .env file in the project root and define values similar to the following:



OPENAI\_API\_KEY=your\_openai\_api\_key

TWILIO\_ACCOUNT\_SID=your\_twilio\_sid

TWILIO\_AUTH\_TOKEN=your\_twilio\_auth\_token

TWIML\_APP\_SID=your\_twiml\_app\_sid

TWILIO\_NUMBER=your\_twilio\_phone\_number

STREAM\_PORT=8000

FLASK\_SOCKET\_URL=http://127.0.0.1:5000/update

PUBLIC\_BASE\_URL=https://your-public-url



Do not commit the .env file. It is already ignored through .gitignore.



\## 6. Setup



1\. Create and activate a virtual environment



&nbsp;  Windows:

&nbsp;  python -m venv venv

&nbsp;  venv\\Scripts\\activate



2\. Install Python dependencies



&nbsp;  pip install -r requirements.txt



3\. Install Node dependencies if needed



&nbsp;  npm install



4\. Make sure .env is present in the project root



\## 7. Running the Application



Run the Flask app:



python app.py



Run the stream server in another terminal:



python stream\_server.py



Open the dashboard in the browser:



http://127.0.0.1:5000



If Twilio is calling your local machine, make sure you expose the Flask app through ngrok or cloudflared and update the public URL inside Twilio.



\## 8. Typical Call Flow



1\. Caller dials the Twilio number.

2\. Twilio hits your Flask endpoint and connects the media stream.

3\. stream\_server.py receives audio, sends it to the AI model, and sends updates to the Flask Socket.IO endpoint.

4\. The dashboard displays caller text, AI suggestions, and call status.

5\. Agent can select to take over while still viewing AI suggestions.

6\. When the call ends, the system can produce a call report.



\## 9. Notes



1\. node\_modules and venv are intentionally ignored and are not part of the repository.

2\. All sensitive keys must be read from .env.

3\. If the dashboard path or Socket.IO endpoint changes, update FLASK\_SOCKET\_URL in .env.



\## 10. License



Add a license here if you plan to make this public.



