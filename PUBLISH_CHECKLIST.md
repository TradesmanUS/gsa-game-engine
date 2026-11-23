# OSS Publish Checklist — GSA Studio Game Engine (v0.1.0)
- [x] Non-explicit core (`game_engine/engine.py`) with zero hardcoded domain branches
- [x] Fail-closed SHA-256 `ProofLedger` + tamper-detection tests passing (`unittest`)
- [x] Zero-leak OSS hygiene gate green (no internal hosts, emails, or secrets)
- [x] `.gitignore` excludes `logs/`, `state/`, `__pycache__/`, `.env`
- [x] GitHub Actions CI gate (`.github/workflows/ci.yml`) ready
- [x] Add `LICENSE` (MIT or Apache-2.0) and `README.md` quickstart
- [x] Confirm target GitHub org (`TradesmanUS` or `tradesmantools`) & repo visibility (`public`)
- [ ] Run `git init && git add . && git commit -m "feat: OSS GSA game engine v0.1.0"`
- [ ] Push `main`, tag `v0.1.0`, and verify green `OSS Proof Gate` workflow on GitHub
