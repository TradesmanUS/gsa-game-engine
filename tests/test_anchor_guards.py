from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path
from game_engine import GameEngine, PlayError
from game_engine.anchor import build_anchor, validate_anchor_target, verify_anchor

ROOT = Path(__file__).resolve().parent.parent

class TestAnchorGuardsAndReconcile(unittest.TestCase):
    def test_network_and_wallet_guards_fail_closed(self) -> None:
        with self.assertRaises(PlayError):
            validate_anchor_target("https://mainnet.accumulatenetwork.io/v2", "/tmp/iso-wallet")
        with self.assertRaises(PlayError):
            validate_anchor_target("https://kermit.accumulatenetwork.io/v2", "")
        with self.assertRaises(PlayError):
            validate_anchor_target("https://kermit.accumulatenetwork.io/v2", "C:\\Users\\demo\\.accumulate")
        net, w = validate_anchor_target("https://kermit.accumulatenetwork.io/v2", "/tmp/iso-wallet")
        self.assertIn("kermit", net); self.assertEqual(w, "/tmp/iso-wallet")
        net2, _ = validate_anchor_target("https://mainnet.accumulatenetwork.io/v2", "C:\\Users\\demo\\.accumulate", allow_mainnet=True)
        self.assertIn("mainnet", net2)

    def test_verify_anchor_matches_and_detects_drift(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d); (tmp / "packs").mkdir()
            (tmp / "packs" / "tool_databank.json").write_text((ROOT / "packs" / "tool_databank.json").read_text(encoding="utf-8"), encoding="utf-8")
            e = GameEngine(tmp / "packs" / "tool_databank.json", tmp)
            e.play("scout", "ingest_snapshot", "Drop", {"corridor": "phx", "category": "tools", "buy_price": 100})
            rec = build_anchor("tool_databank", tmp)
            tx = "acc://" + ("a" * 64) + "@macropay.acme/data"
            mock_rpc = lambda _n, _h: {"result": {"transaction": {"body": {"entry": {"data": [json.dumps(rec, sort_keys=True).encode().hex()]}}}}}
            out = verify_anchor("tool_databank", tx, root=tmp, rpc_fn=mock_rpc)
            self.assertTrue(out["ok"]); self.assertEqual(out["tip"], rec["tip"])
            bad_rec = {**rec, "tip": "0" * 64}
            bad_rpc = lambda _n, _h: {"result": {"transaction": {"body": {"entry": {"data": [json.dumps(bad_rec, sort_keys=True).encode().hex()]}}}}}
            with self.assertRaises(PlayError):
                verify_anchor("tool_databank", tx, root=tmp, rpc_fn=bad_rpc)

if __name__ == "__main__": unittest.main()
