# Demo video script, v2

Approved by the owner on 23 Nov 2026. Not uploaded to a video host yet.

- Video: [`weakest-link-demo-v2.mp4`](weakest-link-demo-v2.mp4), 98.3 s, 1920×1080, 30 fps. Captions are burned in and also in [`weakest-link-demo-v2.srt`](weakest-link-demo-v2.srt).
- Narration: OpenAI TTS, `tts-1-hd`, voice `nova`, one mono voice track normalized to -16 LUFS.
  Captions are timed from Whisper word timestamps. Checks: [`verification-v2.json`](verification-v2.json). Frames every 5 s: [`v2-frames/`](v2-frames/).
- Rebuild: `scripts/video/tts.py` → `transcribe.py` → `record.mjs` (Xvfb + local `vite preview`) → `assemble.py`.

## Changes from the first draft

1. Narration: one voice track, clips placed back to back with at least 1.2 s between them; checked by placement, silence detection and a transcript of the final mix.
2. No drawn pointer. Emphasis is a highlight box around the element being discussed; clicks get a short pause and a ripple.
3. The UI flow starts from a working bag and never shows an empty or error state (the app does update live while ticking; there is now an e2e test for it).
4. Terminal: `agent_demo.py --brief`, a 26 pt font in a 90-column terminal (no wrapping), a digital zoom on the answer and highlight boxes on the pack, leave, buy and charging lines.
5. No idle terminal: the agent scene ends 0.6 s after its last word.
6. Captions come from each clip's own word timestamps and never cross a scene boundary.

| Time | Scene | On screen | Narration |
|---|---|---|---|
| 0:00.0–0:12.0 | hook | Title card: a 4K projector, five minutes to go, the screen says 1080p 30 Hz, then No signal. | Five minutes before your talk, you plug in, and the 4K projector shows a blurry 1080p. Or nothing at all. The laptop is fine. Somewhere in your bag is a weak link. |
| 0:12.0–0:25.2 | ui | Web UI on the local preview build: first-run intro, pick a laptop, tick the bag, pick the venue and 4K at 60 Hz. | Weakest Link tells you before you leave. Pick your laptop, tick what's in your bag, then choose the venue and the picture you want. It all runs in your browser, on Relate's WebAssembly engine. |
| 0:25.2–0:40.2 | diagram | Verdict and chain diagram: the hub is highlighted as the weakest link, with a confidence chip and a source link on every hop; the Cypher behind it. | The answer is a path through a graph: port, hub, cable, projector input. The hop with the lowest capacity is the weakest link. Here, a hub that only does HDMI 1.4. Every link shows its source and a confidence level. |
| 0:40.2–0:52.8 | fix | Best purchase tab: single purchases ranked by how many of the chosen venues they fix. | Best purchase looks across every venue you visit. One USB-C to HDMI cable fixes three of nine. And when the venue's own display is the limit, it says so instead of selling you something. |
| 0:52.8–1:03.2 | charge | Charging tab: a 140 W charger throttled to 60 W by a USB 2.0 cable, the cable to buy, Add to bag, then Fast-charges. | Same graph, in watts. A 140 watt charger on a thin cable charges slowly. It names the cable to buy, and one click later, it fast-charges. |
| 1:03.2–1:21.3 | agent | Terminal: python3 scripts/agent_demo.py --pace, a pack-my-bag agent driving relate serve --mcp. | Your AI assistant gets the same graph through Relate's MCP server. This pack-my-bag agent reads a venue's email, writes it into its own copy of the graph with the source, and runs the vetted query recipes. Pack this, leave that, buy one cable, and a better charging cable. |
| 1:21.3–1:38.2 | close | Closing card: why a graph, why Relate. | Why a graph? Compatibility is relationships: what plugs into what, and what each hop can carry. Relate keeps it all in one cited file that runs the same in the command line, the browser, and MCP. Weakest Link. Find it before your audience does. |
