# HEOS Claude Code Skill

A [Claude Code](https://claude.ai/code) skill for controlling a HEOS whole-home audio system using natural language.

## What it does

Invoke `/heos <request>` from Claude Code to control your HEOS speakers with plain English:

```
/heos what's playing in every room
/heos play Alt Nation in the office
/heos play classical in the living room
/heos turn the patio up to 60
/heos pause everything
/heos play BPM in the bedroom
```

## How it works

- `heos.py` — Python CLI that speaks the [HEOS CLI protocol](https://rn.dmglobal.com/euheos/HEOS_CLI_ProtocolSpecification.pdf) over TCP (port 1255). Discovers players at runtime by name — no hardcoded PIDs.
- `heos.md` — Claude Code command file that translates natural language into `heos.py` calls. Drop it in `~/.claude/commands/` to register the `/heos` skill.

## Requirements

- Python 3 (stdlib only, no dependencies)
- A HEOS-compatible device on your local network (Denon, Marantz, or HEOS branded speakers)
- [Claude Code](https://claude.ai/code)

## Setup

1. Copy both files to `~/.claude/`:
   ```bash
   cp heos.py ~/.claude/
   cp heos.md ~/.claude/commands/
   ```

2. Edit `heos.py` and set `HEOS_HOST` to the IP of any HEOS device on your network:
   ```python
   HEOS_HOST = "192.168.1.x"
   ```
   To discover devices, run:
   ```bash
   python3 heos.py players
   ```
   If that fails, use a network scanner or check your router's DHCP table for Denon/Marantz/HEOS devices.

3. Update the player names and channel quick-reference in `heos.md` to match your setup.

## CLI usage

`heos.py` can also be used standalone:

```bash
python3 heos.py players                        # list all players
python3 heos.py status                         # now playing + volume for all rooms
python3 heos.py status "Office"                # status for one room
python3 heos.py play "Patio"
python3 heos.py pause "Patio"
python3 heos.py volume "Office" 40
python3 heos.py stream "Living Room" 8 symphonyhall "Symphony Hall"   # SiriusXM
python3 heos.py stream "Living Room" 3 s28014 "99.5 WCRB"             # TuneIn
python3 heos.py search 3 "WCRB" 4             # search TuneIn for a station
python3 heos.py browse 8 rock                 # browse SiriusXM rock genre
python3 heos.py favorites                     # list saved favorites
python3 heos.py play_favorite "Office" 1      # play favorite by preset number
```

All output is JSON.

## Music sources

| Source | sid | Notes |
|--------|-----|-------|
| SiriusXM | 8 | Browse by genre or use channel quick-reference |
| TuneIn | 3 | Search by call sign, station name, or genre |
| Local Music | 1024 | NAS or local DLNA library |
| Favorites | 1028 | Saved HEOS favorites |
| Playlists | 1025 | Saved playlists |
| History | 1026 | Recently played |

## Notes

- **SiriusXM stations** require `stream` (uses `browse/play_stream`), not `add` (uses `add_to_queue`). The two commands are not interchangeable.
- Player PIDs change on reboot/firmware update. The script always resolves names → PIDs at runtime.
- Browse commands for SiriusXM return `"command under process"` acks before the real response — the script handles this automatically.
