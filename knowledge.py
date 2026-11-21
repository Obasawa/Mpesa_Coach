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