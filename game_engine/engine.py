from __future__ import annotations
import json, uuid
from pathlib import Path
from typing import Any
from .guards import PlayError, check_guards, score_tool_deal, tally_votes
from .proof import ProofLedger
class GameEngine:
    def __init__(self, pack_path: Path, root: Path | None = None) -> None:
        self.root = root or Path(__file__).resolve().parent.parent
        self.pack = json.loads(pack_path.read_text(encoding="utf-8"))
        self.pack_id = self.pack["pack_id"]
        self.state_path = self.root / "state" / f"{self.pack_id}.json"
        self.ledger = ProofLedger(self.root / "logs" / f"{self.pack_id}_ledger.jsonl")
        self.state = self.pack["initial_state"]
        self.active: dict[str, Any] | None = None
        self.tabled: list[dict[str, Any]] = []
        self._load_state()
    def _load_state(self) -> None:
        if self.state_path.exists():
            snap = json.loads(self.state_path.read_text(encoding="utf-8"))
            self.state, self.active, self.tabled = snap["state"], snap.get("active"), snap.get("tabled", [])
    def _save_state(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps({"pack_id": self.pack_id, "state": self.state, "active": self.active, "tabled": self.tabled}, indent=2), encoding="utf-8")
    def reset(self) -> None:
        self.state, self.active, self.tabled = self.pack["initial_state"], None, []
        if self.state_path.exists(): self.state_path.unlink()
        if self.ledger.path.exists(): self.ledger.path.unlink()
    def valid_cards(self, seat: str) -> list[str]:
        return [cid for cid, s in self.pack["cards"].items() if seat in s["allowed_seats"] and ("*" in s["from_states"] or self.state in s["from_states"])]
    def play(self, seat: str, card_id: str, title: str = "", payload: dict[str, Any] | None = None, votes: dict[str, str] | None = None) -> dict[str, Any]:
        if seat not in self.pack["seats"]: raise PlayError(f"Unknown seat: {seat}")
        spec = self.pack["cards"].get(card_id)
        if not spec: raise PlayError(f"Unknown card: {card_id}")
        if seat not in spec["allowed_seats"]: raise PlayError(f"Seat {seat} cannot play {card_id}")
        if "*" not in spec["from_states"] and self.state not in spec["from_states"]:
            raise PlayError(f"Card {card_id} invalid in state {self.state}")
        data = dict(payload or {})
        merged = {**(self.active.get("payload", {}) if self.active else {}), **data}
        check_guards(spec.get("guards", {}), seat, self.active, merged)
        eff, extra = spec.get("effect", "noop"), {}
        if eff == "open_item":
            self.active = {"item_id": f"itm_{uuid.uuid4().hex[:8]}", "seat": seat, "title": title or card_id, "payload": data, "amendments": []}
        elif eff == "merge_payload" and self.active:
            self.active["payload"].update(data)
        elif eff == "append_amendment" and self.active:
            self.active["amendments"].append({"id": f"amd_{uuid.uuid4().hex[:8]}", "seat": seat, "title": title or card_id, "payload": data})
        elif eff == "score_tool_deal":
            if self.active: self.active["payload"].update(data)
            extra["metrics"] = score_tool_deal(merged)
            if self.active: self.active["metrics"] = extra["metrics"]
        elif eff == "resolve_vote":
            extra["vote_result"] = tally_votes(votes); extra["closed_item"] = self.active; self.active = None
        elif eff == "table_item" and self.active:
            self.tabled.append(self.active); extra["tabled_count"] = len(self.tabled); self.active = None
        elif eff == "close_item":
            extra["closed_item"] = self.active; self.active = None
        if spec.get("to_state") and spec["to_state"] != "KEEP": self.state = spec["to_state"]
        self._save_state()
        return self.ledger.append({"pack_id": self.pack_id, "card": card_id, "seat": seat, "title": title or card_id, "state": self.state, "active_id": self.active["item_id"] if self.active else None, "payload": data, **extra})
