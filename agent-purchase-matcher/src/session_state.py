"""Состояние сессии для агента подбора закупок."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PurchaseMatcherState:
    company_profile: Optional[Dict[str, Any]] = None
    company_id: Optional[str] = None
    company_name: Optional[str] = None
    greeted: bool = False
    query_description: Optional[str] = None
    applications_end_before: Optional[str] = None
    regions_override: Optional[List[str]] = None
    law_preference: Optional[str] = None
    price_notes: Optional[str] = None
    preferences_prompted: bool = False
    purchase_numbers: List[str] = field(default_factory=list)
    purchase_details: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    purchase_descriptions: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    purchase_scores: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def reset(self) -> None:
        self.company_profile = None
        self.company_id = None
        self.company_name = None
        self.greeted = False
        self.query_description = None
        self.applications_end_before = None
        self.regions_override = None
        self.law_preference = None
        self.price_notes = None
        self.preferences_prompted = False
        self.purchase_numbers.clear()
        self.purchase_details.clear()
        self.purchase_descriptions.clear()
        self.purchase_scores.clear()
