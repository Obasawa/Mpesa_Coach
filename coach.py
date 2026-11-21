import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
import json
from datetime import datetime
from prompts import SYSTEM_PROMPT, SUMMARY_PROMPT
from knowledge import KNOWLEDGE_BASE, find_tips
from safeguards import check_reply, check_summary, offline_reply

load_dotenv()
api_key=os.getenv("API_KEY")

if api_key:
    print("Key found")
else:
    print("Key lost")
    
client=genai.Client(api_key=api_key)
MODEL_NAME = "gemini-3.5-flash"

#Ask Gemini, check the reply, retry once
def get_valid_reply(history, extra=""):
    for attempt in range(2):
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=history,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT + extra,
                response_mime_type="application/json")
            )
            
            
        try:
            data=json.loads(response.text)
        except json.JSONDecodeError:
            data = None
        if data is not None and check_reply(data):
            return data, response.text
        
    return None, None

#Final AI call: Summarise the whole conversation, retry once
def make_summary(history):
    ask = types.Content(role="user", parts=[types.Part(text="The session has ended. Write the summary now.")])
    for attempt in range (2):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=history + [ask],
                config=types.GenerateContentConfig(
                    system_instruction=SUMMARY_PROMPT,
                    response_mime_type="application/json")
                )
            data = json.loads(response.text)
        except Exception:
            data = None
        
        if check_summary(data):
            return data
    return None

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
            history.append(types.Content(role="model", parts=[types.Part(text=raw)]))
            with open("cache.json", "w") as f:
                json.dump(data, f, indent=2)
        except Exception as error:
            print("Sorry, I could not reach the AI right now.so I am using your saved totals instead.")
            print("Details:", error)
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