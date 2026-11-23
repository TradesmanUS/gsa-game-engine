from __future__ import annotations
import argparse, json, os, subprocess, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse
from .engine import GameEngine
from .guards import PlayError
from .proof import canonical_sha256

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_NETWORK = "https://kermit.accumulatenetwork.io/v2"
SAFE_HOSTS = ("kermit", "testnet", "devnet", "localhost", "127.0.0.1")

def validate_anchor_target(network: str, wallet: str, allow_mainnet: bool = False) -> tuple[str, str]:
    host = (urlparse(network).hostname or "").lower()
    if not host or (not allow_mainnet and not any(h in host for h in SAFE_HOSTS)):
        raise PlayError(f"Refusing non-testnet endpoint without GSA_ALLOW_MAINNET=1: {network}")
    w = wallet.strip()
    if not w:
        raise PlayError("Refusing live anchor without explicit isolated GSA_ANCHOR_WALLET")
    norm_w = w.replace("\\", "/").rstrip("/").lower()
    if not allow_mainnet and (norm_w == ".accumulate" or norm_w.endswith("/.accumulate")):
        raise PlayError("Refusing default .accumulate wallet without GSA_ALLOW_MAINNET=1")
    return network, w

def build_anchor(pack: str, root: Path = ROOT) -> dict[str, Any]:
    eng = GameEngine(root / "packs" / f"{pack}.json", root)
    ver = eng.ledger.verify()
    if not ver["ok"] or ver["count"] == 0:
        raise PlayError(f"Refusing to anchor invalid or empty ledger for {pack}")
    body = {"pack_id": eng.pack_id, "count": ver["count"], "tip": ver["tip"], "anchored_at": datetime.now(timezone.utc).isoformat()}
    return {**body, "anchor_sha256": canonical_sha256(body)}

def anchor_pack(pack: str, execute: bool = False, root: Path = ROOT) -> dict[str, Any]:
    rec = build_anchor(pack, root)
    adi, cli = os.environ.get("GSA_ANCHOR_ADI", ""), os.environ.get("GSA_ACCUMULATE_BIN", "")
    net = os.environ.get("GSA_ANCHOR_NETWORK", DEFAULT_NETWORK)
    wallet = os.environ.get("GSA_ANCHOR_WALLET", "")
    allow_main = os.environ.get("GSA_ALLOW_MAINNET", "") == "1"
    if not execute:
        return {"mode": "dry_run", "network": net, "target_adi": adi or "unset", "anchor": rec}
    if not adi or not cli:
        raise PlayError("Set GSA_ANCHOR_ADI and GSA_ACCUMULATE_BIN to execute live anchor")
    net, wallet = validate_anchor_target(net, wallet, allow_main)
    signer = os.environ.get("GSA_ANCHOR_SIGNER", "").strip()
    cmd = [cli, "-s", net, "-w", wallet, "data", "write", adi] + ([signer] if signer else []) + [json.dumps(rec, sort_keys=True)]
    cp = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if cp.returncode != 0:
        raise PlayError(f"Anchor command failed ({cp.returncode}): {cp.stderr.strip()}")
    return {"mode": "executed", "network": net, "target_adi": adi, "anchor": rec, "stdout": cp.stdout.strip()}

def _rpc_query_tx(network: str, tx_hash: str) -> dict[str, Any]:
    req = urllib.request.Request(network, data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "query-tx", "params": {"txid": tx_hash}}).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))

def _extract_payload(resp: dict[str, Any]) -> dict[str, Any]:
    if resp.get("error"):
        raise PlayError(f"RPC error: {resp['error']}")
    res = resp.get("result", {})
    entries = res.get("transaction", {}).get("body", {}).get("entry", {}).get("data") or res.get("data", {}).get("entry", {}).get("data") or []
    for raw in entries:
        try: txt = bytes.fromhex(raw).decode("utf-8")
        except ValueError: txt = str(raw)
        try:
            obj = json.loads(txt)
            if isinstance(obj, dict) and "tip" in obj: return obj
        except json.JSONDecodeError: continue
    raise PlayError("No valid anchor JSON payload found in on-chain transaction")

def verify_anchor(pack: str, txid: str, network: str | None = None, root: Path = ROOT, rpc_fn: Callable[[str, str], dict[str, Any]] | None = None) -> dict[str, Any]:
    tx_hash = txid[6:].split("@", 1)[0] if txid.startswith("acc://") else txid.strip()
    if len(tx_hash) != 64 or any(c not in "0123456789abcdefABCDEF" for c in tx_hash):
        raise PlayError(f"Invalid 64-hex txid: {txid}")
    net = network or os.environ.get("GSA_ANCHOR_NETWORK", DEFAULT_NETWORK)
    onchain = _extract_payload((rpc_fn or _rpc_query_tx)(net, tx_hash))
    eng = GameEngine(root / "packs" / f"{pack}.json", root)
    ver = eng.ledger.verify()
    if not ver["ok"] or ver["count"] == 0:
        raise PlayError(f"Local ledger invalid or empty for {pack}")
    if onchain.get("pack_id") != eng.pack_id or onchain.get("tip") != ver["tip"] or onchain.get("count") != ver["count"]:
        raise PlayError(f"On-chain drift: local=({eng.pack_id},{ver['count']},{ver['tip']}) onchain=({onchain.get('pack_id')},{onchain.get('count')},{onchain.get('tip')})")
    if "anchor_sha256" in onchain and canonical_sha256({k: v for k, v in onchain.items() if k != "anchor_sha256"}) != onchain["anchor_sha256"]:
        raise PlayError("On-chain anchor_sha256 integrity mismatch")
    return {"ok": True, "network": net, "txid": tx_hash, "pack_id": eng.pack_id, "count": ver["count"], "tip": ver["tip"]}

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--pack", required=True); ap.add_argument("--execute", action="store_true"); ap.add_argument("--verify-tx", default="")
    a = ap.parse_args()
    print(json.dumps(verify_anchor(a.pack, a.verify_tx) if a.verify_tx else anchor_pack(a.pack, a.execute), indent=2))
