import os
import time
import json
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI, APIError

load_dotenv()
api_key = os.getenv("OPENROUTER_API_KEY")

if api_key:
    print("OpenRouter Key found")
else:
    print("OpenRouter Key lost")

# Connect OpenAI client to OpenRouter
client = OpenAI(
    base_url="https://openrouter.ai" + "/api/v1",
    api_key=api_key,
)


# Check exact model ID on openrouter.ai/models
PRIMARY_MODEL = "deepseek/deepseek-v4.1-flash-1017"
FALLBACK_MODEL = "openrouter/auto"

ROLE = "You are Pesa Coach, a friendly money coach for young Kenyans."
TASK = "The user tells you what they spent, one or two items per message. Put each expense in a category (transport, food, airtime, rent, shopping, other), keep running totals by category, and answer questions about their spending"
CONTEXT = "The user is in Kenya and uses Kenyan shillings (KES). This is a conversation over several turns, so use earlier messages when you answer."
CONSTRAINTS = "Only talk about the user's spending. Never invent an amount the user did not give you. If an amount is missing, ask for it. Keep every reply under 60 words."
OUTPUT = 'Reply ONLY with valid JSON and nothing else, with no markdown. Use exactly these field names and no others: "reply" (a short friendly message to the user), "total_spent" (a number: total KES spent so far in this conversation), "totals" (an object with each category and its running total, for example {"transport": 200, "food": 150}). Never leave a field empty.'

SYSTEM_PROMPT = ROLE + "\n" + TASK + "\n" + CONTEXT + "\n" + CONSTRAINTS + "\n" + OUTPUT

# --- Summary prompt (RTCCO) ---
S_ROLE = "You are Pesa Coach, a money coach for young Kenyans, now writing the end-of-session summary."
S_TASK = "Read the whole conversation and summarise the user's spending."
S_CONTEXT = "The conversation is a record of the expenses the user reported in one session. All amounts are in Kenyan shillings (KES)."
S_CONSTRAINTS = "Use only amounts the user gave you. Never invent an expense. Give exactly three ways to save, each practical for someone in Kenya and based on this user's own spending."
S_OUTPUT = 'Reply ONLY with valid JSON and nothing else, with no markdown. Use exactly these field names and no others: "summary" (2 or 3 short sentences), "breakdown" (an object of category and total KES), "total_spent" (a number), "ways_to_save" (a list of exactly three short tips).'
SUMMARY_PROMPT = S_ROLE + "\n" + S_TASK + "\n" + S_CONTEXT + "\n" + S_CONSTRAINTS + "\n" + S_OUTPUT

# Helper function to call OpenRouter with retries & fallback
def call_openrouter_resilient(history, system_instruction, max_retries=3):
    models_to_try = [PRIMARY_MODEL, PRIMARY_MODEL, FALLBACK_MODEL]
    messages = [{"role": "system", "content": system_instruction}] + history
    
    for attempt in range(max_retries):
        current_model = models_to_try[attempt]
        try:
            response = client.chat.completions.create(
                model=current_model,
                messages=messages,
            )
            return response.choices[0].message.content
        except APIError as e:
            if getattr(e, "status_code", None) in (429, 502, 503) and attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"[Server busy, retrying with {models_to_try[attempt + 1]} in {wait_time}s...]")
                time.sleep(wait_time)
            else:
                raise e

# Clean markdown fences if DeepSeek adds ```json ... ```
def clean_json_text(text):
    if not text:
        return ""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text

# Check the AI's JSON reply
def check_reply(data):
    if not isinstance(data, dict):
        return False
    reply = data.get("reply")
    if not isinstance(reply, str) or reply.strip() == "":
        return False
    if not isinstance(data.get("total_spent"), (int, float)):
        return False
    if not isinstance(data.get("totals"), dict):
        return False
    return True

# Ask OpenRouter, check the reply, retry once if JSON is malformed
def get_valid_reply(history, extra=""):
    for attempt in range(2):
        raw_text = call_openrouter_resilient(
            history=history,
            system_instruction=SYSTEM_PROMPT + extra
        )
        try:
            cleaned = clean_json_text(raw_text)
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            data = None
            
        if data is not None and check_reply(data):
            return data, cleaned
            
    return None, None

# Check the summary has all the fields we asked for
def check_summary(data):
    if not isinstance(data, dict):
        return False
    text = data.get("summary")
    if not isinstance(text, str) or text.strip() == "":
        return False
    if not isinstance(data.get("breakdown"), dict):
        return False
    if not isinstance(data.get("total_spent"), (int, float)):
        return False
    tips = data.get("ways_to_save")
    return isinstance(tips, list) and len(tips) == 3

# Final AI call: Summarise the whole conversation, retry once
def make_summary(history):
    ask = {"role": "user", "content": "The session has ended. Write the summary now."}
    for attempt in range(2):
        try:
            raw_text = call_openrouter_resilient(
                history=history + [ask],
                system_instruction=SUMMARY_PROMPT
            )
            cleaned = clean_json_text(raw_text)
            data = json.loads(cleaned)
            if check_summary(data):
                return data
        except Exception:
            continue
    return None

