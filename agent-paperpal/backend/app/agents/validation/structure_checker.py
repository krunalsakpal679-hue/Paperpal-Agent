# backend/app/agents/validation/structure_checker.py
"""
StructureChecker: Validates document structural requirements (headings, sections, abstract).
"""

import logging
from typing import List

from app.schemas.ir import IRSchema, ElementType
from app.schemas.jro_schema import JROSchema
from app.schemas.job_state import ComplianceItem

logger = logging.getLogger(__name__)

class StructureChecker:
    """Checks the structural integrity of the document against JRO rules."""

    def check(self, ir: IRSchema, jro: JROSchema) -> List[ComplianceItem]:
        """
        Check for missing required sections, heading jumps, and abstract.
        """
        issues = []
        
        # 1. Check required sections
        if jro.section_requirements and jro.section_requirements.required:
            # Flatten all heading text for easier lookup
            headings = [el.raw_text.lower() for el in ir.elements if el.element_type == ElementType.HEADING]
            
            for required_section in jro.section_requirements.required:
                found = False
                for h_text in headings:
                    if required_section.lower() in h_text:
                        found = True
                        break
                
                if not found:
                    issues.append(ComplianceItem(
                        passed=False,
                        severity="error",
                        description=f"Required section missing: {required_section}",
                        rule_ref="Journal structural requirements",
                        suggestion=f"Ensure the manuscript contains a section titled '{required_section}'."
                    ))

        # 2. Check heading hierarchy
        heading_elements = [el for el in ir.elements if el.element_type == ElementType.HEADING and el.level is not None]
        last_level = 0
        for h in heading_elements:
            current_level = h.level
            if current_level > last_level + 1:
                issues.append(ComplianceItem(
                    passed=False,
                    severity="warning",
                    description=f"Heading level jump detected: Level {last_level} followed by Level {current_level} ('{h.raw_text}')",
                    rule_ref="Heading hierarchy standard",
                    suggestion="Ensure headings follow a logical nested order (e.g., Level 1 followed by Level 2)."
                ))
            last_level = current_level

        # 3. Check abstract presence if required
        if jro.abstract_rules:
            abstract_elements = [el for el in ir.elements if el.element_type == ElementType.ABSTRACT]
            if not abstract_elements:
                issues.append(ComplianceItem(
                    passed=False,
                    severity="error",
                    description="Abstract is missing",
                    rule_ref="Abstract requirement",
                    suggestion="Provide an abstract as required by the journal guidelines."
                ))

        return issues
