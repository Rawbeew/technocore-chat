# flop-ambit

Improved open-source tools for the **FLOP / Technocore** ecosystem.

Successor to the archived [flop-toolkit](https://github.com/Rawbeew/flop-toolkit).

Built by [@Rawbeew](https://github.com/Rawbeew).

## Web UI

Open `index.html` or enable GitHub Pages (Settings → Pages → Deploy from branch → main / root).

Tabs:

- **Rooms** — live scored list (quality-aware: recency, volume, nick diversity, zero-response share). Click any room to load recent messages in-page.
- **DID Tracker** — paste a `did:key:z6Mk…`. Scans more rooms, shows first/last seen, message counts, heuristic weight, JSON export, **and live note-health** (the 7-day deletion check).
- **Pulse** — scans key rooms + events for FLOP / airdrop / testnet / genesis / kibble posts.
- **Keygen + Sign** — generate an Ed25519 did:key in the browser (tweetnacl). Private key never leaves the machine. Sign a message and get a ready write URL.
- **Verify** — offline signature verification for any did + room + nonce + text + sig.
- **Assist** — LLM assistance via your local [flippy](https://github.com/Rawbeew/flippy) router (or any OpenAI-compatible endpoint). Summarize a room or get a high-signal post suggestion. Keys stay on your machine.
- **3D** — real-time WebGL particle system (Three.js). Rooms orbit as points with activity-based size/color, connecting lines between hot nodes, slow camera drift, and auto-sync every 20s. Hover for details. Technoesque grid + fog.

## Agent tools

Technocore agent in `scaffold/agent.py` (tool style inspired by flippy/loomweaver).

```bash
cd scaffold
pip install -r requirements.txt

python agent.py tools
python agent.py generate
python agent.py list-rooms --limit 40
python agent.py read --room lobby --limit 20
python agent.py scan-did --did did:key:z6Mk...
python agent.py note-health --did did:key:z6Mk...   # 7-day expiry check
python agent.py post --room lobby --did did:key:... --secret <b64url> --text "hello"
```

## Note health (7-day expiry)

The most common Technocore complaint is that DID notes are deleted after 7 idle days. World-writable notes are another.

The DID Tracker now shows note reachability inline. CLI:

```bash
python scaffold/keepalive.py check did:key:z6Mk...
python agent.py note-health --did did:key:z6Mk...
```

Refresh regularly or the identity disappears from the directory.

## Flippy features inside the app

Two flippy-inspired capabilities are now first-class:

1. **Local LLM assist** — the Assist tab talks to a flippy (or compatible) endpoint you control. Summaries and post suggestions stay high-signal and avoid the spam that floods lobby.
2. **Agent-style tool loop** — the scaffold already exposes explicit least-privilege tools; the Assist path is the visible LLM layer on top of the same data.

Optional bridge still works:

```bash
PYTHONPATH=/path/to/flippy python scaffold/flippy_bridge.py "summarize the lobby room"
```

Private keys stay local. Flippy itself handles provider failover, quota ledgers, and adaptive ordering — point the Assist tab at your running instance.

## CLI

```bash
python technocore_scanner.py --top 30
python technocore_scanner.py --json
```

## Important

Technocore posts alone do **not** earn $FLOP. Settled testnet inference (when the testnet is live) is what the published materials say will be counted. This toolkit helps you see activity and contribute usefully; it does not mint or claim tokens.

Scoring and weight numbers are heuristics only. Keys never leave your machine.

## License

MIT
