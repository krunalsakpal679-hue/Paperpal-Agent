# backend/app/agents/validation/compliance_scorer.py
"""
ComplianceScorer: Calculates category-weighted compliance scores based on detected issues.
"""

from typing import List, Dict
from app.schemas.ir import IRSchema, ElementType
from app.schemas.job_state import ComplianceItem

class ComplianceScorer:
    """Calculates granular and overall compliance scores."""

    def __init__(self):
        self.weights = {
            "citations": 0.30,
            "references": 0.25,
            "headings": 0.20,
            "abstract": 0.15,
            "structure": 0.10
        }

    def score(self, issues: List[ComplianceItem], ir: IRSchema) -> Dict[str, float]:
        """
        Calculates scores for each category and a final weighted overall score.
        Scores are in range [0.0, 1.0].
        """
        # Count errors per category (warnings count less)
        counts = {cat: 0.0 for cat in self.weights.keys()}
        for issue in issues:
            penalty = 1.0 if issue.severity == "error" else 0.5
            
            ref = issue.rule_ref.lower()
            if "citation" in ref:
                counts["citations"] += penalty
            elif "reference" in ref:
                counts["references"] += penalty
            elif "heading" in ref:
                counts["headings"] += penalty
            elif "abstract" in ref:
                counts["abstract"] += penalty
            else:
                counts["structure"] += penalty

        # Denominators per category
        total_elements = {
            "citations": len(ir.metadata.get("citations_parsed", [])),
            "references": len(ir.metadata.get("references_parsed", [])),
            "headings": len([el for el in ir.elements if el.element_type == ElementType.HEADING]),
            "abstract": len([el for el in ir.elements if el.element_type == ElementType.ABSTRACT]),
            "structure": len(ir.elements) / 10.0 # Heuristic for general structure
        }

        category_scores = {}
        for cat in self.weights.keys():
            total = total_elements.get(cat, 1.0)
            if total == 0:
                total = 1.0 # Avoid division by zero, empty list means perfect compliance for what is there
            
            # score = 1.0 - (weighted_errors / total)
            score = 1.0 - (counts[cat] / max(total, 1.0))
            category_scores[cat] = max(0.0, min(1.0, score))

        # Overall weighted score
        overall = sum(category_scores[cat] * self.weights[cat] for cat in self.weights.keys())
        category_scores["overall"] = max(0.0, min(1.0, overall))

        return category_scores
