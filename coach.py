import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
import json
from datetime import datetime

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
CONSTRAINTS="Only talk about the user's spending. Never invent an amount the user did not give you. If an amount is missing, ask for it. Keep every reply under 60 words."
OUTPUT = 'Reply ONLY with valid JSON and nothing else, with no markdown. Use exactly these field names and no others: "reply" (a short friendly message to the user), "total_spent" (a number: total KES spent so far in this conversation), "totals" (an object with each category and its running total, for example {"transport": 200, "food": 150}). Never leave a field empty.'

SYSTEM_PROMPT = ROLE + "\n" + TASK + "\n" + CONTEXT + "\n" + CONSTRAINTS + "\n" + OUTPUT
 
# Check the AI's JSON reply
def check_reply(data):
    if not isinstance(data, dict):
        return False
    reply=data.get("reply")
    if not isinstance(reply,str) or reply.strip()== "":
        return False
    if not isinstance(data.get("total_spent"), (int, float)):
        return False
    if not isinstance(data.get("totals"), dict):
        return False
    return True

#Ask Gemini, check the reply, retry once
def get_valid_reply(history):
    for attempt in range(2):
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=history,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json")
            )
            
            
        try:
            data=json.loads(response.text)
        except json.JSONDecodeError:
            data = None
        if data is not None and check_reply(data):
            return data, response.text
        
    return None, None


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
        history.append(types.Content(role="user", parts=[types.Part(text=user_text)])) 
        session_log.append({"role": "user", "text": user_text}) 
        
        #Storing Gemini reply
        try:
            data, raw = get_valid_reply(history)
            if data is None: 
                print("Sorry, I could not get a clear answer. Please try again.")
                history.pop()
                continue
            print(data["reply"])
            
            session_log.append({"role": "coach", "text": data["reply"]})   # <-- ADD (8 spaces in)
            history.append(types.Content(role="model", parts=[types.Part(text=raw)]))
            with open("cache.json", "w") as f:
                json.dump(data, f, indent=2)
        except Exception as error:
            print("Sorry, I could not reach the AI right now. Please try again.")
            print("Details:", error)
               
            history.pop()
            
    # --- SECTION 6: Save the session ---
    if session_log:
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        os.makedirs("sessions", exist_ok=True)
        filename = "sessions/session_" + stamp + ".json"
        with open(filename, "w") as f:
            json.dump({"conversation": session_log}, f, indent=2)
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
            
main_menu()
        

            

