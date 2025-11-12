import os
from openai import OpenAI
from dotenv import load_dotenv

# Load .env environment variables
load_dotenv()

# Make sure the OPENAI_API_KEY is loaded
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("❌ OPENAI_API_KEY not found. Add it to your .env file.")

client = OpenAI(api_key=OPENAI_API_KEY)

# Correct folder path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
tts_dir = os.path.join(BASE_DIR, "static", "tts")
os.makedirs(tts_dir, exist_ok=True)

GREETING_TEXT = (
    "Hello! This is Mia from The Restaurant. "
    "How can I assist you today? Would you like to make a reservation or ask about our menu?"
)

output_path = os.path.join(tts_dir, "greeting.mp3")

print("🎤 Generating Nova greeting...")

speech = client.audio.speech.create(
    model="gpt-4o-mini-tts",
    voice="nova",
    input=GREETING_TEXT,
)

with open(output_path, "wb") as f:
    f.write(speech.read())

print("✅ Saved greeting as:", output_path)