# Offline fallback: answer from the saved cache when the AI cannot be reached
def offline_reply(user_text):
    try:
        with open("cache.json", "r") as f:
            cached = json.load(f)
    except(FileNotFoundError, json.JSONDecodeError):
        return"I am offline and have no saved totals yet. Please try again later."
    text = user_text.lower()
    if any(ch.isdigit() for ch in text):
        return"I am offline, I can't record new expenses."
    for category, amount in cached.get("totals", {}).items():
        if category.lower() in text:
            return"Offline, from your last saved totals: KES " + str(amount) + " on " + category + "."
    return"Offline, from your last saved totals: KES " + str(cached.get("total_spent", 0)) + " in total."

# --- RAG knowledge base: saving tips the AI can use ---
# --- RAG knowledge base: saving tips the AI can use ---
KNOWLEDGE_BASE = [
    {"keywords": ["matatu", "transport", "fare", "boda", "uber", "bolt"],
     "tip": "Fares often rise at peak hours and when it rains, so travelling a little earlier or later can cost less. Walk short distances when it is safe."},
    {"keywords": ["airtime", "data", "bundle", "safaricom"],
     "tip": "Compare daily, weekly and monthly bundles before buying. A bundle that matches your real use is usually cheaper than many small top-ups."},
    {"keywords": ["food", "lunch", "supper", "breakfast", "groceries"],
     "tip": "Carrying lunch from home a few days a week usually costs less than buying it daily. Buy staples like rice, beans and maize flour in larger packs when you can."},
    {"keywords": ["rent", "house", "landlord"],
     "tip": "Set aside rent as soon as money comes in, so it is not spent on small things during the month."},
    {"keywords": ["mpesa", "m-pesa", "withdraw", "send", "sent", "fee", "charges"],
     "tip": "M-Pesa send and withdrawal charges add up. Check the current charges, and pay through a till or paybill where it is offered, instead of withdrawing cash first."},
    {"keywords": ["save", "saving", "savings", "budget", "salary", "income"],
     "tip": "Treat saving like a bill: move a small fixed amount to a separate savings place on payday, instead of saving whatever is left."},
]

# Retrieve: find the tips that match the user's message
def find_tips(user_text):
    text = user_text.lower()
    found = []
    for item in KNOWLEDGE_BASE:
        for word in item["keywords"]:
            if word in text:
                found.append(item["tip"])
                break
    return found[:2]

# Conversation Memory
def new_session():
    history=[]
    session_log=[]
    while True:
        user_text=input("You: ").strip()
        if user_text=="":
            print("Please type something.")
            continue
        if user_text.lower()=="exit":
            print("Session ended.")
            break
        history.append({"role": "user", "content": user_text})

        session_log.append({"role": "user", "text": user_text}) 
        
        #Storing Gemini reply
        try:
            tips = find_tips(user_text)
            print("[Knowledge base] Tips used:", tips)
            extra = ""
            if tips:
                extra = "\nHelpful saving tips you may use if they are relevant. Do not invent other tips:\n-" + "\n- ".join(tips)
            data, raw = get_valid_reply(history, extra)

            if data is None: 
                print("Sorry, I could not get a clear answer. Please try again.")
                history.pop()
                continue
            print(data["reply"])
            
            session_log.append({"role": "coach", "text": data["reply"]})   # <-- ADD (8 spaces in)
            history.append({"role": "assistant", "content": raw})

            with open("cache.json", "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print("Sorry, I could not reach the AI right now, so I am using your saved totals instead.")
            print("Details:", getattr(e, "body", e))
            print(offline_reply(user_text))
               
            history.pop()
            
    # --- SECTION 6: Save the session ---
    if session_log:
        print("writing your summary...")
        summary = make_summary(history)
        if summary is None:
            print("Sorry, I could not create a summary this time.")
        else:
            print("\n---Session summary ---")
            print(summary["summary"])
            print("Total spent: KES", summary["total_spent"])
            for category, amount in summary["breakdown"].items():
                print("-", category + ":", amount)
            print("Ways to save:")
            for tip in summary["ways_to_save"]:
                print("*", tip)
        
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        os.makedirs("sessions", exist_ok=True)
        filename = "sessions/session_" + stamp + ".json"
        with open(filename, "w") as f:
            json.dump({"conversation": session_log, "summary": summary}, f, indent=2)
        print("Session saved to", filename)
        
#Opening a past session:
def open_past_session():
    if not os.path.exists("sessions"):
        print("No saved sessions yet")
        return
    files=sorted(os.listdir("sessions"))
    if not files:
        print("No saved sessions yet.")
        return
    print("\nSaved sessions:")
    for number, name in enumerate(files, start=1):
        print(number, "-", name)
    choice=input("Enter the number of the session to open:").strip()
    try:
        index=int(choice) - 1
        if index < 0 or index >= len(files):
            print("That number is not in the list.")
            return
        with open("sessions/" + files[index], "r") as f:
            saved = json.load(f)
        print("\n---" + files[index] + "---")
        for entry in saved["conversation"]:
            print(entry["role"] + ": " + entry ["text"])
    except ValueError:
        print("Please type a number.")
    except FileNotFoundError:
        print("That session file could not be found.")
    except(json.JSONDecodeError, KeyError):
        print("That session file is damaged and cannot be read.")
                

#Main Menu
def main_menu():
    while True:
        print("\n=== Pesa Coach ===")
        print("1. Start a new session")
        print("2. Open a past session")
        print("3. Exit")
        choice=input("Choose 1,2 or 3: ").strip()
        
        if choice=="1":
            new_session()
        elif choice=="2":
            open_past_session()
        elif choice=="3":
            print("Goodbye!")
            break
        else:
            print("Please choose 1, 2, or 3.")
            
if __name__=="__main__":
    main_menu()
