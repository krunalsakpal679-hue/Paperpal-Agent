# backend/app/agents/interpretation/llm_extractor.py
"""
LLMRuleExtractor: Uses Google Gemini API to extract structured JRO from journal guideline text.
Uses few-shot prompting and handles validation retries with automated self-correction.
Optimized for Gemini 2.0 Flash (Free Tier).
"""

import json
import logging
import re
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional

import google.generativeai as genai
from app.config import settings
from app.schemas.jro_schema import JROSchema

logger = logging.getLogger(__name__)

class LLMRuleExtractor:
    """
    Extracts formatting rules using Google Gemini.
    Implements retries and schema validation with self-correction.
    """

    def __init__(self):
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        # Using gemini-2.0-flash as it's the current flagship for speed/cost (free tier availability)
        self.model_name = "gemini-2.0-flash" 
        self.model = genai.GenerativeModel(self.model_name)
        
        self.curr_dir = Path(__file__).parent
        try:
            self.system_prompt = (self.curr_dir / "prompts" / "system_prompt.txt").read_text(encoding="utf-8")
        except FileNotFoundError:
            self.system_prompt = "You are an expert academic editor. Extract journal formatting rules into structured JSON."
            
        try:
            self.few_shot_examples = json.loads((self.curr_dir / "prompts" / "few_shot_examples.json").read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            self.few_shot_examples = []

    async def extract(self, page_text: str, journal_name: str) -> JROSchema:
        """
        Extract rules from guidelines text using Gemini.
        Retries up to 2 times on validation failure.
        """
        user_prompt = self._build_user_prompt(page_text, journal_name)
        
        retries = 0
        max_retries = 2
        last_error = ""
        
        while retries <= max_retries:
            try:
                full_prompt = f"{self.system_prompt}\n\n{user_prompt}"
                if last_error:
                    full_prompt += f"\n\n[RETRY FEEDBACK] Previous attempt failed validation with error: {last_error}. Please ensure the JSON matches the schema perfectly."
                
                # Gemini generate_content_async
                response = await self.model.generate_content_async(full_prompt)
                
                raw_content = response.text
                json_str = self._clean_json_string(raw_content)
                data = json.loads(json_str)
                
                # Ensure journal name is consistent
                data["journal_name"] = journal_name
                
                return JROSchema.model_validate(data)
                
            except Exception as e:
                retries += 1
                last_error = str(e)
                logger.warning("[%s] Extraction attempt %d failed for %s: %s", "LLMRuleExtractor", retries, journal_name, last_error)
                if retries <= max_retries:
                    await asyncio.sleep(2 * retries)
        
        logger.error("[%s] Max retries exceeded for %s. Returning partial defaults.", "LLMRuleExtractor", journal_name)
        return self._make_partial_jro(journal_name)

    def _build_user_prompt(self, page_text: str, journal_name: str) -> str:
        """Construct the user prompt with few-shot examples and schema requirements."""
        prompt_parts = [
            f"Extract formatting rules for '{journal_name}' from the following guideline text:\n\n{page_text}\n",
            "\nFollow these structural patterns for your output:"
        ]
        
        for ex in self.few_shot_examples[:2]:
            prompt_parts.append(f"GUIDELINE: {ex.get('input', '...')}")
            prompt_parts.append(f"RESULT JSON: {json.dumps(ex.get('expected_output', {}))}")
            
        prompt_parts.append(f"\nReturn ONLY valid JSON matching this schema: {json.dumps(JROSchema.model_json_schema())}")
        return "\n".join(prompt_parts)

    def _clean_json_string(self, content: str) -> str:
        """Extract JSON from potential markdown fences or extra text."""
        # Find the first '{' and last '}'
        start = content.find('{')
        end = content.rfind('}')
        if start != -1 and end != -1:
            return content[start:end+1]
        
        # Fallback to regex cleaning if simple find fails
        content = re.sub(r"```json\s*", "", content)
        content = re.sub(r"```\s*", "", content)
        return content.strip()

    def _make_partial_jro(self, journal_name: str) -> JROSchema:
        """Create a JRO with sensible defaults and low confidence."""
        return JROSchema(
            journal_name=journal_name,
            extraction_source="gemini_partial_fallback",
            extraction_confidence=0.1,
            heading_rules={"levels": {}},
            abstract_rules={},
            layout_rules={},
            figure_rules={},
            table_rules={},
            section_requirements={}
        )

if __name__ == "__main__":
    import asyncio
    async def test():
        extractor = LLMRuleExtractor()
        print(f"Extractor initialized with model: {extractor.model_name}")
    asyncio.run(test())
