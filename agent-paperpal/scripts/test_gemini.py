# scripts/test_gemini.py
import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from app.agents.interpretation.llm_extractor import LLMRuleExtractor
from app.config import settings

async def main():
    print(f"Testing Gemini integration with model: gemini-1.5-flash")
    print(f"API Key present: {'Yes' if settings.GOOGLE_API_KEY and settings.GOOGLE_API_KEY != 'AIzaSyxxxxxxxxxxxxxxxxxxxx' else 'No (Placeholder only)'}")
    
    if not settings.GOOGLE_API_KEY or settings.GOOGLE_API_KEY == 'AIzaSyxxxxxxxxxxxxxxxxxxxx':
        print("\nERROR: Please update your GOOGLE_API_KEY in .env before running this test.")
        return

    extractor = LLMRuleExtractor()
    
    sample_text = """
    Author Guidelines for the Journal of AI Research:
    Abstracts should be no more than 150 words. 
    Use APA citation style.
    Main headings should be bold and 14pt.
    Figures should have captions below the image.
    Required sections include Introduction, Related Work, and Conclusion.
    """
    
    try:
        jro = await extractor.extract(sample_text, "Journal of AI Research")
        print("\nSUCCESS! Gemini extracted the following JRO:")
        print(jro.model_dump_json(indent=2))
    except Exception as e:
        print(f"\nFAILED: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
