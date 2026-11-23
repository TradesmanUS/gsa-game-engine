from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path
from game_engine import GameEngine, PlayError
from game_engine.anchor import build_anchor
ROOT = Path(__file__).resolve().parent.parent
class TestV030GovernanceAndI3(unittest.TestCase):
    def test_anchor_refuses_tampered_or_empty_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d); (tmp / "packs").mkdir()
            (tmp / "packs" / "tool_databank.json").write_text((ROOT / "packs" / "tool_databank.json").read_text(encoding="utf-8"), encoding="utf-8")
            with self.assertRaises(PlayError): build_anchor("tool_databank", tmp)
            e = GameEngine(tmp / "packs" / "tool_databank.json", tmp)
            e.play("scout", "ingest_snapshot", "Drop", {"corridor": "phx", "category": "tools", "buy_price": 100})
            self.assertIn("anchor_sha256", build_anchor("tool_databank", tmp))
            e.ledger.path.write_text(e.ledger.path.read_text(encoding="utf-8").replace("phx", "bad", 1), encoding="utf-8")
            with self.assertRaises(PlayError): build_anchor("tool_databank", tmp)
    def test_invariant_i3_no_keys_or_private_adi_in_repo(self) -> None:
        banned = ("sandbox-kermit", "lv8rlabs-sandbox", "lv8rlabs.acme", "accumulate.exe", "PRIVATE KEY")
        files = list((ROOT / "game_engine").glob("*.py")) + list((ROOT / "packs").glob("*.json")) + list((ROOT / ".devcontainer").glob("*.json"))
        for fp in files:
            txt = fp.read_text(encoding="utf-8")
            for b in banned: self.assertNotIn(b, txt, f"Invariant I3 violation ({b}) in {fp.name}")
    def test_tool_databank_never_auto_buy(self) -> None:
        pack = json.loads((ROOT / "packs" / "tool_databank.json").read_text(encoding="utf-8"))
        for cid, spec in pack["cards"].items():
            for word in ("buy", "purchase", "checkout", "pay", "order"):
                self.assertNotIn(word, cid.lower().split("_")); self.assertNotIn(word, spec.get("effect", "").lower().split("_"))
if __name__ == "__main__": unittest.main()
