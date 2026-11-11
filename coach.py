import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
api_key=os.getenv("API_KEY")

if api_key:
    print("Key found")
else:
    print("Key lost")
    
client=genai.Client(api_key=api_key)

response=client.models.generate_content(
    
    model="gemini-3.5-flash",
    contents="I spent 200 shillings on matatu fare. Say ok in one short sentence."

)
print(response.text)