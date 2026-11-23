from __future__ import annotations
import csv, json, sys
from pathlib import Path
from .engine import GameEngine
from .guards import PlayError
ROOT = Path(__file__).resolve().parent.parent
def ingest_file(src: Path, reset: bool = False) -> dict:
    eng = GameEngine(ROOT / "packs" / "tool_databank.json", ROOT)
    if reset: eng.reset()
    rows = json.loads(src.read_text(encoding="utf-8")) if src.suffix == ".json" else list(csv.DictReader(src.open(encoding="utf-8")))
    accepted, rejected = [], []
    for r in rows:
        try:
            eng.play("scout", "ingest_snapshot", r["title"], {"corridor": r["corridor"], "category": r["category"], "buy_price": float(r["buy_price"])})
            eng.play("analyst", "verify_comp", "Comp Check", {"comp_median": float(r["comp_median"]), "comp_count": int(r["comp_count"])})
            sc = eng.play("analyst", "score_deal", "Score")
            rc = eng.play("auditor", "publish_receipt", "Seal")
            accepted.append({"title": r["title"], "tier": sc["metrics"]["signal_tier"], "margin_usd": sc["metrics"]["margin_usd"], "proof_hash": rc["proof_hash"]})
        except PlayError as exc:
            eng.state, eng.active = eng.pack["initial_state"], None; eng._save_state()
            rejected.append({"title": r.get("title", "?"), "reason": str(exc)})
    return {"accepted": accepted, "rejected": rejected, "ledger": eng.ledger.verify()}
if __name__ == "__main__":
    print(json.dumps(ingest_file(Path(sys.argv[1]), "--reset" in sys.argv), indent=2))
