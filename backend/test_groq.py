from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()

def test_groq():
    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        models = client.models.list()
        print("✅ Groq API Key is valid.")
        print(f"Available models: {[m.id for m in models.data][:5]}")
    except Exception as e:
        print(f"❌ Groq API Error: {e}")

if __name__ == "__main__":
    test_groq()
