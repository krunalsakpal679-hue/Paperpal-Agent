# backend/app/agents/transformation/transformer_base.py
"""
BaseTransformer: Abstract base class for all IR transformation modules.
Provides a shared interface and a change recording mechanism.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List

from app.schemas.job_state import ChangeEntry
from app.schemas.jro_schema import JROSchema
from app.schemas.ir import IRSchema, IRElement

class BaseTransformer(ABC):
    """
    Abstract base class for IR transformers.
    
    Each transformer focuses on a specific aspect of document formatting
    (e.g., Citations, Headings, Layout).
    """

    def __init__(self, jro: JROSchema, change_log: List[ChangeEntry]):
        self.jro = jro
        self.change_log = change_log

    def record_change(
        self, 
        element_id: str, 
        field: str, 
        old_value: str, 
        new_value: str, 
        rule_source: str
    ):
        """
        Record a formatting change in the shared change log.
        Only records if values actually changed.
        """
        if str(old_value) != str(new_value):
            entry = ChangeEntry(
                element_id=element_id,
                field=field,
                old_value=str(old_value),
                new_value=str(new_value),
                rule_source=rule_source
            )
            self.change_log.append(entry)

    @abstractmethod
    def transform(self, ir: IRSchema) -> IRSchema:
        """
        Apply transformation rules to the complete IR.
        """
        pass
