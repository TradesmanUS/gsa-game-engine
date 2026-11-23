from __future__ import annotations
import tempfile, unittest
from pathlib import Path
from game_engine import GameEngine, PlayError
ROOT = Path(__file__).resolve().parent.parent
class TestGSAGameEngine(unittest.TestCase):
    def _eng(self, pack: str, tmp: Path) -> GameEngine:
        return GameEngine(ROOT / "packs" / f"{pack}.json", tmp)
    def test_tool_databank_and_tamper_detection(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            e = self._eng("tool_databank", Path(d))
            e.play("scout", "ingest_snapshot", "Drop", {"corridor": "phx", "category": "tools", "buy_price": 100})
            with self.assertRaises(PlayError):
                e.play("analyst", "verify_comp", "Thin", {"comp_median": 200, "comp_count": 2})
            e.play("analyst", "verify_comp", "Solid", {"comp_median": 200, "comp_count": 5})
            rec = e.play("analyst", "score_deal", "Score")
            self.assertEqual(rec["metrics"]["signal_tier"], "A_BUY")
            e.play("auditor", "publish_receipt", "Seal")
            self.assertTrue(e.ledger.verify()["ok"])
            raw = e.ledger.path.read_text(encoding="utf-8").replace("phx", "tampered", 1)
            e.ledger.path.write_text(raw, encoding="utf-8")
            self.assertFalse(e.ledger.verify()["ok"])
    def test_parliamentary_no_self_second(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            e = self._eng("parliamentary", Path(d))
            e.play("builder", "main_motion", "Ship")
            with self.assertRaises(PlayError):
                e.play("builder", "second")
    def test_oss_hygiene_no_private_leaks(self) -> None:
        banned = ("grippingly.com", "gmail.com", "canary_secret", "lv8r_admin", "BEGIN PRIVATE KEY")
        for fp in list((ROOT / "game_engine").glob("*.py")) + list((ROOT / "packs").glob("*.json")):
            txt = fp.read_text(encoding="utf-8")
            for b in banned:
                self.assertNotIn(b, txt, f"Leak {b} in {fp.name}")
if __name__ == "__main__": unittest.main()
