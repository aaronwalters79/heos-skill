#!/usr/bin/env python3
"""HEOS CLI controller — used by the /heos Claude Code skill."""

import json
import socket
import sys
from urllib.parse import quote

HEOS_HOST = "192.168.1.23"  # Wired HEOS Amp (Patio) — reliable entry point
HEOS_PORT = 1255
DEFAULT_PLAYER = ""  # Set to a room name to use when none is specified, e.g. "Living Room"


# ── Transport ──────────────────────────────────────────────────────────────────

def connect():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HEOS_HOST, HEOS_PORT))
    sock.settimeout(10)
    return sock


def send_cmd(sock, cmd):
    """Send a HEOS command and return the first non-ack JSON response."""
    sock.sendall((cmd + "\r\n").encode())
    buf = ""
    while True:
        try:
            chunk = sock.recv(4096).decode("utf-8", errors="ignore")
            if not chunk:
                break
            buf += chunk
            while "\r\n" in buf:
                line, buf = buf.split("\r\n", 1)
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    # Skip the intermediate "command under process" ack
                    if "command under process" in data.get("heos", {}).get("message", ""):
                        continue
                    return data
                except json.JSONDecodeError:
                    pass
        except socket.timeout:
            break
    return {"error": "timeout", "buffered": buf}


# ── Player resolution ──────────────────────────────────────────────────────────

def get_players(sock):
    resp = send_cmd(sock, "heos://player/get_players")
    players = {}
    for p in resp.get("payload", []):
        players[p["name"].lower()] = p
    return players


def resolve_player(players, name=None):
    if not name:
        if not DEFAULT_PLAYER:
            names = ", ".join(p["name"] for p in players.values())
            raise ValueError(f"No player specified and DEFAULT_PLAYER is not set. Available: {names}")
        name = DEFAULT_PLAYER
    key = name.lower()
    if key in players:
        return players[key]
    for k, v in players.items():
        if key in k or k in key:
            return v
    names = ", ".join(p["name"] for p in players.values())
    raise ValueError(f"Player '{name}' not found. Available: {names}")


def parse_message(msg):
    """Parse 'key=val&key2=val2' HEOS message string into a dict."""
    result = {}
    for part in msg.split("&"):
        if "=" in part:
            k, _, v = part.partition("=")
            result[k] = v
    return result


# ── Commands ───────────────────────────────────────────────────────────────────

def cmd_players(sock, players, _args):
    out = [
        {"name": p["name"], "model": p["model"], "ip": p["ip"], "network": p["network"]}
        for p in players.values()
    ]
    print(json.dumps(out, indent=2))


def cmd_status(sock, players, args):
    targets = [resolve_player(players, args[0])] if args else list(players.values())
    results = []
    for p in targets:
        pid = p["pid"]
        state_resp = send_cmd(sock, f"heos://player/get_play_state?pid={pid}")
        vol_resp = send_cmd(sock, f"heos://player/get_volume?pid={pid}")
        now_resp = send_cmd(sock, f"heos://player/get_now_playing_media?pid={pid}")

        state_msg = parse_message(state_resp.get("heos", {}).get("message", ""))
        vol_msg = parse_message(vol_resp.get("heos", {}).get("message", ""))
        media = now_resp.get("payload", {})

        results.append({
            "name": p["name"],
            "model": p["model"],
            "state": state_msg.get("state", "unknown"),
            "volume": vol_msg.get("level", "?"),
            "now_playing": {
                "type": media.get("type", "unknown"),
                "song": media.get("song") or media.get("station", ""),
                "artist": media.get("artist", ""),
                "album": media.get("album", ""),
            },
        })
    print(json.dumps(results, indent=2))


def cmd_play(sock, players, args):
    p = resolve_player(players, args[0] if args else None)
    resp = send_cmd(sock, f"heos://player/set_play_state?pid={p['pid']}&state=play")
    print(json.dumps({"player": p["name"], "result": resp.get("heos", {}).get("result")}))


def cmd_pause(sock, players, args):
    p = resolve_player(players, args[0] if args else None)
    resp = send_cmd(sock, f"heos://player/set_play_state?pid={p['pid']}&state=pause")
    print(json.dumps({"player": p["name"], "result": resp.get("heos", {}).get("result")}))


def cmd_stop(sock, players, args):
    p = resolve_player(players, args[0] if args else None)
    resp = send_cmd(sock, f"heos://player/set_play_state?pid={p['pid']}&state=stop")
    print(json.dumps({"player": p["name"], "result": resp.get("heos", {}).get("result")}))


def cmd_next(sock, players, args):
    p = resolve_player(players, args[0] if args else None)
    resp = send_cmd(sock, f"heos://player/play_next?pid={p['pid']}")
    print(json.dumps({"player": p["name"], "result": resp.get("heos", {}).get("result")}))


def cmd_prev(sock, players, args):
    p = resolve_player(players, args[0] if args else None)
    resp = send_cmd(sock, f"heos://player/play_previous?pid={p['pid']}")
    print(json.dumps({"player": p["name"], "result": resp.get("heos", {}).get("result")}))


def cmd_volume(sock, players, args):
    p = resolve_player(players, args[0] if len(args) > 1 else None)
    level = int(args[1] if len(args) > 1 else args[0])
    if not 0 <= level <= 100:
        raise ValueError("Volume must be 0–100")
    resp = send_cmd(sock, f"heos://player/set_volume?pid={p['pid']}&level={level}")
    print(json.dumps({"player": p["name"], "volume": level, "result": resp.get("heos", {}).get("result")}))


