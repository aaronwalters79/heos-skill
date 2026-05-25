Control the HEOS whole-home audio system using natural language.

Arguments: $ARGUMENTS — a natural language request, e.g. "play Alt Nation in the office", "pause everything", "what's playing?", "turn up patio to 60"

## Setup

The controller script is at `~/.claude/heos.py`. Run it with:
```
python3 ~/.claude/heos.py <command> [args...]
```

All output is JSON. Player names are case-insensitive and support partial matching (e.g. "office", "bedroom", "patio").

## Known players (resolved at runtime — run `players` to refresh)

| Name | Model | Network |
|------|-------|---------|
| Home Theater | Marantz CINEMA 60 | wired |
| Patio | HEOS Amp | wired |
| Master Bedroom | Denon Home 150 | wifi |
| Office | HEOS Amp | wired |
| Living Room | HEOS Link | wifi |
| Guest Room | Denon Home 150 | wifi |

## Known favorites (preset numbers for `play_favorite`)

| Preset | Name |
|--------|------|
| 1 | 22 - Pearl Jam Radio (SiriusXM) |
| 2 | 36 - Alt Nation (SiriusXM) |

## SiriusXM channel quick-reference (sid=8 — use `stream` directly)

| Channel | Name | mid |
|---------|------|-----|
| 3 | Unwell Music | `9663` |
| 22 | Pearl Jam Radio | `8370` |
| 27 | Alt2K | `9611` |
| 28 | The Spectrum | `thespectrum` |
| 33 | 1st Wave | `firstwave` |
| 34 | Lithium | `90salternative` |
| 36 | Alt Nation | `altnation` |
| 52 | BPM | `thebeat` |
| 78 | Symphony Hall | `symphonyhall` |

## TuneIn station quick-reference (sid=3 — use `stream` directly)

| Name | mid |
|------|-----|
| 99.5 WCRB (main classical) | `s28014` |
| WCRB Bach Channel | `s188208` |
| WCRB BSO Concert Channel | `s141273` |
| WCRB's Boston Early Music | `s140158` |

## Available music sources

| sid | Name | Notes |
|-----|------|-------|
| 1028 | Favorites | Saved favorites list |
| 8 | SiriusXM | Streaming radio |
| 3 | TuneIn | Internet radio — browsable and searchable |
| 1024 | Local Music | NAS/local library |
| 1025 | Playlists | Saved playlists |
| 1026 | History | Recently played |
| 1027 | AUX Input | Physical input |

## Command reference

```
python3 ~/.claude/heos.py players                      # list all players with current IPs
python3 ~/.claude/heos.py status [player]              # now playing + volume for one or all players
python3 ~/.claude/heos.py play <player>                # resume playback
python3 ~/.claude/heos.py pause <player>               # pause
python3 ~/.claude/heos.py stop <player>                # stop
python3 ~/.claude/heos.py next <player>                # skip to next
python3 ~/.claude/heos.py prev <player>                # previous track
python3 ~/.claude/heos.py volume <player> <0-100>      # set volume
python3 ~/.claude/heos.py mute <player> [on|off|toggle]
python3 ~/.claude/heos.py queue <player>               # show current queue
python3 ~/.claude/heos.py clear <player>               # clear queue
python3 ~/.claude/heos.py favorites                    # list favorites with mid values
python3 ~/.claude/heos.py play_favorite <player> <preset_number>  # play favorite by preset #
python3 ~/.claude/heos.py sources                      # list available music sources
python3 ~/.claude/heos.py browse <sid> [cid]           # browse a source or container
python3 ~/.claude/heos.py search <sid> <query> [scid]  # search (scid: 1=artist 2=album 3=track 4=station)
python3 ~/.claude/heos.py stream <player> <sid> <mid> [name]  # play a station/stream (SiriusXM, internet radio)
python3 ~/.claude/heos.py add <player> <sid> <mid> [cid] [aid]  # add/play local music tracks (aid: 1=now 2=next 3=end 4=replace)
python3 ~/.claude/heos.py history                      # recently played containers
```

## Handling user requests

**"What's playing?" / status requests:**
Run `status` with no player arg to get all rooms, or with a specific player name.

**"Play [favorite name]" in [room]:**
Match the name against the favorites table above. Run `play_favorite <player> <preset>`.
If the user names a favorite not in the list, run `favorites` first to get the current list.

**"Play [SiriusXM channel name/number]" in [room]:**
Browse SiriusXM: `browse 8` (or `browse 8 <genre_cid>` for a genre). Each item has a `mid` field. Use `stream <player> 8 <mid> <channel_name>` — NOT `add`, which doesn't work for SiriusXM stations.

**"Search for [query]" in [room]:**
Use `search 1024 "<query>" 3` for tracks in Local Music, or `search 8 "<query>" 4` for SiriusXM stations.
Results include `mid` and `cid` fields. Use `add` to queue the result.

**"Classical music" / "play classical" in [room]:**
Do NOT search or browse. Immediately present this numbered menu and ask the user to pick one:

```
Classical options:
1. Symphony Hall (SiriusXM 78) — orchestral & opera
2. 99.5 WCRB (TuneIn) — Boston classical, main stream
3. WCRB Bach Channel (TuneIn) — Bach only
4. WCRB BSO Concert Channel (TuneIn) — Boston Symphony Orchestra
5. WCRB's Boston Early Music (TuneIn) — early/baroque music
```

Once the user picks, run `stream <player> <sid> <mid> <name>` with no further prompting.

**"Pause/stop everything":**
Run `status` to find all playing rooms, then `pause` or `stop` each one.

**"Turn up/down volume":**
Parse the target level. If the user says "turn up by 10", run `status` on that player first to get current volume, then compute the new level.

**"Play what's in [room] in [other room]" (copy now playing):**
Run `status <source_room>`, note the now-playing media type. For stations: `add <target_player> <sid> <mid>`.

**Ambiguous room names:**
If the user says "bedroom" and there are multiple (Master Bedroom, Guest Room), ask which one.

## Steps

1. Read $ARGUMENTS carefully.
2. Identify: which player(s), what action, what content (if any).
3. If a content search is needed, run the appropriate `browse` or `search` command first to get the `mid`.
4. Execute the action command(s).
5. Report back in plain language: what's now playing, what changed, any errors.
