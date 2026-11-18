# Pesa Coach - AI Smart Assistant with Memory

## What it does
WRITE 2 OR 3 SENTENCES IN YOUR OWN WORDS: what the tool is, who it helps,
and what the user sees at the end of a session.

## How to run
1. Clone this repository
2. Create and activate a virtual environment:
   python -m venv venv
   venv\Scripts\activate
3. Install the packages:
   pip install -r requirements.txt
4. Set your API key (see the next section)
5. Run the tool:
   python coach.py

## How to set the API key
Create a file called .env in the project folder with one line:
API_KEY=your_gemini_key_here
Never share this file or upload it to GitHub.

## Menu
1. Start a new session
2. Open a past session
3. Exit

## Features
- Conversation memory: the full chat is sent with every AI call
- Replies are returned as JSON and checked, with one retry
- A knowledge base of saving tips (RAG)
- Works offline using saved totals
- Session summary saved to a dated file in the sessions folder

## Sample session
See the samples folder.

## Team
- OBA SAWA
- Debby
- Sir-Isi