def cmd_mute(sock, players, args):
    p = resolve_player(players, args[0] if args else None)
    state = args[1] if len(args) > 1 else "toggle"
    resp = send_cmd(sock, f"heos://player/set_mute?pid={p['pid']}&state={state}")
    print(json.dumps({"player": p["name"], "mute": state, "result": resp.get("heos", {}).get("result")}))


def cmd_queue(sock, players, args):
    p = resolve_player(players, args[0] if args else None)
    resp = send_cmd(sock, f"heos://player/get_queue?pid={p['pid']}")
    print(json.dumps(resp.get("payload", []), indent=2))


def cmd_clear(sock, players, args):
    p = resolve_player(players, args[0] if args else None)
    resp = send_cmd(sock, f"heos://player/clear_queue?pid={p['pid']}")
    print(json.dumps({"player": p["name"], "result": resp.get("heos", {}).get("result")}))


def cmd_sources(sock, players, _args):
    resp = send_cmd(sock, "heos://browse/get_music_sources")
    available = [s for s in resp.get("payload", []) if str(s.get("available")).lower() == "true"]
    print(json.dumps(available, indent=2))


def cmd_favorites(sock, players, _args):
    resp = send_cmd(sock, "heos://browse/browse?sid=1028")
    print(json.dumps(resp.get("payload", []), indent=2))


def cmd_play_favorite(sock, players, args):
    p = resolve_player(players, args[0] if len(args) > 1 else None)
    preset = int(args[1] if len(args) > 1 else args[0])
    resp = send_cmd(sock, f"heos://player/play_favorite?pid={p['pid']}&preset={preset}")
    print(json.dumps({"player": p["name"], "preset": preset, "result": resp.get("heos", {}).get("result")}))


def cmd_browse(sock, players, args):
    sid = args[0]
    if len(args) > 1:
        cid = args[1]
        resp = send_cmd(sock, f"heos://browse/browse?sid={sid}&cid={cid}")
    else:
        resp = send_cmd(sock, f"heos://browse/browse?sid={sid}")
    print(json.dumps(resp.get("payload", []), indent=2))


def cmd_search(sock, players, args):
    # args: sid query [scid]
    # scid: 1=artist 2=album 3=track 4=station
    sid = args[0]
    query = quote(args[1], safe="")
    scid = args[2] if len(args) > 2 else "3"
    resp = send_cmd(sock, f"heos://browse/search?sid={sid}&search={query}&scid={scid}")
    print(json.dumps(resp.get("payload", []), indent=2))


def cmd_add(sock, players, args):
    # args: player sid mid [cid] [aid]
    # aid: 1=play_now 2=play_next 3=add_to_end 4=replace_and_play
    p = resolve_player(players, args[0])
    sid, mid = args[1], args[2]
    cid = args[3] if len(args) > 3 else ""
    aid = args[4] if len(args) > 4 else "4"

    cmd = f"heos://player/add_to_queue?pid={p['pid']}&sid={sid}&mid={mid}&aid={aid}"
    if cid:
        cmd += f"&cid={cid}"
    resp = send_cmd(sock, cmd)
    print(json.dumps({"player": p["name"], "result": resp.get("heos", {}).get("result")}))


def cmd_stream(sock, players, args):
    # Play a station/stream via browse/play_stream (required for SiriusXM and internet radio)
    # args: player sid mid [name]
    p = resolve_player(players, args[0] if len(args) > 2 else None)
    sid, mid = (args[1], args[2]) if len(args) > 2 else (args[0], args[1])
    name = quote(args[3] if len(args) > 3 else (args[2] if len(args) > 2 else mid), safe="")
    resp = send_cmd(sock, f"heos://browse/play_stream?pid={p['pid']}&sid={sid}&mid={mid}&name={name}")
    print(json.dumps({"player": p["name"], "result": resp.get("heos", {}).get("result")}))


def cmd_history(sock, players, _args):
    resp = send_cmd(sock, "heos://browse/browse?sid=1026")
    print(json.dumps(resp.get("payload", []), indent=2))


COMMANDS = {
    "players": cmd_players,
    "status": cmd_status,
    "play": cmd_play,
    "pause": cmd_pause,
    "stop": cmd_stop,
    "next": cmd_next,
    "prev": cmd_prev,
    "volume": cmd_volume,
    "mute": cmd_mute,
    "queue": cmd_queue,
    "clear": cmd_clear,
    "sources": cmd_sources,
    "favorites": cmd_favorites,
    "play_favorite": cmd_play_favorite,
    "browse": cmd_browse,
    "search": cmd_search,
    "add": cmd_add,
    "stream": cmd_stream,
    "history": cmd_history,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("Usage: heos.py <command> [args...]")
        print("Commands:", ", ".join(COMMANDS))
        sys.exit(0)

    command = sys.argv[1]
    args = sys.argv[2:]

    if command not in COMMANDS:
        print(json.dumps({"error": f"Unknown command '{command}'", "available": list(COMMANDS)}))
        sys.exit(1)

    try:
        sock = connect()
        players = get_players(sock)
        COMMANDS[command](sock, players, args)
        sock.close()
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
