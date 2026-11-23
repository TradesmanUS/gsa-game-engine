from __future__ import annotations
import argparse, json, os, subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from .engine import GameEngine
from .guards import PlayError
from .proof import canonical_sha256
ROOT = Path(__file__).resolve().parent.parent
def build_anchor(pack: str, root: Path = ROOT) -> dict[str, Any]:
    eng = GameEngine(root / "packs" / f"{pack}.json", root)
    ver = eng.ledger.verify()
    if not ver["ok"] or ver["count"] == 0:
        raise PlayError(f"Refusing to anchor invalid or empty ledger for {pack}")
    body = {"pack_id": eng.pack_id, "count": ver["count"], "tip": ver["tip"], "anchored_at": datetime.now(timezone.utc).isoformat()}
    return {**body, "anchor_sha256": canonical_sha256(body)}
def anchor_pack(pack: str, execute: bool = False, root: Path = ROOT) -> dict[str, Any]:
    rec = build_anchor(pack, root)
    adi = os.environ.get("GSA_ANCHOR_ADI", "")
    cli = os.environ.get("GSA_ACCUMULATE_BIN", "")
    if not execute:
        return {"mode": "dry_run", "target_adi": adi or "unset", "anchor": rec}
    if not adi or not cli:
        raise PlayError("Set GSA_ANCHOR_ADI and GSA_ACCUMULATE_BIN to execute live anchor")
    cmd = [cli, "data", "write", adi, json.dumps(rec, sort_keys=True)]
    cp = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if cp.returncode != 0:
        raise PlayError(f"Anchor command failed ({cp.returncode}): {cp.stderr.strip()}")
    return {"mode": "executed", "target_adi": adi, "anchor": rec, "stdout": cp.stdout.strip()}
if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--pack", required=True); ap.add_argument("--execute", action="store_true"); a = ap.parse_args()
    print(json.dumps(anchor_pack(a.pack, a.execute), indent=2))
