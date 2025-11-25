RESTAURANT_INFO = ("""
    Restaurant Name: The Restaurant
    Cuisine: Italian & Continental
    Timings: 10:00 AM - 10:00 PM
    Location: 123 Main Street, Austin, TX
    Contact: +1 (507) 554-1673
    Menu Highlights:
    - Starters: Garlic Bread, Caesar Salad, Bruschetta
    - Main Course: Alfredo Pasta, Margherita Pizza, Lasagna
    - Desserts: Tiramisu, Chocolate Mousse
    - Beverages: Coffee, Wine, Fresh Juice
    Policies:
    - Accepts reservations up to 10 people.
    - Takeout and curbside pickup available.
    - No home delivery.
""")

SYSTEM_INSTRUCTIONS = (
    "You are Mia, a polite and professional restaurant receptionist for 'The Restaurant'. "
    "You handle calls for reservations, timings, and menu questions. "
    "Always speak only in English. Never switch to any other language, even if the caller speaks in a different language, ask them to speak in English."
    "Keep track of what the caller already said and never ask the same question again. "
    "And also be sure to only provide information that is in the restaurant info provided. "
    "Be warm, concise, and conversational. Use short natural English sentences. "
    "If there is prolonged silence from the caller (for example 5 seconds or more), you must politely ask: 'Are you still there? Can I help you with anything else?'. And do not repeat this frequently, ask only after prolonged silence. "
    "If the caller gives reservation details, confirm clearly, then ask for their name, email and phone "
    "If they provide contact info, repeat it back to confirm accuracy. If they said its correct or right or anything that means yes, proceed. "
    "If unclear. Ask them to spell each slowly and confirm what you understood. "
    "Unclear even after spelling out, ask only for that portion to be repeated. Once both are clear, confirm everything, "
    "Then say: 'Thank you! Your reservation is confirmed. We look forward to seeing you.' "
    f"Here is the restaurant information:\n{RESTAURANT_INFO}"
)


QA_PROMPT = (
    "You are a senior QA evaluator analyzing a real phone call between a human customer "
    "and an AI restaurant receptionist. Evaluate ONLY what is explicitly present in the "
    "conversation log below. Do NOT guess or fabricate details.\n\n"
    "Use the following rubric and be strict and evidence-based:\n"
    "1. Overall Score (0-10) based only on demonstrated behavior.\n"
    "2. Communication Metrics (each 0-10, or 'N/A' if not enough evidence):\n"
    "   - Greeting & Politeness\n"
    "   - Active Listening\n"
    "   - Clarity & Conciseness\n"
    "   - Empathy & Tone\n"
    "   - Accuracy of Information\n"
    "3. Summary (2-3 sentences describing how the AI performed overall).\n"
    "4. Detailed Analysis (3-5 sentences explaining specific strengths and issues based on the transcript).\n"
    "5. Strengths (up to 3 short bullet points).\n"
    "6. Areas for Improvement (up to 3 short bullet points).\n"
    "7. AI Recommendations (practical suggestions to improve future calls).\n\n"
    "Return plain text only (no markdown tables or formatting). "
    "If any metric cannot be judged from the transcript, clearly mark it as 'N/A'.\n\n"
        
)


EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<title>Reservation Confirmation</title>

<style>
    body {{
        font-family: Arial, sans-serif;
        background-color: #f7f7f7;
        padding: 0;
        margin: 0;
    }}
    .container {{
        background: #ffffff;
        max-width: 600px;
        margin: 30px auto;
        padding: 25px;
        border-radius: 12px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.08);
    }}
    h2 {{
        color: #2c3e50;
        text-align: center;
        border-bottom: 2px solid #e2e2e2;
        padding-bottom: 10px;
    }}
    .details-box {{
        background: #f0f7ff;
        border-left: 5px solid #3498db;
        padding: 15px;
        margin: 20px 0;
        border-radius: 8px;
    }}
    .details-box p {{
        font-size: 16px;
        margin: 5px 0;
    }}
    .footer {{
        margin-top: 25px;
        text-align: center;
        font-size: 14px;
        color: #777;
    }}
</style>
</head>

<body>
<div class="container">
    <h2>🍽️ Reservation Confirmed!</h2>
    <p>Hi <b>{{name}}</b>,</p>

    <p>Your reservation at <b>The Restaurant</b> has been successfully confirmed.</p>

    <div class="details-box">
        <p><b>Date:</b> {{date}}</p>
        <p><b>Time:</b> {{time}}</p>
        <p><b>Guests:</b> {{people}}</p>
        <p><b>Phone:</b> {{phone}}</p>
        <p><b>Email:</b> {{email}}</p>
    </div>

    <p>
        We're excited to host you!  
        If you need to make any changes, feel free to reply to this email.
    </p>

    <p class="footer">
        — The Restaurant Team<br>
        123 Main Street, Austin, TX<br>
        Open 10 AM - 10 PM
    </p>
</div>
</body>
</html>
"""
