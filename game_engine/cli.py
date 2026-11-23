from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from .engine import GameEngine
ROOT = Path(__file__).resolve().parent.parent
def _eng(pack: str) -> GameEngine:
    p = ROOT / "packs" / f"{pack}.json"
    if not p.exists(): raise SystemExit(f"Unknown pack: {pack}")
    return GameEngine(p, ROOT)
def main() -> None:
    ap = argparse.ArgumentParser(prog="game_engine")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("packs")
    for c in ("status", "verify", "reset"):
        p = sub.add_parser(c); p.add_argument("--pack", required=True)
    pl = sub.add_parser("play")
    pl.add_argument("--pack", required=True); pl.add_argument("--seat", required=True); pl.add_argument("--card", required=True)
    pl.add_argument("--title", default=""); pl.add_argument("--payload", default="{}"); pl.add_argument("--votes", default="{}")
    a = ap.parse_args()
    if a.cmd == "packs":
        print(json.dumps(sorted(p.stem for p in (ROOT / "packs").glob("*.json")), indent=2)); return
    e = _eng(a.pack)
    if a.cmd == "reset": e.reset(); print(json.dumps({"reset": a.pack, "state": e.state})); return
    if a.cmd == "status":
        print(json.dumps({"pack": e.pack_id, "state": e.state, "active": e.active, "valid": {s: e.valid_cards(s) for s in e.pack["seats"]}}, indent=2)); return
    if a.cmd == "verify":
        res = e.ledger.verify(); print(json.dumps({"pack": e.pack_id, **res}, indent=2)); sys.exit(0 if res["ok"] else 1)
    if a.cmd == "play":
        rec = e.play(a.seat, a.card, a.title, json.loads(a.payload), json.loads(a.votes))
        print(json.dumps(rec, indent=2))
