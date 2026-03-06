# backend/app/agents/validation/citation_checker.py
"""
CitationConsistencyChecker: Verifies that all in-text citations have matching references and vice versa.
"""

import logging
import re
from typing import List, Tuple, Set, Dict, Any

from app.schemas.ir import IRSchema
from app.schemas.job_state import ComplianceItem

logger = logging.getLogger(__name__)

class CitationConsistencyChecker:
    """Checks for consistency between in-text citations and the reference list."""

    def _normalize_key(self, author: str, year: str) -> str:
        """Create a normalized key: lastname_year."""
        # Clean author name (take last word as last name if simple string)
        last_name = ""
        if author:
            # Handle "Last, First" or "First Last"
            if "," in author:
                last_name = author.split(",")[0].strip()
            else:
                last_name = author.split()[-1].strip()
        
        # Clean year (strip non-digits)
        year_clean = "".join(re.findall(r"\d+", str(year)))
        
        return f"{last_name.lower()}_{year_clean}"

    def check(self, ir: IRSchema) -> Tuple[List[ComplianceItem], float]:
        """
        Check for unmatched citations and uncited references.
        Returns (list of issues, citation coverage float).
        """
        issues = []
        
        citations_parsed = ir.metadata.get("citations_parsed", [])
        references_parsed = ir.metadata.get("references_parsed", [])
        
        # 1. Build citation keys
        citation_keys: Set[str] = set()
        for cit in citations_parsed:
            ref_ids = cit.get("ref_ids", [])
            for rid in ref_ids:
                # Find matching ref in references_parsed to get author/year if available
                matching_ref = next((r for r in references_parsed if r.get("id") == rid), None)
                if matching_ref:
                    # Prefer normalized key from reference data
                    authors = matching_ref.get("authors", [])
                    year = matching_ref.get("year", "")
                    if authors:
                        citation_keys.add(self._normalize_key(authors[0], year))
                    else:
                        citation_keys.add(rid) # Fallback to ID
                else:
                    citation_keys.add(rid) # Fallback to ID
                    
        # 2. Build reference keys
        reference_keys: Set[str] = set()
        ref_id_to_key: Dict[str, str] = {}
        for ref in references_parsed:
            authors = ref.get("authors", [])
            year = ref.get("year", "")
            key = self._normalize_key(authors[0], year) if authors else ref.get("id")
            reference_keys.add(key)
            ref_id_to_key[ref.get("id")] = key

        # 3. Unmatched citations (Citations pointing to missing references)
        # Re-check citations using raw_text or ref_ids
        unmatched_count = 0
        for cit in citations_parsed:
            ref_ids = cit.get("ref_ids", [])
            for rid in ref_ids:
                if rid not in [r.get("id") for r in references_parsed]:
                    unmatched_count += 1
                    issues.append(ComplianceItem(
                        passed=False,
                        severity="error",
                        description=f"In-text citation '{cit.get('raw_text')}' has no matching reference entry (ID: {rid})",
                        rule_ref="Citation traceability requirement",
                        suggestion=f"Add a reference entry for this citation to the bibliography."
                    ))

        # 4. Uncited references (References not mentioned in text)
        cited_ref_ids = set()
        for cit in citations_parsed:
            for rid in cit.get("ref_ids", []):
                cited_ref_ids.add(rid)
                
        for ref in references_parsed:
            if ref.get("id") not in cited_ref_ids:
                authors = ref.get("authors", [])
                author_str = authors[0] if authors else "Unknown"
                issues.append(ComplianceItem(
                    passed=False,
                    severity="warning",
                    description=f"Reference entry '{author_str} ({ref.get('year')})' is not cited in the text",
                    rule_ref="Citation completeness",
                    suggestion="Cite this reference in the body text or remove it from the reference list."
                ))

        # Coverage: matched / total_citations
        total_citations = len(citations_parsed)
        if total_citations == 0:
            coverage = 1.0
        else:
            # coverage = (total - unmatched) / total
            # But here unmatched_count is per ref_id in citation. 
            # Let's simplify: percentage of citations that have at least one valid reference
            valid_citations = 0
            for cit in citations_parsed:
                if any(rid in [r.get("id") for r in references_parsed] for rid in cit.get("ref_ids", [])):
                    valid_citations += 1
            coverage = valid_citations / total_citations

        return issues, coverage
