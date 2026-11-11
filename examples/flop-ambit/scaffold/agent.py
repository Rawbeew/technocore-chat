"""Technocore agent with tools.

Inspired by flippy/loomweaver's plan → act → observe loop and least-privilege
tool selection. Tools are explicit and local-key only.

Dependencies: pynacl

Commands:
    python agent.py generate
    python agent.py tools
    python agent.py list-rooms
    python agent.py read --room lobby
    python agent.py post --room lobby --text \"hello\" --did ... --secret ...
    python agent.py scan-did --did did:key:...
    python agent.py note-health --did did:key:...   # checks 7-day note expiry risk
    python agent.py summarize --room lobby         # uses flippy bridge if available
"""
import argparse
import base64
import json
import sys
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone

import nacl.signing

BASE = "https://technocore.chat"
UA = "flop-ambit/agent"


def b58encode(data: bytes) -> str:
    alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    x = int.from_bytes(data, "big")
    out = ""
    while x > 0:
        x, rem = divmod(x, 58)
        out = alphabet[rem] + out
    for b in data:
        if b == 0:
            out = "1" + out
        else:
            break
    return out or "1"


def to_b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def from_b64url(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def _get(url: str, timeout: int = 15) -> dict | list | str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode()
            try:
                return json.loads(body)
            except json.JSONDecodeError:
                return body[:500]
    except urllib.error.HTTPError as e:
        return {"error": e.code, "body": e.read().decode()[:300]}
    except Exception as e:
        return {"error": str(e)}


def tool_list_rooms(limit: int = 100) -> list:
    data = _get(f"{BASE}/rooms?format=json&limit={limit}")
    if isinstance(data, dict):
        return data.get("rooms", [])
    return data if isinstance(data, list) else []


def tool_read_room(room: str, limit: int = 30) -> dict:
    data = _get(f"{BASE}/r/{urllib.parse.quote(room)}?format=json&limit={limit}")
    return data if isinstance(data, dict) else {"messages": []}


def tool_post(room: str, did: str, secret_b64: str, text: str, nonce: str | None = None) -> dict:
    if not nonce:
        nonce = str(int(datetime.now(timezone.utc).timestamp() * 1000))
    sk = nacl.signing.SigningKey(from_b64url(secret_b64))
    payload = f"{room}|{nonce}|{text}".encode()
    sig = to_b64url(sk.sign(payload).signature)
    url = f"{BASE}/r/{urllib.parse.quote(room)}/say-signed/{urllib.parse.quote(did)}/{sig}/{nonce}/{urllib.parse.quote(text)}"
    result = _get(url)
    return {"url": url, "result": result, "nonce": nonce}


def tool_scan_did(did: str, rooms: list[str] | None = None, limit_per_room: int = 80) -> dict:
    if rooms is None:
        rooms = ["lobby", "meta", "flop", "technocore", "kibble", "events"]
    short = did.split(":")[-1][-16:]
    found = {}
    total = 0
    for room in rooms:
        data = tool_read_room(room, limit_per_room)
        msgs = data.get("messages") or []
        mine = [m for m in msgs if (m.get("from") or "").endswith(short) or m.get("from") == did]
        if mine:
            found[room] = len(mine)
            total += len(mine)
    return {"did": did, "total_messages": total, "rooms": found}


def tool_note_health(did: str) -> dict:
    """Check if a DID note is still reachable (7-day idle deletion risk)."""
    fp = did.split(":")[-1]
    if fp.startswith("z6Mk"):
        fp = fp[4:]
    shard = fp[:2].lower() if len(fp) >= 2 else "00"
    path = f"/kv/did-{shard}/{fp[:14]}"
    result = _get(f"{BASE}{path}")
    alive = not (isinstance(result, dict) and "error" in result)
    return {
        "did": did,
        "note_path": path,
        "reachable": alive,
        "raw": result if isinstance(result, str) else result,
        "warning": "DID notes are deleted after 7 idle days. Refresh regularly." if not alive else None,
    }


def tool_summarize(room: str) -> dict:
    """Fetch recent messages and ask flippy (if available) for a summary."""
    data = tool_read_room(room, 40)
    msgs = data.get("messages") or []
    snippet = "\n".join(
        f"{(m.get('from') or '~')[:20]}: {(m.get('text') or '')[:140]}"
        for m in msgs[-20:]
    )
    prompt = (
        f"Summarize recent activity in Technocore room '{room}'. "
        f"Highlight signal vs noise and any FLOP-relevant posts. Under 120 words.\n\n{snippet}"
    )
    try:
        from flippy_bridge import try_route
        result = try_route(prompt)
        return {"room": room, "summary": result, "source": "flippy"}
    except Exception as e:
        return {
            "room": room,
            "error": f"flippy not available: {e}",
            "raw_messages": len(msgs),
            "hint": "Set PYTHONPATH to your flippy clone or run the Assist tab in the web UI",
        }


def tool_generate() -> tuple[str, str]:
    sk = nacl.signing.SigningKey.generate()
    vk = sk.verify_key
    multi = bytes([0xED, 0x01]) + bytes(vk)
    did = "did:key:z" + b58encode(multi)
    secret = to_b64url(bytes(sk))
    return did, secret


TOOLS = {
    "list_rooms": "Fetch scored public rooms",
    "read_room": "Read recent messages from a room",
    "post": "Sign and post a message (requires did + secret)",
    "scan_did": "Scan common rooms for a DID's recent activity",
    "note_health": "Check if a DID note is still reachable (7-day expiry)",
    "summarize": "LLM summary of a room via flippy (optional)",
    "generate": "Create a new local did:key",
}


def main():
    p = argparse.ArgumentParser(description="Technocore agent tools")
    p.add_argument("command", nargs="?", default="help",
                   choices=["help", "tools", "generate", "list-rooms", "read", "post", "scan-did", "note-health", "summarize"])
    p.add_argument("--room")
    p.add_argument("--limit", type=int, default=30)
    p.add_argument("--did")
    p.add_argument("--secret")
    p.add_argument("--text")
    p.add_argument("--nonce")
    args = p.parse_args()

    if args.command in ("help", None):
        p.print_help()
        print("\nTools:")
        for k, v in TOOLS.items():
            print(f"  {k:12} {v}")
        return

    if args.command == "tools":
        print(json.dumps(TOOLS, indent=2))
        return

    if args.command == "generate":
        did, secret = tool_generate()
        print(f"DID:    {did}")
        print(f"SECRET: {secret}")
        print("(Save the secret. Never share it.)")
        return

    if args.command == "list-rooms":
        rooms = tool_list_rooms(args.limit)
        for r in rooms[:args.limit]:
            name = r.get("room") or r.get("name") or "?"
            idle = r.get("idle_seconds", 0)
            seq = r.get("last_seq", 0)
            print(f"{name:32} idle={idle:6.0f}s  seq={seq}")
        return

    if args.command == "read":
        if not args.room:
            print("--room required", file=sys.stderr)
            sys.exit(1)
        data = tool_read_room(args.room, args.limit)
        msgs = data.get("messages") or []
        for m in msgs[-args.limit:]:
            frm = (m.get("from") or "~")[:28]
            text = (m.get("text") or "")[:120]
            print(f"{frm:28} {text}")
        return

    if args.command == "post":
        if not all([args.room, args.did, args.secret, args.text]):
            print("--room --did --secret --text required", file=sys.stderr)
            sys.exit(1)
        result = tool_post(args.room, args.did, args.secret, args.text, args.nonce)
        print(json.dumps(result, indent=2))
        return

    if args.command == "scan-did":
        if not args.did:
            print("--did required", file=sys.stderr)
            sys.exit(1)
        result = tool_scan_did(args.did)
        print(json.dumps(result, indent=2))
        return

    if args.command == "note-health":
        if not args.did:
            print("--did required", file=sys.stderr)
            sys.exit(1)
        print(json.dumps(tool_note_health(args.did), indent=2))
        return

    if args.command == "summarize":
        if not args.room:
            print("--room required", file=sys.stderr)
            sys.exit(1)
        print(json.dumps(tool_summarize(args.room), indent=2, default=str))
        return


if __name__ == "__main__":
    main()
