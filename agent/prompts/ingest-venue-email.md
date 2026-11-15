# Prompt: turn a venue's AV email into a graph venue

Read the email (or booking page, or tech rider) below and produce **one JSON object** that matches
`agent/schemas/venue.schema.json`. Then send it as parameter `v` with the `ingest_venue` recipe
through `write_cypher` on `weakest-link-mybag`, and verify it.

## Mapping rules (pick the slower option when unsure)

| The email says | You write |
|---|---|
| "4K" and "60 Hz" | `max_mode: "4K60"`, confidence medium |
| "4K" only | `max_mode: "4K30"`, input/edge confidence low, note "refresh rate not stated" |
| "Full HD", "1080p", "1920x1080", "WUXGA", "1920x1200" | `max_mode: "1080p60"` |
| "1440p", "QHD" | `max_mode: "1440p60"` |
| "720p", "HD ready", or nothing | `max_mode: "720p60"`, confidence low |
| "HDMI 1.4" / "HDMI 2.0" / "HDMI 2.1" input | `HDMI-1.4` / `HDMI-2.0` / `HDMI-2.1-FRL`, medium |
| "HDMI" input, no version | `HDMI-1.4`, low (or `HDMI-2.0`, low, when the display is 4K60) |
| "DisplayPort" / "DP" input | `DP-1.2-HBR2` (low) unless "1.4" is stated (`DP-1.4-HBR3`, medium) |
| "USB-C" input on the display | `DP-Alt-4L-HBR3`, low |
| "VGA" input | `VGA-1200p`, medium |
| "we leave/provide an HDMI cable" with no grade, "older", "standard" | provides `cable-hdmi-standard` |
| "High Speed HDMI cable" / "Premium High Speed" / "Ultra High Speed" | `cable-hdmi-high-speed` / `cable-hdmi-premium` / `cable-hdmi-ultra` |
| "VGA cable" provided | `cable-vga` |
| anything negated ("no adapters", "we don't supply VGA cables") | nothing |

- `id`: a slug of the venue and room, e.g. `riverside-library-room-2`. It must not be a catalog
  venue id.
- `confidence`: the venue's overall confidence. An email is at most `medium`; use `low` if any key
  fact was assumed.
- `source`: `{id: "email-<venue-id>-<date>", kind: "email", publisher: "<sender>", title: "<subject>",
  url: null, supports: "<the exact sentences you used>"}`.
- `display.inputs[].note`: say what you assumed, e.g. "HDMI version not stated; assumed HDMI 1.4".

## Example

Email: "Room 2 has a ceiling-mounted Full HD (1920x1080) projector. At the lectern there are HDMI
and VGA inputs. We leave an HDMI cable at the lectern; it's one of our older ones."

```json
{"id": "riverside-library-room-2", "name": "Riverside Library, Room 2", "confidence": "low",
 "description": "Ceiling-mounted Full HD projector, HDMI and VGA inputs, an older HDMI cable at the lectern.",
 "source": {"id": "email-riverside-library-room-2-2026-11-11", "kind": "email",
            "publisher": "Priya Nair <events@riverside-library.example>", "title": "Re: AV for your talk on 3 December",
            "url": null, "supports": "Room 2 has a ceiling-mounted Full HD (1920x1080) projector. At the lectern there are HDMI and VGA inputs. We leave an HDMI cable at the lectern; it's one of our older ones."},
 "display": {"name": "Riverside Library, Room 2 projector", "max_mode": "1080p60",
             "inputs": [{"connector": "HDMI", "standard": "HDMI-1.4", "confidence": "low", "note": "HDMI version not stated; assumed HDMI 1.4"},
                        {"connector": "VGA", "standard": "VGA-1200p", "confidence": "medium", "note": "VGA input"}]},
 "provides": ["cable-hdmi-standard"]}
```

After the write, run the venue check query from `CYPHER.md` and tell the user what was stored.
