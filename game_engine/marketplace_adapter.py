from __future__ import annotations
import csv, json, re, sys
from pathlib import Path
from typing import Any
from .engine import GameEngine
from .guards import PlayError
ROOT = Path(__file__).resolve().parent.parent
ALIASES = {
    "title": ("title", "item", "listing_title", "name"),
    "corridor": ("corridor", "trade_area", "area", "market"),
    "category": ("category", "cat", "tool_category"),
    "buy_price": ("buy_price", "price", "ask_price"),
    "comp_median": ("comp_median", "cell_median", "median_price", "comp"),
    "comp_count": ("comp_count", "sample_size", "comps", "n"),
}
def _pick(row: dict[str, Any], keys: tuple[str, ...]) -> Any:
    low = {k.strip().lower(): v for k, v in row.items()}
    for k in keys:
        if k in low and str(low[k]).strip() != "": return low[k]
    raise PlayError(f"Missing column for {keys[0]}")
def _num(val: Any) -> float:
    s = re.sub(r"[^0-9.\-]", "", str(val))
    if not s: raise PlayError(f"Invalid numeric value: {val}")
    return float(s)
def normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": str(_pick(row, ALIASES["title"])).strip(),
        "corridor": str(_pick(row, ALIASES["corridor"])).strip().lower().replace(" ", "_"),
        "category": str(_pick(row, ALIASES["category"])).strip().lower().replace(" ", "_"),
        "buy_price": _num(_pick(row, ALIASES["buy_price"])),
        "comp_median": _num(_pick(row, ALIASES["comp_median"])),
        "comp_count": int(_num(_pick(row, ALIASES["comp_count"]))),
    }
def ingest_rows(rows: list[dict[str, Any]], root: Path = ROOT, reset: bool = False) -> dict[str, Any]:
    eng = GameEngine(root / "packs" / "tool_databank.json", root)
    if reset: eng.reset()
    accepted, rejected = [], []
    for raw in rows:
        try:
            r = normalize_row(raw)
            eng.play("scout", "ingest_snapshot", r["title"], {"corridor": r["corridor"], "category": r["category"], "buy_price": r["buy_price"]})
            eng.play("analyst", "verify_comp", "Comp Check", {"comp_median": r["comp_median"], "comp_count": r["comp_count"]})
            sc = eng.play("analyst", "score_deal", "Score")
            rc = eng.play("auditor", "publish_receipt", "Seal")
            accepted.append({"title": r["title"], "corridor": r["corridor"], "tier": sc["metrics"]["signal_tier"], "margin_usd": sc["metrics"]["margin_usd"], "proof_hash": rc["proof_hash"]})
        except PlayError as exc:
            eng.state, eng.active = eng.pack["initial_state"], None; eng._save_state()
            rejected.append({"raw_title": str(raw.get("item") or raw.get("title") or "?"), "reason": str(exc)})
    return {"accepted": accepted, "rejected": rejected, "ledger": eng.ledger.verify()}
if __name__ == "__main__":
    p = Path(sys.argv[1])
    rows = json.loads(p.read_text(encoding="utf-8")) if p.suffix == ".json" else list(csv.DictReader(p.open(encoding="utf-8")))
    print(json.dumps(ingest_rows(rows, ROOT, "--reset" in sys.argv), indent=2))
