# backend/app/agents/interpretation/llm_extractor.py
"""
LLMRuleExtractor: Uses Claude API to extract structured JRO from journal guideline text.
Uses few-shot prompting and handles validation retries.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import google.generativeai as genai
from app.config import settings
from app.schemas.jro_schema import JROSchema

logger = logging.getLogger(__name__)

class LLMRuleExtractor:
    """
    Extracts formatting rules using Google Gemini (Free Tier).
    Implements retries and validation against JROSchema.
    """

    def __init__(self):
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        self.model = genai.GenerativeModel("gemini-2.0-flash")
        self.curr_dir = Path(__file__).parent
        self.system_prompt = (self.curr_dir / "prompts" / "system_prompt.txt").read_text(encoding="utf-8")
        self.few_shot_examples = json.loads((self.curr_dir / "prompts" / "few_shot_examples.json").read_text(encoding="utf-8"))

    async def extract(self, page_text: str, journal_name: str) -> JROSchema:
        """
        Extract rules from guidelines text.
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
                    full_prompt += f"\n\nPrevious attempt failed validation with error: {last_error}. Please fix the JSON and try again."
                
                response = await self.model.generate_content_async(full_prompt)
                
                raw_content = response.text
                json_str = self._clean_json_string(raw_content)
                data = json.loads(json_str)
                data["journal_name"] = journal_name
                
                return JROSchema.model_validate(data)
                
            except Exception as e:
                retries += 1
                last_error = str(e)
                logger.warning("Extraction attempt %d failed for %s: %s", retries, journal_name, last_error)
                if retries <= max_retries:
                    import asyncio
                    await asyncio.sleep(2 * retries)
        
        return self._make_partial_jro(journal_name)

    def _build_user_prompt(self, page_text: str, journal_name: str) -> str:
        """Construct the user prompt with few-shot examples and schema requirements."""
        prompt_parts = [
            f"Extract formatting rules for {journal_name} from the following text:\n\n{page_text}\n",
            "\nFollow these examples for structure:"
        ]
        for ex in self.few_shot_examples:
            prompt_parts.append(f"INPUT: {ex['input']}")
            prompt_parts.append(f"OUTPUT: {json.dumps(ex['expected_output'])}")
            
        prompt_parts.append(f"\nReturn ONLY valid JSON matching this schema: {JROSchema.model_json_schema()}")
        return "\n".join(prompt_parts)

    def _clean_json_string(self, content: str) -> str:
        """Extract JSON from potential markdown fences or extra text."""
        if "```json" in content:
            match = re.search(r"```json\n(.*?)\n```", content, re.DOTALL)
            if match:
                return match.group(1).strip()
        elif "```" in content:
            match = re.search(r"```(.*?)\n```", content, re.DOTALL)
            if match:
                return match.group(1).strip()
        return content.strip()

    def _make_partial_jro(self, journal_name: str) -> JROSchema:
        """Create a JRO with sensible defaults and low confidence."""
        return JROSchema(
            journal_name=journal_name,
            extraction_source="llm_partial",
            extraction_confidence=0.3,
            heading_rules={"levels": {}},
            abstract_rules={},
            layout_rules={},
            figure_rules={},
            table_rules={},
            section_requirements={}
        )
