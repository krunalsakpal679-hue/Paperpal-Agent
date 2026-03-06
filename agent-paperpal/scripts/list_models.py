# scripts/list_models.py
import google.generativeai as genai
import os
from pathlib import Path
import sys

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent / "backend"))
from app.config import settings

def main():
    genai.configure(api_key=settings.GOOGLE_API_KEY)
    try:
        print("Available models:")
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(m.name)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
