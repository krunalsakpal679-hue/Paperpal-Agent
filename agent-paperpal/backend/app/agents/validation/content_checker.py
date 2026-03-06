# backend/app/agents/validation/content_checker.py
"""
ContentChecker: Validates specific content rules (word counts, numbering, notation).
"""

import logging
import re
from typing import List, Any

from app.schemas.ir import IRSchema, ElementType
from app.schemas.jro_schema import JROSchema
from app.schemas.job_state import ComplianceItem

logger = logging.getLogger(__name__)

class ContentChecker:
    """Checks content-level compliance such as word counts and numbering sequences."""

    def check(self, ir: IRSchema, jro: JROSchema) -> List[ComplianceItem]:
        """
        Check abstract word count, figure/table numbering, and statistical notation.
        """
        issues = []
        
        # 1. Abstract word count
        if jro.abstract_rules and jro.abstract_rules.max_words:
            abstract_elements = [el for el in ir.elements if el.element_type == ElementType.ABSTRACT]
            for abstract in abstract_elements:
                word_count = len(abstract.raw_text.split())
                if word_count > jro.abstract_rules.max_words:
                    issues.append(ComplianceItem(
                        passed=False,
                        severity="warning",
                        description=f"Abstract is {word_count} words; limit is {jro.abstract_rules.max_words} words",
                        rule_ref="Abstract length constraint",
                        suggestion=f"Shorten the abstract to stay within the {jro.abstract_rules.max_words} word limit."
                    ))

        # 2. Figure numbering
        figure_elements = [el for el in ir.elements if el.element_type == ElementType.FIGURE]
        self._check_sequence(figure_elements, "Figure", issues)

        # 3. Table numbering
        table_elements = [el for el in ir.elements if el.element_type == ElementType.TABLE]
        self._check_sequence(table_elements, "Table", issues)

        # 4. Statistical notation (basic check)
        # Check for common p-value format violations (e.g., p < 0.05 vs p=0.04)
        # This is a placeholder for more complex NLP checks
        body_text = " ".join([el.raw_text for el in ir.elements if el.element_type == ElementType.PARAGRAPH])
        if "p < ." in body_text:
             issues.append(ComplianceItem(
                passed=False,
                severity="warning",
                description="P-value missing leading zero (e.g., 'p < .05')",
                rule_ref="Statistical notation style",
                suggestion="Use a leading zero for p-values (e.g., 'p < 0.05')."
            ))

        return issues

    def _check_sequence(self, elements: List[Any], label: str, issues: List[ComplianceItem]):
        """Helper to check for gaps in figure/table numbering."""
        numbers = []
        for el in elements:
            # Try to extract number from raw_text or metadata
            text = el.raw_text
            match = re.search(rf"{label}\s*(\d+)", text, re.I)
            if match:
                numbers.append(int(match.group(1)))
        
        if not numbers:
            return

        # Check for gaps or departures from 1,2,3...
        expected = 1
        sorted_numbers = sorted(numbers)
        for num in sorted_numbers:
            if num != expected:
                issues.append(ComplianceItem(
                    passed=False,
                    severity="warning",
                    description=f"{label} numbering gap or sequence error: found {num} when expecting {expected}",
                    rule_ref=f"{label} sequencing",
                    suggestion=f"Renumber your {label.lower()}s to ensure a continuous sequence starting from 1."
                ))
                expected = num # Reset to found to catch next gap
            expected += 1
