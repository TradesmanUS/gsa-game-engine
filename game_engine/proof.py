from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
GENESIS_HASH = "0" * 64
def canonical_sha256(obj: dict[str, Any]) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()
class ProofLedger:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
    def last_hash(self) -> str:
        if not self.path.exists():
            return GENESIS_HASH
        lines = [ln for ln in self.path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        return json.loads(lines[-1])["proof_hash"] if lines else GENESIS_HASH
    def append(self, event: dict[str, Any]) -> dict[str, Any]:
        body = {"timestamp": datetime.now(timezone.utc).isoformat(), "prev_hash": self.last_hash(), **event}
        rec = {**body, "proof_hash": canonical_sha256(body)}
        with self.path.open("a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(rec, sort_keys=True) + "\n")
        return rec
    def verify(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"ok": True, "count": 0, "tip": GENESIS_HASH}
        prev, count = GENESIS_HASH, 0
        for idx, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            rec = json.loads(line)
            claimed = rec.get("proof_hash")
            body = {k: v for k, v in rec.items() if k != "proof_hash"}
            if rec.get("prev_hash") != prev or canonical_sha256(body) != claimed:
                return {"ok": False, "failed_line": idx, "count": count, "tip": prev}
            prev, count = claimed, count + 1
        return {"ok": True, "count": count, "tip": prev}
