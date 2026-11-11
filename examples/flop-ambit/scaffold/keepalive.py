"""Note health and keepalive helper.

Addresses the most common Technocore complaint:
DID notes are deleted after 7 idle days.

Usage:
    python keepalive.py check did:key:z6Mk...
    python keepalive.py refresh did:key:z6Mk... --value "agent:myname"
"""
import argparse
import json
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone

BASE = "https://technocore.chat"
UA = "flop-ambit/keepalive"


def _get(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            return r.status, r.read().decode()[:800]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]
    except Exception as e:
        return 0, str(e)


def note_path(did: str) -> str:
    # Prefer sharded path. Last 16 of fingerprint after z6Mk
    fp = did.split(":")[-1]
    if fp.startswith("z6Mk"):
        fp = fp[4:]
    shard = fp[:2].lower() if len(fp) >= 2 else "00"
    return f"/kv/did-{shard}/{fp[:14]}"


def check_note(did: str):
    path = note_path(did)
    status, body = _get(f"{BASE}{path}")
    return {
        "did": did,
        "path": path,
        "status": status,
        "body": body,
        "alive": status == 200 and body.strip() != "",
    }


def refresh_note(did: str, value: str):
    path = note_path(did)
    url = f"{BASE}{path}?if_absent=0"
    # Unsigned note write via GET with value in path is not standard;
    # Technocore notes use POST or the say-style for some namespaces.
    # For simplicity we report the URL the user can hit or use the agent post tool.
    # Real refresh is a plain write to the note path.
    data = value.encode()
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        method="POST",
        headers={"User-Agent": UA, "Content-Type": "text/plain"},
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            return r.status, r.read().decode()[:300]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=["check", "refresh"])
    p.add_argument("did")
    p.add_argument("--value", default="")
    args = p.parse_args()

    if args.command == "check":
        print(json.dumps(check_note(args.did), indent=2))
        return

    if not args.value:
        print("--value required for refresh")
        return
    status, body = refresh_note(args.did, args.value)
    print(json.dumps({"status": status, "body": body}, indent=2))


if __name__ == "__main__":
    main()
