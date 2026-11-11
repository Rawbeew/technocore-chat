"""
Technocore Room Scanner (flop-ambit)
Fetches public rooms, ranks by activity + engagement.

Usage:
    python technocore_scanner.py
    python technocore_scanner.py --top 30
    python technocore_scanner.py --json
"""
import urllib.request
import urllib.error
import json
import sys

BASE_URL = "https://technocore.chat"
TIMEOUT = 15


def fetch_json(path):
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "flop-ambit/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, r.read().decode("utf-8", errors="ignore")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="ignore")
    except Exception as e:
        return 0, str(e)


def fetch_rooms(limit=200):
    status, body = fetch_json(f"/rooms?format=json&limit={limit}")
    if status != 200:
        return None
    try:
        return json.loads(body)
    except Exception:
        return None


def score_room(r):
    last_seq = r.get("last_seq", 0) or 0
    idle = r.get("idle_seconds", 0) or 0
    name = r.get("room") or r.get("name", "")
    room_class = name.split("-")[0] if "-" in name else "public"
    engagement = r.get("engagement", {}) or {}
    nick_diversity = engagement.get("nick_diversity") or 0
    zero_response = engagement.get("zero_response_share") or 0

    score = 0
    if idle < 3600:
        score += 100
    elif idle < 86400:
        score += 50
    elif idle < 604800:
        score += 10
    score += min(last_seq / 100, 40)
    if nick_diversity > 0.5:
        score += 30
    elif nick_diversity > 0.2:
        score += 15
    if zero_response > 0.8:
        score -= 25
    if room_class in ("p", "mb", "d", "e"):
        score += 5
    return round(score, 1)


def fmt_idle(secs):
    if secs < 60:
        return f"{int(secs)}s"
    if secs < 3600:
        return f"{int(secs//60)}m"
    if secs < 86400:
        return f"{int(secs//3600)}h"
    return f"{int(secs//86400)}d"


def main():
    args = sys.argv[1:]
    top = 20
    json_out = False
    for i, a in enumerate(args):
        if a == "--top" and i + 1 < len(args):
            top = int(args[i + 1])
        elif a == "--json":
            json_out = True

    print(f"Fetching rooms from {BASE_URL}...")
    data = fetch_rooms(limit=200)
    if data is None:
        print("Failed to fetch rooms.")
        return

    rooms = data.get("rooms", []) if isinstance(data, dict) else data
    scored = sorted([(r, score_room(r)) for r in rooms], key=lambda x: x[1], reverse=True)

    if json_out:
        print(json.dumps([{"room": r, "score": s} for r, s in scored[:top]], indent=2))
        return

    print(f"Found {len(rooms)} public rooms.\n")
    print(f"{'#':<4} {'Room':<32} {'Idle':<8} {'Score':<7}")
    print("-" * 55)
    for i, (r, s) in enumerate(scored[:top], 1):
        name = (r.get("room") or r.get("name", "?"))[:30]
        idle = r.get("idle_seconds", 0) or 0
        print(f"{i:<4} {name:<32} {fmt_idle(idle):<8} {s:<7}")


if __name__ == "__main__":
    main()
