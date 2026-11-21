import json

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



# Check the summary has all the fields we asked for
def check_summary(data):
    if not isinstance(data, dict):
        return False
    text = data.get("summary")
    if not isinstance(text, str) or text.strip() =="":
        return False
    if not isinstance(data.get("breakdown"), dict):
        return False
    if not isinstance(data.get("total_spent"), (int, float)):
        return False
    tips = data.get("ways_to_save")
    return isinstance(tips, list) and len(tips) == 3


    
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

