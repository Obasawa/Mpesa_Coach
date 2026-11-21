import streamlit as st
from google.genai import types
import json
from coach import get_valid_reply, find_tips, offline_reply
import os
from datetime import datetime
from coach import get_valid_reply, make_summary
from knowledge import find_tips
from safeguards import offline_reply


st.title("Pesa Coach")

# Streamlit re-runs this file on every click, so memory must live in session_state
if "history" not in st.session_state:
    st.session_state.history = []
if "log" not in st.session_state:
    st.session_state.log = []
    
    
# Sidebar buttons
with st.sidebar:
    st.header("Session")
    end_clicked = st.button("End session and summarise")
    new_clicked = st.button("Start a new session")

# New session: clear the memory
if new_clicked:
    st.session_state.history = []
    st.session_state.log = []
    st.rerun()    
# Show the conversation so far
for entry in st.session_state.log:
    who = "user" if entry["role"] == "user" else "assistant"
    with st.chat_message(who):
        st.write(entry["text"])

# Chat box at the bottom of the page
user_text = st.chat_input("Tell me what you spent...")

if user_text:
    st.session_state.history.append(types.Content(role="user", parts=[types.Part(text=user_text)]))
    st.session_state.log.append({"role": "user", "text": user_text})
    with st.chat_message("user"):
        st.write(user_text)
    try:
        tips = find_tips(user_text)
        extra = ""
        if tips:
            extra = "\nHelpful saving tips you may use if they are relevant. Do not invent other tips:\n- " + "\n- ".join(tips)
        data, raw = get_valid_reply(st.session_state.history, extra)
        if data is None:
            reply = "Sorry, I could not get a clear answer. Please try again."
            st.session_state.history.pop()
        else:
            reply = data["reply"]
            st.session_state.history.append(types.Content(role="model", parts=[types.Part(text=raw)]))
            with open("cache.json", "w") as f:
                json.dump(data, f, indent=2)
    except Exception as error:
        st.error("Details: " + str(error))
        reply = "I could not reach the AI, so I am using your saved totals instead. " + offline_reply(user_text)
        st.session_state.history.pop()
    st.session_state.log.append({"role": "coach", "text": reply})
    with st.chat_message("assistant"):
        st.write(reply)
        
# End session: write the summary and save everything
if end_clicked:
    if not st.session_state.log:
        st.warning("Nothing to summarise yet. Send a message first.")
    else:
        with st.spinner("Writing your summary..."):
            summary = make_summary(st.session_state.history)
        if summary is None:
            st.error("Sorry, I could not create a summary this time.")
        else:
            st.subheader("Session summary")
            st.write(summary["summary"])
            st.write("Total spent: KES", summary["total_spent"])
            for category, amount in summary["breakdown"].items():
                st.write("- " + category + ": " + str(amount))
            st.write("Ways to save:")
            for tip in summary["ways_to_save"]:
                st.write("* " + tip)
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        os.makedirs("sessions", exist_ok=True)
        filename = "sessions/session_" + stamp + ".json"
        with open(filename, "w") as f:
            json.dump({"conversation": st.session_state.log, "summary": summary}, f, indent=2)
        st.success("Session saved to " + filename)