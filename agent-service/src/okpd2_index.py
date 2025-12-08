from __future__ import annotations

import csv
from pathlib import Path
from typing import List

from .models import Okpd2Item

DATA_PATH = Path(__file__).parent / "data" / "okpd2.csv"


def load_okpd2_index() -> List[Okpd2Item]:
    items: List[Okpd2Item] = []
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Не найден okpd2.csv по пути {DATA_PATH}")
    with DATA_PATH.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row.get("code"):
                continue
            items.append(Okpd2Item(code=row["code"].strip(), title=row.get("category", "").strip()))
    return items


OKPD2_INDEX = load_okpd2_index()
