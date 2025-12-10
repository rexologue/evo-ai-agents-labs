"""#B8;8BK 4;O MCP 8=AB@C<5=B>2."""

import json
import os
from dataclasses import dataclass
from typing import Any

from mcp.shared.exceptions import ErrorData, McpError
from mcp.types import TextContent


@dataclass
class ToolResult:
    """#=8D8F8@>20==0O AB@C:BC@0 @57C;LB0B0 4;O MCP 8=AB@C<5=B>2."""

    content: list[TextContent]  # '5;>25:>-G8B05<K9 B5:AB 4;O LLM
    structured_content: (
        dict[str, Any] | list[dict[str, Any]]
    )  # !K@K5 40==K5 API
    meta: dict[str, Any]  # 5B040==K5 2K?>;=5=8O (?0@0<5B@K, AG5BG8:8)


def _require_env_vars(vars: list[str]) -> dict[str, str]:
    """
    @>25@:0 8 ?>;CG5=85 ?5@5<5==KE >:@C65=8O.

    Args:
        vars: !?8A>: 8<5= ?5@5<5==KE >:@C65=8O

    Returns:
        !;>20@L ?5@5<5==KE >:@C65=8O

    Raises:
        McpError: A;8 :0:0O-;81> ?5@5<5==0O >BACBAB2C5B
    """
    missing = [v for v in vars if not os.getenv(v)]
    if missing:
        raise McpError(
            ErrorData(
                code=-32603,
                message=f"Missing environment variables: {', '.join(missing)}",
            )
        )
    return {v: os.getenv(v) for v in vars}  # type: ignore


def format_api_error(text: str, code: int) -> str:
    """
    $>@<0B8@>20=85 >H81:8 API 4;O >B>1@065=8O ?>;L7>20B5;N.

    Args:
        text: "5:AB >B25B0 API
        code: HTTP :>4 >B25B0

    Returns:
        BD>@<0B8@>20==>5 A>>1I5=85 >1 >H81:5
    """
    if code == 404:
        return ">:C<5=B =5 =0945="
    elif code == 422:
        # 0@A8=3 >H81>: 20;840F88 Pydantic
        try:
            error_data = json.loads(text)
            detail = error_data.get("detail", [])
            if isinstance(detail, list):
                messages = []
                for err in detail:
                    loc = ".".join(str(x) for x in err.get("loc", []))
                    msg = err.get("msg", "Unknown error")
                    messages.append(f"{loc}: {msg}")
                return "H81:8 20;840F88:\n  - " + "\n  - ".join(messages)
        except Exception:
            pass
    return f"HTTP {code}: {text[:200]}"


def format_purchase_summary(purchase: dict[str, Any]) -> str:
    """
    $>@<0B8@>20=85 :@0B:>9 8=D>@<0F88 > 70:C?:5.

    Args:
        purchase: !;>20@L A 40==K<8 70:C?:8

    Returns:
        BD>@<0B8@>20==K9 B5:AB
    """
    stage_map = {
        1: ">40G0 70O2>:",
        2: " 01>B0 :><8AA88",
        3: "0:C?:0 7025@H5=0",
        4: "0:C?:0 >B<5=5=0",
    }

    okpd2_codes = ", ".join(purchase.get("okpd2") or [])
    close_at = purchase.get("submission_close_at")
    close_at_str = close_at if close_at else "=5 C:070=>"

    max_price = purchase.get("max_price", 0)
    max_price_str = f"{max_price:,.2f}" if max_price else "=5 C:070=>"

    return f"""---
><5@ 70:C?:8: {purchase['purchase_number']}
0:07G8: (): {purchase['customer']}
@54<5B: {purchase['object_info']}
0:A8<0;L=0O F5=0: {max_price_str} {purchase['currency_code']}
:>=G0=85 ?>40G8 70O2>:: {close_at_str}
-B0?: {stage_map.get(purchase['stage'], '=58725AB=>')}
 538>=: {purchase['region']}
2: {okpd2_codes or '=5 C:070=>'}
---"""


def format_purchase_list(purchases: list[dict[str, Any]], total: int) -> str:
    """
    $>@<0B8@>20=85 A?8A:0 70:C?>:.

    Args:
        purchases: !?8A>: 70:C?>:
        total: 1I55 :>;8G5AB2> =0945==KE 70:C?>:

    Returns:
        BD>@<0B8@>20==K9 B5:AB
    """
    header = f"0945=> 70:C?>:: {total}\n>:070=>: {len(purchases)}\n\n"
    summaries = [format_purchase_summary(p) for p in purchases]
    return header + "\n\n".join(summaries)


def format_purchase_details(purchase: dict[str, Any]) -> str:
    """
    $>@<0B8@>20=85 45B0;L=>9 8=D>@<0F88 > 70:C?:5 A 4>:C<5=B0<8.

    Args:
        purchase: !;>20@L A 40==K<8 70:C?:8

    Returns:
        BD>@<0B8@>20==K9 B5:AB
    """
    text = format_purchase_summary(purchase)

    # >102;O5< <5AB0 ?>AB02:8
    if purchase.get("delivery_places"):
        text += "\n\n5AB0 ?>AB02:8:\n"
        for place in purchase["delivery_places"]:
            text += f"  - {place}\n"

    # >102;O5< 4>:C<5=BK
    docs = purchase.get("docs", [])
    text += f"\n\n>:C<5=BK 70:C?:8 ({len(docs)}):\n"
    for doc in docs:
        text += f"  - {doc['doc_type']} (>?C1;8:>20=>: {doc['published_at']})\n"

    # >102;O5< A2O70==K5 ?;0=K
    if purchase.get("plan_numbers"):
        text += (
            f"\n\n!2O70==K5 ?;0=K 70:C?>:: {', '.join(purchase['plan_numbers'])}\n"
        )

    return text
