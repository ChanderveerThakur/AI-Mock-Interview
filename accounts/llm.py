import os 
from google import genai
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=API_KEY)

def get_gemini_response(user_query):

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=user_query
    )

    return response.text