from __future__ import annotations
from typing import Any
class PlayError(ValueError):
    pass
def check_guards(guards: dict[str, Any], seat: str, active: dict[str, Any] | None, payload: dict[str, Any]) -> None:
    if guards.get("forbids_active") and active is not None:
        raise PlayError("Active item already on floor")
    if guards.get("requires_active") and active is None:
        raise PlayError("Requires an active item")
    if guards.get("distinct_from_proposer") and active and seat == active.get("seat"):
        raise PlayError("Seat cannot self-approve or self-second own item")
    for key in guards.get("required_keys", []):
        if key not in payload or payload[key] in (None, ""):
            raise PlayError(f"Missing required payload key: {key}")
    for key, lo in guards.get("min_values", {}).items():
        val = payload.get(key)
        if not isinstance(val, (int, float)) or val < lo:
            raise PlayError(f"Payload {key} must be >= {lo}")
def score_tool_deal(payload: dict[str, Any]) -> dict[str, Any]:
    buy = float(payload["buy_price"])
    comp = float(payload["comp_median"])
    fees = float(payload.get("fees_usd", round(comp * 0.10, 2)))
    margin = round(comp - buy - fees, 2)
    discount_pct = round(((comp - buy) / comp) * 100, 2) if comp > 0 else 0.0
    roi_pct = round((margin / buy) * 100, 2) if buy > 0 else 0.0
    tier = "A_BUY" if discount_pct >= 35 and margin >= 25 else ("B_WATCH" if discount_pct >= 20 else "C_PASS")
    return {"buy_price": buy, "comp_median": comp, "fees_usd": fees, "margin_usd": margin, "discount_pct": discount_pct, "roi_pct": roi_pct, "signal_tier": tier}
def tally_votes(votes: dict[str, str] | None) -> dict[str, Any]:
    tally = {k: str(v).upper() for k, v in (votes or {}).items()}
    approves = sum(1 for v in tally.values() if v == "APPROVE")
    rejects = sum(1 for v in tally.values() if v == "REJECT")
    return {"votes": tally, "approves": approves, "rejects": rejects, "passed": approves > 0 and approves > rejects}
