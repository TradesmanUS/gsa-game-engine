from __future__ import annotations
import argparse, json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from .engine import GameEngine
from .guards import PlayError
ROOT = Path(__file__).resolve().parent.parent
def _eng(pack: str) -> GameEngine:
    p = ROOT / "packs" / f"{pack}.json"
    if not p.exists(): raise PlayError(f"Unknown pack: {pack}")
    return GameEngine(p, ROOT)
class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, obj: dict) -> None:
        raw = json.dumps(obj).encode("utf-8")
        self.send_response(code); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw)
    def log_message(self, fmt: str, *args) -> None: pass
    def do_GET(self) -> None:
        u = urlparse(self.path); pack = (parse_qs(u.query).get("pack") or [""])[0]
        try:
            if u.path == "/packs": return self._send(200, {"packs": sorted(p.stem for p in (ROOT / "packs").glob("*.json"))})
            e = _eng(pack)
            if u.path == "/status": return self._send(200, {"pack": e.pack_id, "state": e.state, "active": e.active, "valid": {s: e.valid_cards(s) for s in e.pack["seats"]}})
            if u.path == "/verify":
                res = e.ledger.verify(); return self._send(200 if res["ok"] else 409, {"pack": e.pack_id, **res})
            self._send(404, {"error": "Not found"})
        except PlayError as exc: self._send(400, {"error": str(exc)})
    def do_POST(self) -> None:
        b = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        try:
            e = _eng(b.get("pack", ""))
            if self.path == "/reset": e.reset(); return self._send(200, {"reset": e.pack_id, "state": e.state})
            if self.path == "/play": return self._send(200, e.play(b["seat"], b["card"], b.get("title", ""), b.get("payload"), b.get("votes")))
            self._send(404, {"error": "Not found"})
        except (PlayError, KeyError) as exc: self._send(400, {"error": str(exc)})
if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--host", default="127.0.0.1"); ap.add_argument("--port", type=int, default=8790); a = ap.parse_args()
    ThreadingHTTPServer((a.host, a.port), Handler).serve_forever()
