# GSA Studio Game Engine (gsa-game-engine)

Non-explicit (data-driven), fail-closed OSS game & workflow engine by **TradesmanUS / TradesmanTools** for **GSA Studio (GTM) "as a Service"** and the **Tool Data Bank** game. Zero external Python dependencies (100% stdlib).

## Included Rule Packs (packs/)
- `tool_databank`: Snapshot intake -> comp verification (`comp_count >= 3`) -> deterministic deal scoring -> SHA-256 receipt.
- `gtm_studio`: Market signal (chained to `source_proof_hash`) -> brief draft -> review gate -> quorum publish.
- `parliamentary`: Generalized Robert's Rules governance (`main_motion`, `second`, `scope_tweak`, `call_the_question`, `point_of_order`).

## Quickstart

    python3 -m game_engine packs
    python3 -m game_engine.ingest examples/sample_snapshot.csv --reset
    python3 -m game_engine verify --pack tool_databank
    python3 -m game_engine.server --host 127.0.0.1 --port 8790
    python3 -m unittest discover -s tests -v

## License
Licensed under the Apache License, Version 2.0 (see LICENSE and NOTICE).
