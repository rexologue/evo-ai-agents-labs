"""Общие утилиты для MCP инструментов codes-mcp."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import List, Any
from dataclasses import dataclass, field

from mcp.types import Content

from models import Okpd2Item, RegionItem

ODKP2_PATH = Path(__file__).parent.parent / "okpd2.csv"
REGIONS_PATH = Path(__file__).parent.parent / "regions.csv"

def load_okpd2_index() -> List[Okpd2Item]:
    items: List[Okpd2Item] = []
    if not ODKP2_PATH.exists():
        raise FileNotFoundError(f"Не найден okpd2.csv по пути {ODKP2_PATH}")
    
    with ODKP2_PATH.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            if not row.get("code"):
                continue
            
            items.append(Okpd2Item(code=row["code"].strip(), title=row.get("category", "").strip()))
            
    return items

def load_region_index() -> List[RegionItem]:
    items: List[RegionItem] = []
    if not REGIONS_PATH.exists():
        raise FileNotFoundError(f"Не найден regions.csv по пути {REGIONS_PATH}")
    
    with REGIONS_PATH.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            if not row.get("code"):
                continue
            
            items.append(RegionItem(code=row["code"].strip(), title=row.get("region", "").strip()))
            
    return items


OKPD2_INDEX = load_okpd2_index()
REGION_INDEX = load_region_index()


def format_okpd2_index() -> str:
    pretty_okpd2 = "Таблица кодов экономической деятельности и соответсвующих им наименований по ОКПД2\n"
    
    for item in OKPD2_INDEX:
        pretty_okpd2 += f"{item.code} - {item.title}\n"
        
    return pretty_okpd2[:-1]


def format_region_index() -> str:
    pretty_regions = "Таблица кодов регионов и соответсвующих им названий\n"
    
    for item in REGION_INDEX:
        pretty_regions += f"{item.code} - {item.title}\n"
        
    return pretty_regions[:-1]


@dataclass
class ToolResult:
    """Стандартный ответ MCP инструмента."""
    content: list[Content]
    structured_content: dict[str, Any] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)
    