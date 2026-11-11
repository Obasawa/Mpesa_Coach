import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
import json

load_dotenv()
api_key=os.getenv("API_KEY")

if api_key:
    print("Key found")
else:
    print("Key lost")
    
client=genai.Client(api_key=api_key)

ROLE="You are Pesa Coach, a friendly money coach for young Kenyans."
TASK="The user tells you what they spent, one or two items per message. Put each expense in a category (transport, food, airtime, rent, shopping, other), keep running totals by category, and answer questions about their spending"
CONTEXT="The user is in Kenya and uses Kenyan shillings (KES). This is a conversation over several turns, so use earlier messages when you answer."
CONSTRAINTS="Only talk about the user's spending. Never invent an amount the user did not give you.if an amount is missing, ask for it. Keep every reply under 60 words."
OUTPUT = 'Reply ONLY with valid JSON and nothing else, with no markdown. Use exactly these field names and no others: "reply" (a short friendly message to the user), "total_spent" (a number: total KES spent so far in this conversation), "totals" (an object with each category and its running total, for example {"transport": 200, "food": 150}). Never leave a field empty.'

SYSTEM_PROMPT = ROLE + "\n" + TASK + "\n" + CONTEXT + "\n" + CONSTRAINTS + OUTPUT

response=client.models.generate_content(
    
    model="gemini-3.8-flash",
    contents="I spent 200 on matatu and 150 on lunch.",
    config=types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        response_mime_type="application/json")

)

data=json.loads(response.text)
print(data["reply"])

